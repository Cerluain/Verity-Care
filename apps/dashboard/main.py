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


@app.get("/spend/{facility_id}")
def spend(facility_id: str):
    """Try live Abhi service first, fall back to his pre-built sample JSON."""
    try:
        r = _http.get(f"{SPEND_API_BASE}/spend/{facility_id}")
        if r.status_code == 200:
            return JSONResponse(r.json())
    except Exception:
        pass
    sample = SPEND_SAMPLES_DIR / f"{facility_id}.json"
    if sample.exists():
        return JSONResponse(json.loads(sample.read_text()))
    raise HTTPException(404, f"no SPEND data for {facility_id}")


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
    try:
        r = _http.get(f"{SHIFT_API_BASE}/shift/{facility_id}")
        if r.status_code == 200:
            return JSONResponse(r.json())
    except Exception:
        pass
    return JSONResponse({"signals": [], "note": "phantom-shift service not yet online"})


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
