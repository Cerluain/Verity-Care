"""Guardian timeline + staff check-in API (Dev A). Storage: SQLite (care_db.py).

Staff check-in (POST /care/events):
  photo → apps/onchain POST /delivery (Saswata's Proof-of-Service pipeline):
  image → IPFS, metadata → IPFS, sha256(canonical(metadata)) committed on-chain
  (claim_type 5, STAFF wallet). We store tx/CIDs against the care-plan item so the
  guardian timeline shows it. If the onchain service is down (or older, without
  /delivery), we fall back to /commit claim_type 1, then to "recorded, not anchored".

Disputes (POST /care/disputes) are ROUTED, not sent straight to the state:
  1. facility (Director of Nursing)            — always
  2. State Long-Term Care Ombudsman            — if a safety item (medication)
  3. State investigator (MFCU)                  — only if the item is BILLED, or the
                                                 family has disputed 2+ items in 7 days
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

import care_db
from care_db import _lock

ONCHAIN_SERVICE_URL = os.getenv("ONCHAIN_SERVICE_URL", "http://localhost:8001")
CARE_DEMO_TIME = os.getenv("CARE_DEMO_TIME", "12:30")   # "now" for the demo; empty -> real time
PHOTOS = care_db.DB_PATH.parent / "photos"
SERVICE_TYPE = {"meal": "meal", "medication": "medication", "therapy": "pt_session",
                "vitals": "visit", "activity": "visit"}
ROLE_LABEL = {"RN": "Registered nurse", "LPN": "Licensed practical nurse", "CNA": "Nursing aide",
              "PT": "Physical therapist", "OT": "Occupational therapist"}

router = APIRouter()
_http = httpx.Client(timeout=90.0)
_db = None


def db():
    global _db
    if _db is None:
        _db = care_db.connect()
    return _db


def _today() -> str:
    return date.today().isoformat()


def _now_hhmm() -> str:
    return CARE_DEMO_TIME or datetime.now().strftime("%H:%M")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(r) -> dict:
    return dict(r) if r else None


def _resident(rid: str) -> dict:
    r = _row(db().execute("SELECT * FROM residents WHERE id=?", (rid,)).fetchone())
    if not r:
        raise HTTPException(404, f"unknown resident {rid}")
    r["profile"] = json.loads(r.pop("profile_json"))
    r["guardian"] = _row(db().execute("SELECT * FROM guardians WHERE resident_id=?", (rid,)).fetchone())
    return r


def _items(rid: str, day: str) -> list[dict]:
    plan = [dict(x) for x in db().execute("SELECT * FROM care_plan WHERE resident_id=? ORDER BY time", (rid,))]
    ins = {x["plan_item_id"]: dict(x) for x in db().execute(
        "SELECT * FROM check_ins WHERE resident_id=? AND day=? ORDER BY captured_at", (rid, day))}
    dsp = {x["plan_item_id"]: dict(x) for x in db().execute(
        "SELECT * FROM disputes WHERE resident_id=? AND day=?", (rid, day))}
    staff = {x["id"]: dict(x) for x in db().execute("SELECT * FROM staff")}
    now, today = _now_hhmm(), _today()
    out = []
    for p in plan:
        ev, d = ins.get(p["id"]), dsp.get(p["id"])
        if d:
            d["route"] = json.loads(d.pop("route_json"))
        if d:
            status = "disputed"
        elif ev:
            status = "verified"
        elif day < today or p["time"] <= now:
            status = "not_verified"
        else:
            status = "upcoming"
        if ev and ev.get("staff_id") in staff:
            ev["staff"] = staff[ev["staff_id"]]
        out.append({**p, "status": status, "event": ev, "dispute": d})
    return out


# ------------------------------------------------------------------ guardian side
@router.get("/care/residents")
def residents():
    rows = [dict(x) for x in db().execute("SELECT id, name, age, room FROM residents ORDER BY name")]
    return {"residents": rows, "facility": care_db.FACILITY_NAME}


@router.get("/care/residents/{rid}")
def resident_profile(rid: str):
    r = _resident(rid)
    r["history"] = [dict(x) for x in db().execute(
        "SELECT day, kind, title, detail FROM history WHERE resident_id=? ORDER BY day DESC", (rid,))]
    adm = date.fromisoformat(r["admitted"])
    r["days_in_care"] = (date.today() - adm).days
    return r


@router.get("/care/days")
def days():
    go_live = care_db.GO_LIVE().isoformat()
    return {"go_live": go_live, "today": _today(),
            "days": [{"day": d, "before_go_live": d < go_live} for d in care_db.days_back(7)]}


@router.get("/care/timeline/{rid}")
def timeline(rid: str, day: str | None = None):
    r = _resident(rid)
    day = day or _today()
    go_live = care_db.GO_LIVE().isoformat()
    if day < go_live:
        return {"resident": r, "day": day, "before_go_live": True, "go_live": go_live,
                "demo_time": _now_hhmm(), "counts": {}, "items": []}
    items = _items(rid, day)
    counts = {s: sum(i["status"] == s for i in items) for s in ("verified", "not_verified", "disputed", "upcoming")}
    return {"resident": r, "day": day, "before_go_live": False, "go_live": go_live,
            "demo_time": _now_hhmm(), "counts": counts, "items": items}


@router.post("/care/disputes")
async def dispute(req: Request):
    b = await req.json()
    rid, pid = b.get("resident_id", ""), b.get("plan_item_id", "")
    _resident(rid)
    item = _row(db().execute("SELECT * FROM care_plan WHERE id=? AND resident_id=?", (pid, rid)).fetchone())
    if not item:
        raise HTTPException(400, "unknown plan_item_id")
    day = b.get("day") or _today()
    now = _utc()
    since = (date.today() - timedelta(days=7)).isoformat()
    prior = db().execute("SELECT COUNT(*) FROM disputes WHERE resident_id=? AND day>=? AND plan_item_id<>?",
                         (rid, since, pid)).fetchone()[0]
    route = [{"to": "facility", "label": "Sent to the facility (Director of Nursing)", "at": now, "done": True}]
    if item["category"] == "medication":
        route.append({"to": "ombudsman", "label": "Escalated to the State Long-Term Care Ombudsman (missed medication is a safety issue)", "at": now, "done": True})
    else:
        route.append({"to": "ombudsman", "label": "Goes to the State Long-Term Care Ombudsman if not resolved in 24 h", "at": None, "done": False})
    why = []
    if item["billed"]:
        why.append(f"this service is billed ({item['billed']})")
    if prior >= 1:
        why.append(f"{prior + 1} disputes from this family in 7 days")
    if why:
        route.append({"to": "investigator", "label": "Referred to the state investigator (MFCU): " + "; ".join(why), "at": now, "done": True})
    status = route[-1]["to"] if route[-1]["done"] else "facility"
    did = "dsp-" + uuid.uuid4().hex[:8]
    with _lock:
        db().execute("DELETE FROM disputes WHERE resident_id=? AND plan_item_id=? AND day=?", (rid, pid, day))
        db().execute("INSERT INTO disputes VALUES (?,?,?,?,?,?,?,?)",
                     (did, pid, rid, day, (b.get("reason") or "Family says this did not happen")[:500],
                      now, json.dumps(route), status))
        db().commit()
    return {"id": did, "route": route, "status": status}


# ------------------------------------------------------------------ staff side
@router.get("/care/staff/{sid}")
def staff_login(sid: str):
    s = _row(db().execute("SELECT * FROM staff WHERE id=?", (sid.strip().upper(),)).fetchone())
    if not s:
        raise HTTPException(404, "Staff ID not found")
    s["role_label"] = ROLE_LABEL.get(s["role"], s["role"])
    res = []
    for r in db().execute("""SELECT r.id, r.name, r.room, r.age FROM residents r
                             JOIN assignments a ON a.resident_id=r.id WHERE a.staff_id=? ORDER BY r.room""", (s["id"],)):
        tasks = [i for i in _items(r["id"], _today()) if i["role"] == s["role"]]
        res.append({**dict(r), "open": sum(t["status"] in ("not_verified", "upcoming") for t in tasks),
                    "due": sum(t["status"] == "not_verified" for t in tasks), "total": len(tasks)})
    return {"staff": s, "residents": res, "facility": care_db.FACILITY_NAME, "demo_time": _now_hhmm()}


@router.get("/care/staff/{sid}/tasks/{rid}")
def staff_tasks(sid: str, rid: str):
    s = staff_login(sid)["staff"]
    if not db().execute("SELECT 1 FROM assignments WHERE staff_id=? AND resident_id=?", (s["id"], rid)).fetchone():
        raise HTTPException(403, "Not your resident")
    r = _resident(rid)
    return {"resident": {k: r[k] for k in ("id", "name", "room", "age")},
            "allergies": r["profile"]["allergies"],
            "tasks": [i for i in _items(rid, _today()) if i["role"] == s["role"]]}


@router.post("/care/events")
async def capture(req: Request):
    b = await req.json()
    sid, rid, pid = (b.get("staff_id") or "").upper(), b.get("resident_id", ""), b.get("plan_item_id", "")
    s = _row(db().execute("SELECT * FROM staff WHERE id=?", (sid,)).fetchone())
    item = _row(db().execute("SELECT * FROM care_plan WHERE id=? AND resident_id=?", (pid, rid)).fetchone())
    if not s or not item:
        raise HTTPException(400, "unknown staff, resident or task")
    if not db().execute("SELECT 1 FROM assignments WHERE staff_id=? AND resident_id=?", (sid, rid)).fetchone():
        raise HTTPException(403, "Not your resident")
    data_url = b.get("photo") or ""
    if "," not in data_url:
        raise HTTPException(400, "photo must be a data URL")
    raw = base64.b64decode(data_url.split(",", 1)[1])
    if len(raw) > 8_000_000:
        raise HTTPException(413, "photo too large")

    eid = "evt-" + uuid.uuid4().hex[:10]
    PHOTOS.mkdir(parents=True, exist_ok=True)
    (PHOTOS / f"{eid}.jpg").write_bytes(raw)
    delivered_at = _utc()
    rec = {"photo_sha256": hashlib.sha256(raw).hexdigest()}

    # 1) Saswata's Proof-of-Service pipeline: IPFS + staff wallet (claim type 5)
    try:
        r = _http.post(f"{ONCHAIN_SERVICE_URL}/delivery",
                       data={"facility_id": care_db.FACILITY_ID, "patient_pseudonym": rid,
                             "service_type": SERVICE_TYPE.get(item["category"], "visit"),
                             "service_detail": f"{item['title']}: {item['detail']}", "staff_pseudonym": sid,
                             "delivered_at": delivered_at},
                       files={"image": (f"{eid}.jpg", raw, "image/jpeg")})
        if r.status_code == 200:
            d = r.json()
            rec.update({k: d.get(k) for k in ("claim_hash", "tx_hash", "explorer_url", "signer_role", "image_cid",
                                              "metadata_cid", "image_url", "metadata_url", "pin_mode")})
            rec["mocked"] = int(bool(d.get("mocked") or str(d.get("tx_hash", "")).startswith("0xmock")))
    except Exception:
        pass
    # 2) Fallback: plain commit (older onchain service without /delivery)
    if not rec.get("tx_hash"):
        att = {"photo_sha256": rec["photo_sha256"], "resident_id": rid, "plan_item_id": pid,
               "staff_id": sid, "captured_at": delivered_at}
        rec["claim_hash"] = "0x" + hashlib.sha256(json.dumps(att, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        try:
            r = _http.post(f"{ONCHAIN_SERVICE_URL}/commit", json={"claim_type": 1, "claim_hash": rec["claim_hash"]})
            if r.status_code == 200:
                d = r.json()
                rec.update({"tx_hash": d.get("tx_hash"), "explorer_url": d.get("explorer_url"),
                            "signer_role": d.get("signer_role"), "mocked": int(bool(d.get("mocked")))})
        except Exception:
            pass  # recorded, not anchored

    row = {"id": eid, "plan_item_id": pid, "resident_id": rid, "staff_id": sid, "day": _today(),
           "captured_at": delivered_at, "note": (b.get("note") or None), "seeded": 0,
           "photo_url": f"/care/photos/{eid}", **{k: rec.get(k) for k in (
               "photo_sha256", "claim_hash", "tx_hash", "explorer_url", "signer_role", "mocked", "image_cid",
               "metadata_cid", "image_url", "metadata_url", "pin_mode")}}
    with _lock:
        db().execute(f"INSERT INTO check_ins ({','.join(row)}) VALUES ({','.join('?' * len(row))})", tuple(row.values()))
        db().commit()
    return row


@router.get("/care/photos/{eid}")
def photo(eid: str):
    p = PHOTOS / f"{eid}.jpg"
    if not eid.startswith("evt-") or not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/jpeg")


# ------------------------------------------------------------------ investigator side
@router.get("/care/reports")
def reports(facility_id: str):
    """Only disputes the routing sent to the investigator (billed or repeated)."""
    out = []
    for d in db().execute("""SELECT d.*, r.name AS resident, p.time, p.title, p.billed FROM disputes d
                             JOIN residents r ON r.id=d.resident_id JOIN care_plan p ON p.id=d.plan_item_id
                             WHERE r.facility_id=? ORDER BY d.created_at DESC""", (facility_id,)):
        d = dict(d)
        route = json.loads(d["route_json"])
        inv = next((s for s in route if s["to"] == "investigator"), None)
        if inv:
            out.append({"id": d["id"], "kind": "dispute", "resident": d["resident"], "time": d["time"],
                        "title": d["title"], "detail": f'Family: "{d["reason"]}" · {inv["label"]}'})
    return {"reports": out}


@router.post("/care/reset")
def reset():
    global _db
    with _lock:
        if _db is not None:
            _db.close()
            _db = None
    care_db.reset()
    # Also nuke the photo cache so the demo starts with zero uploaded images.
    if PHOTOS.exists():
        for p in PHOTOS.glob("*"):
            try:
                p.unlink()
            except Exception:
                pass
    return {"ok": True, "photos_cleared": True}
