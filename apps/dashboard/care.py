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
import re
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
CARE_DEMO_TIME = os.getenv("CARE_DEMO_TIME", "")   # empty -> real local time (on-time demo); "HH:MM" to pin
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


# Per-category windows (minutes). Tighter for anything safety-critical, looser for
# optional activities. See contexts/saswata.md "decisions log" (Nov 22) for rationale.
# NOTE: medication is the tightest because insulin timing matters clinically.
CATEGORY_WINDOW = {
    "medication": (10, 10),   # ±10 min (insulin, scheduled meds)
    "vitals":     (20, 30),   # morning rounds, slight slack
    "meal":       (20, 20),   # breakfast tight; tray delivery + eating pace
    "therapy":    (60, 120),  # PT/OT reschedules intraday
    "activity":   (60, 180),  # optional, loose
}
CATEGORY_WINDOW_DEFAULT = (30, 60)


def _hhmm_from_iso(iso: str) -> str | None:
    """Extract local HH:MM from an ISO-like timestamp. Handles both UTC-Z and offset forms."""
    if not iso:
        return None
    try:
        # Python 3.11+ fromisoformat handles the 'Z' suffix fine.
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to local wallclock so it compares apples-to-apples with scheduled HH:MM.
        local = dt.astimezone()
        return local.strftime("%H:%M")
    except Exception:
        m = re.search(r"T(\d{2}):(\d{2})", iso) or re.search(r"(\d{2}):(\d{2})", iso)
        return f"{m.group(1)}:{m.group(2)}" if m else None


def _12h(hhmm: str | None) -> str:
    """'07:30' -> '7:30 AM' for display text."""
    if not hhmm or not re.match(r"^\d{1,2}:\d{2}$", hhmm):
        return hhmm or ""
    h, m = int(hhmm.split(":")[0]), hhmm.split(":")[1]
    return f"{(h % 12) or 12}:{m} {'AM' if h < 12 else 'PM'}"


def _mins_between(hhmm_a: str, hhmm_b: str) -> int:
    """Signed minutes from a→b (negative = a is after b)."""
    ah, am = int(hhmm_a[:2]), int(hhmm_a[-2:])
    bh, bm = int(hhmm_b[:2]), int(hhmm_b[-2:])
    return (bh * 60 + bm) - (ah * 60 + am)


def _classify(scheduled_hhmm: str, now_hhmm: str, captured_hhmm: str | None,
              category: str, day: str, today: str) -> str:
    """Return status for a plan item under the window policy.
    verified         → photo landed inside [scheduled-before, scheduled+after]
    verified_late    → photo landed AFTER the window
    upcoming         → clock hasn't reached scheduled-before yet (today only)
    due              → clock is inside the window, no photo yet (today only)
    delayed          → clock is past scheduled+after, no photo (today only, or any past day)
    """
    before, after = CATEGORY_WINDOW.get(category, CATEGORY_WINDOW_DEFAULT)
    if captured_hhmm:
        delta = _mins_between(scheduled_hhmm, captured_hhmm)   # positive = captured AFTER scheduled
        return "verified_late" if delta > after else "verified"
    # No photo yet.
    if day < today:
        return "delayed"
    pre_start = _mins_between(now_hhmm, scheduled_hhmm)        # positive = scheduled is in the future
    if pre_start > before:
        return "upcoming"
    past_end = _mins_between(scheduled_hhmm, now_hhmm) - after # positive = past the window end
    if past_end > 0:
        return "delayed"
    return "due"


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
        captured = _hhmm_from_iso(ev.get("captured_at") or "") if ev else None
        if d:
            status = "disputed"
        else:
            status = _classify(p["time"], now, captured, p["category"], day, today)
        if ev and ev.get("staff_id") in staff:
            ev["staff"] = staff[ev["staff_id"]]
        before, after = CATEGORY_WINDOW.get(p["category"], CATEGORY_WINDOW_DEFAULT)
        out.append({**p, "status": status, "event": ev, "dispute": d,
                    "window": {"before_min": before, "after_min": after}})
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
    counts = {s: sum(i["status"] == s for i in items)
              for s in ("verified", "verified_late", "due", "delayed", "disputed", "upcoming")}
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


