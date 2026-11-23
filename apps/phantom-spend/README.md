# apps/phantom-spend — Procurement fraud detection

**Owner:** Abhi (Dev A) · **Port:** 8003 · **Status:** P0 endpoint live, 17 tests passing.

Produces SPEND signal cards for each facility. Full plan + decisions: `contexts/abi.md`.

## Run

```bash
cd apps/phantom-spend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8003 --reload
.venv/bin/pytest -q
```

No env vars or keys. All data is static JSON. Can't run the service? Use `samples/<facility_id>.json`; they're the exact responses.

## Endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{ok, service, facilities, prices_pulled_at}` |
| GET | `/spend` | `{facilities: [{id, name, spend_overall}]}`, handy for the left rail |
| GET | `/spend/{facility_id}` | `{signals: SignalCard[4]}`; 404 on unknown id |

Every card validates against `packages/schemas/signal-card.schema.json` (checked in tests). Always 4 cards, in this order:

| `signal_type` | What the dashboard needs from it |
|---|---|
| `ref_price_delta` | `headline`, `severity`; **invoice table** = `evidence.line_items` (12 rows: drug, qty, unit_price, reference_price, price_ratio, price_severity, supplier, related_party_supplier, volume_ratio, …) |
| `ownership_overlap` | **graph** = `evidence.ownership_graph` `{nodes, edges, notes}`, vis-network-ready. Nodes `{id, label, type, illustrative, details}` with type ∈ facility/operator/parent/supplier/registered_agent. Edges `{from, to, type, label, related_party}`; draw `related_party: true` in red. `evidence.path` = highlighted path |
| `volume_sanity` | `headline`, `severity`, `evidence.{billed_units, expected_max, ratio, resident_days, assumptions}` |
| `spend_overall` | **Use this for the facility roll-up**, not the 3 individual severities (see below) |

All cards have `data_provenance: "demo_grounded"` and a `citation` (NADAC / facility source / PBJ).

## Scoring (`scoring.py`)

| Signal | Red | Yellow | Green |
|---|---|---|---|
| `ref_price_delta` | worst line > 3× NADAC | 1.5–3× | < 1.5× |
| `ownership_overlap` | a supplier shares an owner with the facility within 3 hops | shared registered agent only | none |
| `volume_sanity` | worst line > 1.5× expected | 1.2–1.5× | ≤ 1.2× |
| `spend_overall` | all 3 red | any red/yellow | all green |

Reference price = **CMS NADAC** (real, pulled 2026-11 via data.medicaid.gov; median per unit across NDCs). ASP wasn't used: it covers Part B injectables, and NADAC covers all 20 drugs.

## Overall facility colour — please use `spend_overall`

The rule "red if any pillar has a red signal" would turn `crook-county-wy-rural` red because of its rural price signal, which breaks the false-positive check. **Dashboard roll-up should take SPEND's contribution from the `spend_overall` card.** Roll-up across pillars stays: red if any pillar red, yellow if any yellow, else green.

## Current results

| Facility | price | ownership | volume | **spend_overall** |
|---|---|---|---|---|
| buffalo-center-centers-health | 🔴 insulin 4.2× | 🔴 Centers Health Care, 3 hops | 🔴 insulin 2.9× | 🔴 |
| accordius-rose-manor-portopiccolo | 🔴 quetiapine 4.5× | 🔴 Portopiccolo, 3 hops | 🔴 quetiapine 2.4× | 🔴 |
| mi-casa-life-care-az | 🟡 Januvia 1.6× | 🟢 | 🟢 | 🟡 |
| crook-county-wy-rural | 🔴 insulin 3.2× (rural) | 🟢 | 🟢 | 🟡 |
| terraces-phoenix-humangood | 🟢 | 🟢 | 🟢 | 🟢 |
| haven-health-green-valley | 🟢 | 🟢 | 🟢 | 🟢 |

Mi Casa is deliberately quiet on SPEND (`worthless_services` lands on VOICE/SHIFT).

## Data (`data/spend/`)

| File | Provenance | Made by |
|---|---|---|
| `prices.json` | **real**: CMS NADAC 2026 | `scripts/pull_prices.py` |
| `line-items.json` | demo_grounded: 12 supplier→facility invoices per facility, Q3 2026 | `scripts/build_demo_data.py` |
| `ownership-graphs.json` | demo_grounded: real parents from facility citations; vendor names illustrative (`illustrative: true`) | `scripts/build_demo_data.py` |
| `census.json` | placeholder: beds × occupancy × 91 days, plus usage assumptions | `scripts/build_demo_data.py` |

Change a story: edit the knobs in `scripts/build_demo_data.py`, re-run it, re-run tests. Swap in real PBJ resident-days (Leo) by editing `census` generation.

## Not owned here
Dashboard UI + vis-network rendering (Dev C), case file, chain. P1: anchor card hashes via `packages/onchain-client` per `HANDOFF.md`.
