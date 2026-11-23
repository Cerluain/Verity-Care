"""
apps/dashboard/main.py — Verity Care Investigator Dashboard.

Thin FastAPI server:
- Serves `index.html` + static assets at `/`
- Serves `/data/facilities.json` from the repo root
- Proxies `GET /spend/{id}`     → phantom-spend:8003
- Proxies `POST /chain/commit`  → onchain:8001/commit
- Proxies `GET /chain/{tx}`     → onchain:8001/commit/{tx}
- Proxies `GET /chain/verify`   → onchain:8001/verify

Why proxy instead of browser-to-service direct? One origin → zero CORS fuss, and
the dashboard can swap mock/live upstream URLs without rebuilding the frontend.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

ONCHAIN_SERVICE_URL = os.getenv("ONCHAIN_SERVICE_URL", "http://localhost:8001")
SPEND_API_BASE = os.getenv("SPEND_API_BASE", "http://localhost:8003")
SHIFT_API_BASE = os.getenv("SHIFT_API_BASE", "http://localhost:8002")

APP_DIR = Path(__file__).parent
REPO_ROOT = APP_DIR.resolve().parents[1]
STATIC_DIR = APP_DIR / "static"
FACILITIES_PATH = REPO_ROOT / "data" / "facilities.json"
SPEND_SAMPLES_DIR = REPO_ROOT / "apps" / "phantom-spend" / "samples"

app = FastAPI(title="Verity Care — Investigator Dashboard")
_http = httpx.Client(timeout=15.0)

# Guardian timeline + live staff photo check-in (Dev A) — see care.py
from care import router as care_router  # noqa: E402
app.include_router(care_router)


# Extra pages on the same site (Dev A): pitch story, guardian view, staff check-in.
@app.get("/pitch")
def pitch_page():
    return FileResponse(APP_DIR / "pitch.html")


@app.get("/guardian")
def guardian_page():
    return FileResponse(APP_DIR / "guardian.html")


@app.get("/staff")
def staff_page():
    return FileResponse(APP_DIR / "staff.html")


@app.get("/")
def index():
    return FileResponse(APP_DIR / "index.html")


@app.get("/facilities")
def facilities():
    if not FACILITIES_PATH.exists():
        raise HTTPException(500, f"facilities.json missing at {FACILITIES_PATH}")
    return JSONResponse(json.loads(FACILITIES_PATH.read_text()))


def _auto_anchor_signals(payload: dict, claim_type: int) -> dict:
    """verity_service auto-anchors every analytics signal card so the investigator
    never clicks 'commit on-chain'. Idempotent: hits the onchain service's /verify
    which reads Postgres FIRST (cheap, no chain RPC), then JSONL fallback. Only
    cards that have never been committed trigger a fresh /commit (one real Base
    Sepolia tx). After the first facility click each refetch is a pure DB read."""
    signals = (payload or {}).get("signals") or []
    if not signals:
        return payload
    import hashlib as _h
    def canon(o):
        if isinstance(o, dict): return {k: canon(o[k]) for k in sorted(o)}
        if isinstance(o, list): return [canon(x) for x in o]
        return o
    for card in signals:
        if card.get("chain_commit"):
            continue
        clean = {k: v for k, v in card.items() if not k.startswith("_") and k != "chain_commit"}
        claim_hash = "0x" + _h.sha256(json.dumps(canon(clean), separators=(",", ":")).encode()).hexdigest()
        # Cache check: /verify hits Postgres first. No chain RPC in the hot path.
        try:
            v = _http.get(f"{ONCHAIN_SERVICE_URL}/verify",
                          params={"claim_hash": claim_hash, "claim_type": claim_type}, timeout=5)
            if v.status_code == 200 and v.json().get("count"):
                m = v.json()["matches"][0]
                card["chain_commit"] = {
                    "tx_hash": m.get("tx_hash"), "block_number": m.get("block_number"),
                    "signer_role": m.get("signer_role"), "signer_address": m.get("signer_address"),
                    "explorer_url": m.get("explorer_url"), "committed_at": m.get("committed_at"),
                    "mocked": m.get("mocked", False), "claim_hash": claim_hash,
                }
                continue
        except Exception:
            pass
        # First-ever request for this card. Fire a single real commit.
        try:
            r = _http.post(f"{ONCHAIN_SERVICE_URL}/commit",
                           json={"claim_type": claim_type, "claim_hash": claim_hash}, timeout=10)
            if r.status_code == 200:
                m = r.json()
                card["chain_commit"] = {
                    "tx_hash": m.get("tx_hash"), "block_number": m.get("block_number"),
                    "signer_role": m.get("signer_role"), "signer_address": m.get("signer_address"),
                    "explorer_url": m.get("explorer_url"), "committed_at": m.get("committed_at"),
                    "mocked": m.get("mocked", False), "claim_hash": claim_hash,
                }
        except Exception:
            pass
    return payload


@app.get("/spend/{facility_id}")
def spend(facility_id: str):
    """Try live Abhi service first, fall back to his pre-built sample JSON.
    verity_service auto-anchors each signal card before returning."""
    payload = None
    try:
        r = _http.get(f"{SPEND_API_BASE}/spend/{facility_id}")
        if r.status_code == 200:
            payload = r.json()
    except Exception:
        pass
    if payload is None:
        sample = SPEND_SAMPLES_DIR / f"{facility_id}.json"
        if not sample.exists():
            raise HTTPException(404, f"no SPEND data for {facility_id}")
        payload = json.loads(sample.read_text())
    return JSONResponse(_auto_anchor_signals(payload, claim_type=4))


@app.get("/pbj/{facility_id}")
def pbj(facility_id: str):
    """MOCK PBJ staffing summary from phantom-spend until Leo's phantom-shift is live."""
    try:
        r = _http.get(f"{SPEND_API_BASE}/pbj/{facility_id}")
        if r.status_code == 200:
            return JSONResponse(r.json())
    except Exception:
        pass
    mock = REPO_ROOT / "data" / "spend" / "pbj-mock.json"
    doc = json.loads(mock.read_text()) if mock.exists() else {"facilities": {}}
    if facility_id not in doc["facilities"]:
        raise HTTPException(404, f"no PBJ data for {facility_id}")
    return JSONResponse({**doc["facilities"][facility_id], "_meta": doc.get("_meta", {})})


