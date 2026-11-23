# Abi — context

Role: **Dev A — Phantom Spend** (procurement fraud pillar), **backend-only**. (Saswata's files spell it "Abhi". Same person.)

> **For Saswata / Leo (and your agents):** I've read `contexts/answers-to-abi.md` and I'm building to it. SPEND is a FastAPI service in `apps/phantom-spend/` on port 8003, exposing `GET /spend/{facility_id}` → `{ signals: SignalCard[] }` per `packages/schemas/signal-card.schema.json`, keyed off the locked `data/facilities.json` ids. **Dev C draws the ownership graph** from `evidence.ownership_graph`; I don't write any UI. **I won't change shared schemas or `facilities.json`.**
>
> **Saswata, please read "Replies to answers-to-abi.md" below.** One change affects your dashboard roll-up (the `spend_overall` card).

---

## Status — SPEND P0 backend is DONE (Nov 22, evening)

**`GET :8003/spend/{facility_id}` is live, with 17 tests passing.** Saswata: you can build the SPEND tab now. Run instructions and the full response contract are in `apps/phantom-spend/README.md`. Can't run it? `apps/phantom-spend/samples/<facility_id>.json` are the exact responses.

| Facility | price | ownership | volume | **spend_overall** |
|---|---|---|---|---|
| `buffalo-center-centers-health` | 🔴 insulin 4.2× NADAC | 🔴 shares owner Centers Health Care | 🔴 insulin 2.9× | 🔴 |
| `accordius-rose-manor-portopiccolo` | 🔴 quetiapine 4.5× | 🔴 shares owner Portopiccolo | 🔴 quetiapine 2.4× | 🔴 |
| `mi-casa-life-care-az` | 🟡 Januvia 1.6× | 🟢 | 🟢 | 🟡 |
| `crook-county-wy-rural` | 🔴 insulin 3.2× (rural) | 🟢 | 🟢 | 🟡 ← rural check works |
| `terraces-phoenix-humangood` | 🟢 | 🟢 | 🟢 | 🟢 |
| `haven-health-green-valley` | 🟢 | 🟢 | 🟢 | 🟢 |

### Progress log
- **Real prices pulled:** 20 nursing-home drugs from **CMS NADAC 2026** (data.medicaid.gov API, effective 2026-11-18) → `data/spend/prices.json`. Unit-normalised (insulin per 10 mL vial, enoxaparin per 0.4 mL syringe). **Changed from plan: no CMS ASP**, which covers Part B injectables only; NADAC covers all 20 drugs. Example: insulin lispro $24.03/vial, Eliquis 5 mg $5.52/tablet.
- **Demo data generated** by `scripts/build_demo_data.py` from per-facility settings, so numbers stay consistent: `line-items.json` (6 × 12 invoices, Q3 2026), `ownership-graphs.json` (real parents from facility citations, fictional vendor names flagged `illustrative: true`), `census.json` (placeholder resident-days + usage assumptions).
- **Scoring** (`scoring.py`): 3 signals + `spend_overall`, thresholds as below.
- **Cards + API** (`cards.py`, `main.py`): 4 schema-valid cards per facility; `GET /health`, `GET /spend`, `GET /spend/{id}`.
- **Tests** (`test_scoring.py`): expected colours for all 6, every card validated against `packages/schemas/signal-card.schema.json`, graph drawable, 12 table rows, 404 on unknown id.
- **Tested locally by Abi** via curl: output matches the table above.

### What's next
- [ ] Saswata: build the SPEND tab against the endpoint/samples; use `spend_overall` for the roll-up
- [ ] Leo: send PBJ resident-days → I swap them into `census.json` and re-check colours
- [ ] Optional: Cost Plus Drugs prices as a second reference column
- [ ] P1: anchor card hashes via `packages/onchain-client`; cost-report CSV upload endpoint
- [ ] Possible wording tweak: ownership headline says "3 hops", which could read "shares an owner"

---

## Replies to `answers-to-abi.md` (decisions — Nov 22)

### 1. Real facility names with authored SPEND evidence: DEFERRED
I'm going with the 6 real facilities as locked. Invoices, markups and volumes on SPEND are authored by us. Concern noted (it shows invented numbers under real names), but we've decided to defer it for the demo. Revisit only if time allows (fallback: "modelled on …" fictional names for the 2 SPEND-red facilities).

### 2. Dashboard roll-up: SPEND returns a pillar-level `spend_overall` card — ACTION FOR SASWATA
The rule "red if any pillar has a red signal" turns `crook-county-wy-rural` red, because its price signal is red, and that breaks the rural false-positive check. Fix:

- `/spend/{facility_id}` returns **one extra card** with `signal_type: "spend_overall"`:
  - **red** = all 3 SPEND signals red
  - **yellow** = at least one SPEND signal red or yellow, but not all 3 red
  - **green** = all 3 green
- **Dashboard roll-up: use the `spend_overall` card as SPEND's contribution** and ignore the three individual SPEND signal severities when computing the left-rail facility colour. Individual cards still render in the SPEND tab.
- `crook-county-wy-rural` → `spend_overall: yellow` → stays yellow as long as SHIFT/VOICE have no reds for it.

### 3. `data_provenance`: `demo_grounded` for price-gap and volume cards
Only the *reference* side is real (CMS ASP/NADAC prices, PBJ resident-days). The *facility* side (invoice prices, units bought) is authored. So:

| Card | `data_provenance` | `citation` |
|---|---|---|
| `ref_price_delta` | `demo_grounded` | CMS ASP / NADAC file URL |
| `ownership_overlap` | `demo_grounded` | the facility's `citation` from `facilities.json` (NY AG / ProPublica / CMS) |
| `volume_sanity` | `demo_grounded` | PBJ dataset URL |
| `spend_overall` | `demo_grounded` | — |

`real` is reserved for cards built **entirely** from public data (none on SPEND at P0).

---

## How I'm building SPEND

### Architecture
- **FastAPI service**, `apps/phantom-spend/`, port **8003**. Backend only.
- **Static data, no live fetching at demo time.** Signals are computed on each request from JSON in `data/spend/`, so it's fast and survives bad WiFi.
- **One-off Python script** pulls real CMS NADAC prices into `data/spend/prices.json` (ASP dropped; see progress log).
- **No chain anchoring at P0.** P1 option: `packages/onchain-client` → `commit(CLAIM_SIGNAL_CARD, hash)` per `HANDOFF.md`.
- **Framing:** rows are **supplier → facility invoices that feed the cost report** (CMS Form 2540, Worksheet A-8-1), not Medicaid claim lines. Part A has no drug line items (see `02-fraud-research-brief.md`).

### Files
```
apps/phantom-spend/
  main.py                 ← FastAPI: GET /health, GET /spend, GET /spend/{facility_id}; CORS open
  scoring.py              ← ref_price_delta, ownership_overlap, volume_sanity, spend_overall
  cards.py                ← builds schema-valid SignalCards
  test_scoring.py         ← expected colour per facility + schema validation
  requirements.txt
  scripts/pull_prices.py  ← one-time: CMS NADAC → data/spend/prices.json
  scripts/build_demo_data.py ← generates line-items / ownership-graphs / census from per-facility settings
  samples/<id>.json       ← saved responses for the dashboard
data/spend/
  prices.json             ← 20 drugs: NADAC (real, source URL + effective date)
  line-items.json         ← 6 facilities × 12 invoice rows (authored)
  ownership-graphs.json   ← 6 graphs: nodes + edges + notes (authored, grounded in facility citations)
  census.json             ← resident-days per facility (placeholder → Leo's PBJ numbers)
```
`data/facilities.json` and `packages/schemas/` are read-only for me.

### Response shape — `GET /spend/{facility_id}`
```json
{
  "signals": [
    {
      "signal_id": "spend-ref_price_delta-buffalo-center-centers-health-L003",
      "pillar": "spend",
      "signal_type": "ref_price_delta",
      "facility_id": "buffalo-center-centers-health",
      "severity": "red",
      "headline": "Eliquis 5mg invoiced at 4.1× CMS ASP",
      "detail": "...",
      "data_provenance": "demo_grounded",
      "evidence": { "line_id": "L003", "ndc": "...", "unit_price": 0, "asp": 0, "nadac": 0,
                    "ratio": 4.1, "supplier": "...", "line_items": [ ] },
      "citation": { "source": "CMS ASP pricing file", "url": "https://www.cms.gov/..." },
      "computed_at": "2026-11-22T20:00:00Z"
    },
    { "signal_type": "ownership_overlap",
      "evidence": { "hops": 2, "shared_node": "...", "path": [ ],
                    "ownership_graph": { "nodes": [ ], "edges": [ ], "notes": "..." } } },
    { "signal_type": "volume_sanity",
      "evidence": { "drug": "...", "billed_units": 0, "expected_max": 0, "ratio": 2.9,
                    "resident_days": 0, "assumptions": { } } },
    { "signal_type": "spend_overall", "severity": "red",
      "evidence": { "ref_price_delta": "red", "ownership_overlap": "red", "volume_sanity": "red" } }
  ]
}
```
- Exactly one card each for `ref_price_delta` (the worst line; all 12 rows in `evidence.line_items` for the table), `ownership_overlap`, `volume_sanity` and `spend_overall`.
- Graph nodes/edges are vis-network-ready: `{ id, label, type, details }`, `{ from, to, label, related_party }`.
- Unknown facility id → 404.

### Scoring rules (thresholds from `apps/phantom-spend/README.md`)
| Signal | Red | Yellow | Green |
|---|---|---|---|
| `ref_price_delta` | worst unit price > 3× NADAC | 1.5–3× | < 1.5× |
| `ownership_overlap` | supplier shares an ancestor with the facility within 3 hops | shared registered agent / address only | no overlap |
| `volume_sanity` | billed > 1.5× expected max | 1.2–1.5× | ≤ 1.2× |
| `spend_overall` | all 3 red | some red/yellow, not all 3 red | all green |

### The 6 facilities (locked `data/facilities.json`)
| id | Beds | SPEND story | Expected `spend_overall` |
|---|---|---|---|
| `buffalo-center-centers-health` (NY) | 200 | **Hero.** Owner-controlled vendor LLCs under Centers Health Care (per NY AG complaint); ~3 big markups; ~2.9× volume | 🔴 red |
| `accordius-rose-manor-portopiccolo` (NC) | 111 | Captive pharmacy vendor under Portopiccolo; high pharmacy markups + over-volume | 🔴 red |
| `mi-casa-life-care-az` (AZ) | 180 | Boring. Maybe one modest markup, no ownership overlap. (Red comes from VOICE/SHIFT) | 🟡 or 🟢 |
| `crook-county-wy-rural` (WY) | 32 | +180% markups on 2 items (thin frontier market), county-district owner, normal volume | 🟡 yellow |
| `terraces-phoenix-humangood` (AZ) | 64 | Near-reference prices, unrelated suppliers | 🟢 green |
| `haven-health-green-valley` (AZ) | 111 | Same | 🟢 green |

**Volume maths** (realistic; fixes `03-demo-plan.md`): resident-days ≈ beds × ~90% occupancy × 91 days. E.g. Buffalo: 200 beds → ~180 residents → ~16,400 resident-days/quarter → ~36 insulin users × ~4.5 vials → expected max ~160 vials; billed ~470 → **2.9×**. Assumptions are returned in `evidence.assumptions`; swapped for Leo's PBJ numbers when available.

---

## Build plan

| # | Step | Work | Done when |
|---|---|---|---|
| 1 | Service skeleton | `main.py` with `/health` + stub `/spend/{id}`, `requirements.txt`, CORS | `curl :8003/health` ok |
| 2 | Real prices | `pull_prices.py`: CMS ASP + NADAC for ~20 drugs, unit-normalised; Abi hand-pulls ~10 Cost Plus prices | `data/spend/prices.json` with sources |
| 3 | Census | `census.json` from bed counts (placeholder) | 6 rows |
| 4 | Ownership graphs | `ownership-graphs.json` for 6 facilities, grounded in each facility's citation | Buffalo + Accordius show related-party path |
| 5 | Line items | `line-items.json`, 6 × 12 rows matching the stories above | Reviewed by Abi |
| 6 | Scoring | `scoring.py`: 3 signals + `spend_overall` | Unit tests pass |
| 7 | Cards + API | `cards.py` + wire `/spend/{id}`; validate every card against the schema | All 6 return schema-valid cards with the expected colours |
| 8 | Hand-off | Tell Saswata the endpoint is live; sample responses committed | Dashboard renders SPEND |
| 9 | PBJ swap | Replace placeholder census with Leo's numbers; re-check colours | Tests still pass |
| 10 | P1 | Signal-card chain anchoring; intake CSV-upload endpoint | — |
| 11 | Rehearse | Q&A prep, dry run | — |

**Cut order if behind:** ZK stretch → chain anchoring → intake upload → Cost Plus column.

---

## Task checklist (mirrors Dev A in `saswata.md`, UI tasks moved to Dev C)

### P0 — Must ship
- [x] 1. ~~CMS ASP~~ → replaced by NADAC (ASP covers Part B injectables only)
- [x] 2. NADAC for 20 drugs → `data/spend/prices.json`
- [ ] 3. Hand-pull 10 Cost Plus Drugs prices (optional now)
- [x] 4. Author line items: 6 facilities × 12 rows
- [x] 5. Author ownership graphs for 6 facilities
- [x] 6. Scoring: reference-price delta
- [x] 7. Scoring: ownership overlap
- [x] 8. Scoring: volume-vs-census
- [x] 12. Rural case: `crook-county-wy-rural` → `spend_overall` yellow
- [x] (new) `spend_overall` card + `GET /spend/{id}` returning schema-valid cards
- ~~9–11. SPEND tab table, signal cards, vis-network graph~~ → **Dev C** (per `answers-to-abi.md`). I supply the data in `evidence`.

### P1 — Should ship
- [ ] 13. Cost-report CSV upload (backend endpoint; Dev C hosts the widget)
- [x] 14. Citation on every card (built into the card builder)
- [ ] Anchor signal-card hashes via `packages/onchain-client`

### P2 — Stretch (cut first)
- [ ] 16. ZK invoice-integrity proof in Noir

---

## Other dependencies
| From | What | Needed by | If late |
|---|---|---|---|
| Saswata | Dashboard roll-up uses `spend_overall` (decision 2 above) | Before dry run | Rural tile turns red |
| Leo | Real PBJ resident-days per facility (Dev B #1) | Before dry run | Labelled placeholder in `data/spend/census.json` |
| Saswata | Onchain service (mock mode is fine) | P1 only | Skip anchoring |

## Q&A I own
Procurement fraud, reference prices, PE nursing-home chains, PECOS / ownership opacity, "why not just NADAC."
- **"Rural homes pay more?"** → `crook-county-wy-rural`: price-only red stays yellow.
- **"Invoices aren't public?"** → Public cost reports flag which homes to examine → MFCU subpoenas invoices → tool fuses the signals.
- **Legal hook:** 42 CFR 413.17 ("prudent buyer" / related-party cost rule) lets CMS disallow related-party markups.

## What I do NOT own
- All UI, including the SPEND tab and ownership-graph rendering (Dev C).
- Dashboard shell, shared schemas, `data/facilities.json`, onchain service, Voice, Case File (Saswata / Dev C).
- SHIFT pillar (Leo / Dev B).

## Open questions
- **Headline stats** for the pitch need sources: "$12B/yr" (is it really NBER w28474?) and "~$90B Medicaid to nursing homes."
- **ASP units:** ASP is per HCPCS billing unit, not per vial. Normalising and recording the conversion.
- **Team docs drift:** `AGENTS.md` / `01-project-brief.md` still say "no chain, staffing out", which contradicts `HANDOFF.md` + `saswata.md`.

## Decisions I've made
- (Nov 22) Taking Dev A — Phantom Spend.
- (Nov 22, updated) Building to the locked scaffold: FastAPI `apps/phantom-spend` on :8003, data in `data/spend/`.
- (Nov 22, updated) Backend-only. Dev C renders the SPEND tab + graph from my card `evidence`.
- (Nov 22) SPEND returns a `spend_overall` card; the dashboard should roll up from it.
- (Nov 22) Price-gap, volume, ownership and overall cards are `data_provenance: "demo_grounded"`.
- (Nov 22) Real-facility-names concern deferred for the demo.
- (Nov 22) Rural safety case is `crook-county-wy-rural` (WY).
- (Nov 22) Reference price = CMS NADAC only (dropped ASP).
- (Nov 22) Demo data is generated from settings in `scripts/build_demo_data.py`, not hand-typed; edit the settings and re-run.

## TODO sections (for teammates to drop asks here)

(add your TODO sections at the bottom using the format in `contexts/README.md`)

## TODO from Leo — PBJ data handoff for volume_sanity

### [ ] TODO 1 — Share the 6 facility CCNs and quarterly PBJ resident-day numbers as soon as Task 1 finishes (P0, ~immediate)

The `volume_sanity` scoring function is blocked on the exact shared facility identifiers and resident-day values. Send the finalized six-row dataset in the same shape as `facilities.json` once Leo Task 1 is complete.
