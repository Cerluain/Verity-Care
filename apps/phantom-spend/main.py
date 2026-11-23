"""Phantom Spend service (Dev A). Port 8003.

    uvicorn main:app --port 8003 --reload

GET /health                 -> {"ok": true, ...}
GET /spend                  -> {"facilities": [{id, name, spend_overall}]}
GET /pbj/{facility_id}      -> MOCK PBJ staffing summary (until Dev B's service is live)
GET /spend/{facility_id}    -> {"signals": SignalCard[]}   (ref_price_delta, ownership_overlap,
                                                             volume_sanity, spend_overall)
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cards import Store, spend_signals

app = FastAPI(title="Verity Care — Phantom Spend", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

store = Store()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "phantom-spend", "facilities": len(store.facilities),
            "prices_pulled_at": store.prices_doc["pulled_at"]}


@app.get("/spend")
def spend_index() -> dict:
    out = []
    for fid, fac in store.facilities.items():
        overall = next(c for c in spend_signals(store, fid) if c["signal_type"] == "spend_overall")
        out.append({"id": fid, "name": fac["name"], "spend_overall": overall["severity"]})
    return {"facilities": out}


@app.get("/spend/{facility_id}")
def spend(facility_id: str) -> dict:
    if facility_id not in store.facilities:
        raise HTTPException(status_code=404, detail=f"unknown facility_id: {facility_id}")
    return {"signals": spend_signals(store, facility_id)}


@app.get("/pbj/{facility_id}")
def pbj(facility_id: str) -> dict:
    """MOCK Payroll-Based Journal summary. Replaced by Dev B's real PBJ data."""
    import json
    from cards import SPEND
    doc = json.loads((SPEND / "pbj-mock.json").read_text())
    if facility_id not in doc["facilities"]:
        raise HTTPException(status_code=404, detail=f"unknown facility_id: {facility_id}")
    return {**doc["facilities"][facility_id], "_meta": doc["_meta"]}