@app.get("/shift/{facility_id}")
def shift(facility_id: str):
    payload = None
    try:
        r = _http.get(f"{SHIFT_API_BASE}/shift/{facility_id}")
        if r.status_code == 200:
            payload = r.json()
    except Exception:
        pass
    if payload is None:
        return JSONResponse({"signals": [], "note": "phantom-shift service not yet online"})
    return JSONResponse(_auto_anchor_signals(payload, claim_type=4))


@app.post("/chain/commit")
async def chain_commit(req: Request):
    body = await req.json()
    r = _http.post(f"{ONCHAIN_SERVICE_URL}/commit", json=body)
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/sign")
async def sign(req: Request):
    """Proxy to apps/onchain /sign for ed25519 envelope signing (case file)."""
    body = await req.json()
    r = _http.post(f"{ONCHAIN_SERVICE_URL}/sign", json=body)
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/admin/reset-demo")
def admin_reset(scope: str = "all"):
    """Proxy the hard-reset button: wipes deliveries + commits in the DB index."""
    r = _http.post(f"{ONCHAIN_SERVICE_URL}/admin/reset-demo", params={"scope": scope})
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/facility/inventory/parse")
async def facility_parse(req: Request):
    body = await req.body()
    headers = {"content-type": req.headers.get("content-type", "application/octet-stream")}
    r = _http.post(f"{ONCHAIN_SERVICE_URL}/facility/inventory/parse", content=body, headers=headers, timeout=60.0)
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/facility/inventory/commit")
async def facility_commit(req: Request):
    body = await req.json()
    r = _http.post(f"{ONCHAIN_SERVICE_URL}/facility/inventory/commit", json=body, timeout=60.0)
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/facility/inventory/snapshot")
async def facility_snapshot(req: Request):
    """Stream the multipart body through to the onchain service."""
    body = await req.body()
    headers = {"content-type": req.headers.get("content-type", "application/octet-stream")}
    r = _http.post(f"{ONCHAIN_SERVICE_URL}/facility/inventory/snapshot", content=body, headers=headers, timeout=60.0)
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/facility/inventory")
def facility_inventory(facility_id: str | None = None, limit: int = 20):
    params = {"limit": limit}
    if facility_id: params["facility_id"] = facility_id
    r = _http.get(f"{ONCHAIN_SERVICE_URL}/facility/inventory", params=params)
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/facility/inventory/periods/{facility_id}")
def facility_periods(facility_id: str):
    r = _http.get(f"{ONCHAIN_SERVICE_URL}/facility/inventory/periods/{facility_id}")
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/facility/inventory/fixture-preview/{facility_id}")
def facility_fixture_preview(facility_id: str, period: str | None = None):
    params = {"period": period} if period else {}
    r = _http.get(f"{ONCHAIN_SERVICE_URL}/facility/inventory/fixture-preview/{facility_id}", params=params)
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/investigator/drug-disparity/{facility_id}")
def investigator_drug_disparity(facility_id: str):
    r = _http.get(f"{ONCHAIN_SERVICE_URL}/investigator/drug-disparity/{facility_id}", timeout=15.0)
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/facility")
def facility_page():
    return FileResponse(APP_DIR / "facility.html")


@app.get("/chain/health")
def chain_health():
    try:
        r = _http.get(f"{ONCHAIN_SERVICE_URL}/health")
        return JSONResponse(r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=503)


@app.get("/delivery/defaults")
def delivery_defaults():
    r = _http.get(f"{ONCHAIN_SERVICE_URL}/delivery/defaults")
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/delivery")
async def delivery(req: Request):
    """Multipart proxy to apps/onchain /delivery.
    Dashboard-side helper for the Proof-of-Service tab; keeps browser on one origin."""
    body = await req.body()
    r = _http.post(
        f"{ONCHAIN_SERVICE_URL}/delivery", content=body,
        headers={"content-type": req.headers.get("content-type", "")},
        timeout=90.0,
    )
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/deliveries")
def deliveries(facility_id: str | None = None, limit: int = 50):
    params: dict = {"limit": limit}
    if facility_id:
        params["facility_id"] = facility_id
    r = _http.get(f"{ONCHAIN_SERVICE_URL}/deliveries", params=params)
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/chain/{tx_hash}")
def chain_get(tx_hash: str):
    r = _http.get(f"{ONCHAIN_SERVICE_URL}/commit/{tx_hash}")
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/chain/verify/by-hash")
def chain_verify(claim_hash: str, claim_type: int | None = None):
    params: dict = {"claim_hash": claim_hash}
    if claim_type is not None:
        params["claim_type"] = claim_type
    r = _http.get(f"{ONCHAIN_SERVICE_URL}/verify", params=params)
    return JSONResponse(r.json(), status_code=r.status_code)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mount data/demo/ so the facility UI can fetch the staged inventory photo.
_DEMO_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "demo"
if _DEMO_DIR.exists():
    app.mount("/static-demo", StaticFiles(directory=_DEMO_DIR), name="static-demo")