# ------------------------------------------------------------------ shared demo selection
# Links the staff app and the guardian page across devices: when a staff member signs in
# (or opens a resident) on the phone, the guardian page on the laptop follows.
_session: dict = {"staff_id": None, "resident_id": None}


@router.get("/care/session")
def get_session():
    out = dict(_session)
    if out["staff_id"]:
        s = _row(db().execute("SELECT id, name, role FROM staff WHERE id=?", (out["staff_id"],)).fetchone())
        out["staff"] = s
        out["residents"] = [dict(x) for x in db().execute(
            """SELECT r.id, r.name, r.room FROM residents r JOIN assignments a ON a.resident_id=r.id
               WHERE a.staff_id=? ORDER BY r.name""", (out["staff_id"],))]
    return out


@router.post("/care/session")
async def set_session(req: Request):
    b = await req.json()
    if "staff_id" in b:
        sid = (b["staff_id"] or "").upper() or None
        if sid and not db().execute("SELECT 1 FROM staff WHERE id=?", (sid,)).fetchone():
            raise HTTPException(404, "Staff ID not found")
        if sid != _session["staff_id"]:
            _session["resident_id"] = None
        _session["staff_id"] = sid
    if "resident_id" in b:
        _session["resident_id"] = b["resident_id"] or None
    return get_session()


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
        tasks = [i for i in _items(r["id"], _today()) if i["owner"] == s["id"]]
        res.append({**dict(r), "open": sum(t["status"] in ("due", "delayed", "not_verified", "upcoming") for t in tasks),
                    "due": sum(t["status"] in ("due", "delayed", "not_verified") for t in tasks), "total": len(tasks)})
    return {"staff": s, "residents": res, "facility": care_db.FACILITY_NAME, "demo_time": _now_hhmm()}


@router.get("/care/staff/{sid}/tasks/{rid}")
def staff_tasks(sid: str, rid: str):
    s = staff_login(sid)["staff"]
    if not db().execute("SELECT 1 FROM assignments WHERE staff_id=? AND resident_id=?", (s["id"], rid)).fetchone():
        raise HTTPException(403, "Not your resident")
    r = _resident(rid)
    return {"resident": {k: r[k] for k in ("id", "name", "room", "age")},
            "allergies": r["profile"]["allergies"],
            "tasks": [i for i in _items(rid, _today()) if i["owner"] == s["id"]]}


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
    """Investigator-facing stream:
       - family disputes that were routed to the investigator (billed or repeated)
       - DELAYED or VERIFIED_LATE items, especially when the plan item is billed
    Both shapes land in the investigator's GUARDIAN REPORTS tab.
    """
    out = []
    # 1. disputes
    for d in db().execute("""SELECT d.*, r.name AS resident, p.time, p.title, p.billed FROM disputes d
                             JOIN residents r ON r.id=d.resident_id JOIN care_plan p ON p.id=d.plan_item_id
                             WHERE r.facility_id=? ORDER BY d.created_at DESC""", (facility_id,)):
        d = dict(d)
        route = json.loads(d["route_json"])
        inv = next((s for s in route if s["to"] == "investigator"), None)
        if inv:
            out.append({"id": d["id"], "kind": "dispute", "resident": d["resident"], "time": _12h(d["time"]),
                        "title": d["title"], "detail": f'Family: "{d["reason"]}" · {inv["label"]}'})

    # 2. delayed / verified_late (today only — past days accumulate too much noise)
    today = _today()
    residents = [dict(x) for x in db().execute(
        "SELECT id, name FROM residents WHERE facility_id=?", (facility_id,))]
    for r in residents:
        for i in _items(r["id"], today):
            if i["status"] in ("delayed", "verified_late"):
                if i["status"] == "delayed":
                    detail = f'Scheduled {_12h(i["time"])}, past ±{i["window"]["after_min"]}-min window, no staff photo.'
                else:
                    cap = _hhmm_from_iso((i["event"] or {}).get("captured_at", "")) or "??:??"
                    detail = f'Scheduled {_12h(i["time"])}, staff photo captured {_12h(cap)} ({i["window"]["after_min"]}+ min late).'
                if i.get("billed"):
                    detail += f' Billed as {i["billed"]}.'
                out.append({"id": f'late-{r["id"]}-{i["id"]}', "kind": i["status"],
                            "resident": r["name"], "time": _12h(i["time"]), "title": i["title"],
                            "detail": detail})
    return {"reports": out}


@router.post("/care/reset")
def reset():
    global _db
    _session.update({"staff_id": None, "resident_id": None})
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


# ------------------------------------------------------------------ demo seed
# Re-times every care task around "now" (or ?at=HH:MM) so the demo always looks like
# mid-shift: morning done (seeded, placeholder photos, NOT on-chain), a couple missed,
# 2 tasks due for Priya + 2 for Marcus right after T, the rest later.
# Offsets are minutes from T.   D = seeded done · M = missed (no photo) · DUE · U = upcoming
SEED_PLAN = {
    "res-rosa": [("vitals-am", -200, "D", "BP 132/78 · glucose 148"), ("insulin-am", -185, "D", None),
                 ("meds-am", -180, "D", None), ("breakfast", -160, "D", "Ate about 75%"),
                 ("pt-am", -135, "M", None),                       # billed therapy, never verified
                 ("lunch", -25, "D", "Ate half"), ("insulin-noon", 5, "DUE", None),       # Priya due #1
                 ("activity", 90, "U", None), ("ot-pm", 150, "U", None),
                 ("dinner", 300, "U", None), ("meds-pm", 450, "U", None)],
    "res-walter": [("vitals-am", -190, "D", "BP 144/86"), ("breakfast", -70, "M", None),  # Marcus missed
                   ("lunch", 6, "DUE", None),                                             # Marcus due #1
                   ("meds-am", 8, "DUE", None),                                           # Priya due #2
                   ("activity", 100, "U", None), ("dinner", 310, "U", None), ("meds-pm", 440, "U", None)],
    "res-mae": [("vitals-am", -195, "D", None), ("meds-am", -175, "D", None),
                ("breakfast", -150, "D", "Pureed oats, all eaten"), ("pt-am", -100, "D", "Walked 40 ft with walker"),
                ("lunch", 12, "DUE", None),                                               # Marcus due #2
                ("activity", 110, "U", None), ("ot-pm", 160, "U", None),
                ("dinner", 305, "U", None), ("meds-pm", 455, "U", None)],
}


def _hhmm(minutes: int) -> str:
    minutes = max(0, min(23 * 60 + 59, minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@router.post("/care/seed")
def seed(at: str | None = None):
    """Reset + re-time the demo day around real time (or ?at=HH:MM)."""
    if at:
        try:
            h, m = (int(x) for x in at.split(":"))
        except Exception:
            raise HTTPException(400, "at must be HH:MM")
    else:
        now = datetime.now()
        h, m = now.hour, now.minute
    t = h * 60 + m
    reset()
    today = _today()
    local_tz = datetime.now().astimezone().tzinfo
    staff_for = {x["id"]: x["owner"] for x in db().execute("SELECT id, owner FROM care_plan")}
    summary = {"T": _hhmm(t), "done": 0, "missed": 0, "due": [], "upcoming": 0}
    with _lock:
        for rid, rows in SEED_PLAN.items():
            for pid, off, kind, note in rows:
                full = f"{rid}:{pid}"
                sched = _hhmm(t + off)
                db().execute("UPDATE care_plan SET time=? WHERE id=?", (sched, full))
                if kind == "D":
                    cap_min = t + off + 2
                    cap = datetime.now(local_tz).replace(hour=max(0, cap_min) // 60 % 24, minute=max(0, cap_min) % 60,
                                                         second=0, microsecond=0).isoformat()
                    cat = db().execute("SELECT category FROM care_plan WHERE id=?", (full,)).fetchone()[0]
                    db().execute("""INSERT INTO check_ins (id, plan_item_id, resident_id, staff_id, day, captured_at,
                                    note, seeded, photo_url) VALUES (?,?,?,?,?,?,?,1,?)""",
                                 (f"seed-{rid}-{pid}", full, rid, staff_for[full], today, cap, note,
                                  f"/static/seed/{cat}.svg"))
                    summary["done"] += 1
                elif kind == "M":
                    summary["missed"] += 1
                elif kind == "DUE":
                    summary["due"].append(f"{staff_for[full]} → {rid} {pid} @ {sched}")
                else:
                    summary["upcoming"] += 1
        db().commit()
    return summary
