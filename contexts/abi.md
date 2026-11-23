# Abi — context

Role: **Dev A — Phantom Spend** (procurement fraud pillar). Taking the open Dev A seat from `contexts/saswata.md`. (Saswata's files spell it "Abhi". Same person.)

> **For Saswata / Leo (and your agents):** I'm building SPEND to match the locked scaffold in `HANDOFF.md`. That means a FastAPI service in `apps/phantom-spend/` on port 8003, exposing `GET /spend/{facility_id}` → `{ signals: SignalCard[] }` per `packages/schemas/signal-card.schema.json`, keyed off the locked `data/facilities.json`. **I won't change shared schemas or `facilities.json`.** Open questions for Saswata are in **"Asks for Saswata"** below. None of them block me starting.

---

## Asks for Saswata

### [ ] ASK 1 — Who renders the SPEND tab and ownership graph? (P0, needed by H3, ~2 min)

`apps/phantom-spend/README.md` says **Dev C draws the vis-network**. `apps/dashboard/README.md` says SPEND is **"Abhi renders via Dev C's shell."** The graph is the demo's photographable moment, so one person has to own it.

My proposal: **I build the SPEND tab component** (signal cards, invoice table, vis-network ownership graph) as a drop-in for your shell, so you can focus on VOICE + CASE FILE. I need from you:
```html
<section id="tab-spend"></section>     <!-- where my component mounts -->
```
```js
Alpine.store('app').selectedFacility    // facility id; SPEND re-renders on change
```
If you'd rather draw it yourself, I'll put everything you need in the response (see "Response shape" below).

### [ ] ASK 2 — Small schema/data clarifications (P0, needed by H1, ~5 min)

1. **Synthetic labelling.** `SignalCard` has no `synthetic` field, and the team rule says made-up data must be labelled in the UI. I'll put `evidence.synthetic: true` on cards built from authored invoices/graphs. Please render an "illustrative" badge when it's set.
2. **Overall severity.** `signal_type` for spend lists only `ref_price_delta | ownership_overlap | volume_sanity`. I'll also return a top-level `overall` field in the response (red only when all 3 are red; price-only red → yellow). Is that OK, or do you compute overall in CASE FILE?
3. **CCNs may be real facilities.** `035123`, `035091`, `035217`, `275012`, `505071`, `385118` use real state prefixes. If any is a live CCN, the demo accuses a real nursing home of fraud. Can you check them against Nursing Home Compare, or switch to obviously fake ones? I'll do the lookup myself during the data pull and report back.
4. **`phoenix-memory-care` = `worthless_services`.** That isn't a pricing pattern. My plan: it goes red on SPEND through **volume_sanity** (billed wound-care/incontinence supplies far beyond what 60 beds could use, i.e. billed-but-not-delivered) plus a related-party supplier. OK?

---

## How I'm building SPEND

### Architecture (matches `HANDOFF.md`)
- **FastAPI service**, `apps/phantom-spend/`, port **8003**.
- **Static data, no live fetching at demo time.** Scores are computed from JSON in `data/spend/` at request time, so it's fast and survives bad WiFi.
- **Python one-off script** pulls real CMS ASP + NADAC prices into `data/spend/prices.json`.
- **No chain anchoring at P0.** P1 option: `packages/onchain-client` → `commit(CLAIM_SIGNAL_CARD, hash)` per `HANDOFF.md`.
- **Framing:** rows are **supplier → facility invoices that feed the cost report** (CMS Form 2540, Worksheet A-8-1), *not* Medicaid claim lines. Part A has no drug line items (see `02-fraud-research-brief.md`).

### Files I'm creating
```
apps/phantom-spend/
  main.py               ← FastAPI: GET /spend/{facility_id}, GET /health
  scoring.py            ← 3 signal functions + combine()
  test_scoring.py       ← asserts expected colour for all 6 facilities
  requirements.txt
  scripts/pull_prices.py← one-time: CMS ASP + NADAC → data/spend/prices.json
  spend-tab.html        ← SPEND tab component (if ASK 1 = me)
  .env.example          ← only if a key is ever needed (none planned)
data/spend/
  prices.json           ← ~20 drugs: ASP, NADAC, Cost Plus (real, with source URL + date)
  line-items.json       ← 6 facilities × 12 invoice rows (synthetic)
  ownership-graphs.json ← 6 graphs: nodes + edges (illustrative; ProPublica-grounded)
  census.json           ← resident-days per facility (placeholder until Leo's PBJ lands)
```
`data/facilities.json` is read-only for me.

### Response shape — `GET /spend/{facility_id}`
```json
{
  "facility_id": "sunrise-valley",
  "overall": "red",
  "signals": [
    {
      "signal_id": "spend-ref_price_delta-sunrise-valley-L003",
      "pillar": "spend",
      "signal_type": "ref_price_delta",
      "facility_id": "sunrise-valley",
      "severity": "red",
      "headline": "Eliquis 5mg invoiced at 4.1× CMS ASP",
      "detail": "...",
      "evidence": { "line_id": "L003", "ndc": "...", "unit_price": 0, "asp": 0, "nadac": 0,
                    "ratio": 4.1, "line_items": [ ], "synthetic": true },
      "citation": { "source": "CMS ASP Q4 2026", "url": "https://www.cms.gov/..." },
      "computed_at": "2026-11-22T20:00:00Z"
    },
    { "signal_type": "ownership_overlap", "evidence": { "hops": 2, "shared_node": "...",
      "path": [ ], "graph": { "nodes": [ ], "edges": [ ] }, "synthetic": true } },
    { "signal_type": "volume_sanity", "evidence": { "billed_units": 0, "expected_max": 0,
      "ratio": 2.9, "resident_days": 0, "assumptions": { }, "synthetic": true } }
  ]
}
```
- One `ref_price_delta` card per flagged line (worst first). Green lines appear only in `evidence.line_items` for the table.
- The `ownership_overlap` card carries the full vis-network-ready `graph`, so whoever draws it needs nothing else.

### Scoring rules (`scoring.py`, thresholds from `apps/phantom-spend/README.md`)
| Signal | Red | Yellow | Green |
|---|---|---|---|
| `ref_price_delta` | unit price > 3× ASP | 1.5–3× | < 1.5× |
| `ownership_overlap` | supplier shares an ancestor/registered agent with facility within 3 hops | shared agent only, > 3 hops | no overlap |
| `volume_sanity` | billed > 1.5× expected max | 1.2–1.5× | ≤ 1.2× |
| **overall** | **all 3 red** | any red, but not all 3 (Montana rule) | none red |

### The 6 facilities (from locked `data/facilities.json`)
| id | Beds | Scenario | SPEND story | Expected |
|---|---|---|---|---|
| `sunrise-valley` (AZ) | 120 | `pe_owned_fraud` | Sister-LLC supplier under Meridian Holdings; big markups on insulin/Eliquis/Jardiance; ~2.9× volume | 🔴 |
| `desert-palms` (AZ) | 95 | `pharmacy_kickback` | Related LTC pharmacy under Saguaro Senior Partners; markups + overdispensing | 🔴 |
| `phoenix-memory-care` (AZ) | 60 | `worthless_services` | Wound-care/incontinence supplies billed far beyond census (billed-not-delivered) from related supplier | 🔴 (see ASK 2.4) |
| `big-sky-rural` (MT) | 35 | `rural_ambiguous` | High prices (thin rural market), independent supplier, normal volume | 🟡 |
| `pine-valley` (WA) | 110 | `clean_baseline` | Near-reference prices, unrelated suppliers, normal volume | 🟢 |
| `lakeview` (OR) | 80 | `clean_baseline` | Same | 🟢 |

- ~70% of each fraud home's rows are priced normally, so the fraud looks realistic.
- Ownership graphs for the red homes are modelled on real reported structures (Portopiccolo, Centers Health Care, from ProPublica / NY AG reporting) with fictional names.
- **Realistic volume maths** (fixes `03-demo-plan.md`, where 4,210 resident-days ≈ 46 residents, not 1,050 diabetics): resident-days ≈ beds × ~90% occupancy × 91 days, so `sunrise-valley` ≈ 9,800/quarter ≈ 108 residents. ~20 insulin users × ~4–5 vials/quarter → expected max ~110 vials. Billed ~320 → **2.9×**. Assumptions returned in `evidence.assumptions`; swapped for Leo's real PBJ numbers when available.

### SPEND tab UI (if ASK 1 = me)
1. Three signal cards (price gap / ownership / volume) plus the overall badge, each with a `citation` footer.
2. Invoice table from `evidence.line_items`: 12 rows, flagged rows highlighted. Header reads "Supplier invoices → cost report".
3. vis-network ownership graph from `evidence.graph`: related-party edge in red, tooltips (LLC, state, registered agent), labelled as demo data grounded in ProPublica reporting. **Most polish time goes here.**
4. "Illustrative" badge wherever `evidence.synthetic` is true.

---

## Build plan (6h)

| Time | Step | Work | Done when |
|---|---|---|---|
| 0:00–0:15 | 1. Align | Send ASK 1 + ASK 2 to Saswata | Answers in, or proceed with my proposals |
| 0:15–0:45 | 2. Real prices | `pull_prices.py`: ASP + NADAC for ~20 drugs, unit-normalised; hand-pull 10 Cost Plus prices; check the 6 CCNs | `data/spend/prices.json` with sources |
| 0:45–2:00 | 3. Author data | `line-items.json`, `ownership-graphs.json`, `census.json` for the 6 facilities (slowest step) | Stories reviewed, names clearly fictional |
| 2:00–3:00 | 4. Scoring + API | `scoring.py`, `main.py`, `test_scoring.py` | `curl :8003/spend/<id>` gives schema-valid cards; all 6 colours correct; Montana = yellow |
| 3:00–4:30 | 5. SPEND UI | Cards + table + ownership graph against the live endpoint | Clickable end to end |
| 4:30–5:15 | 6. Integrate | Mount in Saswata's shell; CASE FILE pulls my cards; swap in Leo's PBJ numbers | Works inside the dashboard |
| 5:15–6:00 | 7. Rehearse | Team dry run, Q&A practice, deck screenshots | — |

**Cut order if behind:** ZK stretch → signal-card chain anchoring → graph tooltips → intake upload widget → (last resort) static graph image.

---

## Task checklist (mirrors Dev A in `saswata.md`)

### P0 — Must ship
- [ ] 1. CMS ASP quarterly file → lookup table for ~20 common SNF drugs
- [ ] 2. NADAC (Socrata) for the same drugs, joined to the ASP table
- [ ] 3. Hand-pull 10 Cost Plus Drugs prices
- [ ] 4. Author line items: 6 facilities × 12 rows — **start first**
- [ ] 5. Author ownership graphs for 6 facilities — **start first**
- [ ] 6. Scoring: reference-price delta
- [ ] 7. Scoring: ownership overlap
- [ ] 8. Scoring: volume-vs-census
- [ ] 9. SPEND tab: 12-row line-item table
- [ ] 10. Three signal cards above the table
- [ ] 11. vis-network ownership graph on clicking a flagged row
- [ ] 12. Montana rural case → overall yellow

### P1 — Should ship
- [ ] 13. Cost-report CSV upload widget on intake page (mock: hash + console log)
- [ ] 14. Citation footer on each signal card
- [ ] 15. Hover tooltips on ownership graph nodes
- [ ] (new) Anchor signal-card hashes via `packages/onchain-client` (per `HANDOFF.md`)

### P2 — Stretch (cut first)
- [ ] 16. ZK invoice-integrity proof in Noir

### Checkpoints
- [ ] H0 — ASK 1 + ASK 2 sent to Saswata
- [ ] H1 — `data/spend/` drafts in repo; CCNs checked
- [ ] H2 — `/spend/{id}` returns schema-valid cards with correct colours for all 6
- [ ] H3 — SPEND UI works end to end against the endpoint
- [ ] H4 — mounted in shell; CASE FILE pulls my cards
- [ ] H5 — full-team dry run

---

## Other dependencies
| From | What | Needed by | If late |
|---|---|---|---|
| Leo | Real PBJ resident-days per facility (Dev B #1) | H2 | Labelled placeholder in `data/spend/census.json` |
| Saswata | Dashboard shell + `#tab-spend` + `selectedFacility` (Dev C #5–7) | H3 | Test SPEND UI standalone against :8003 |
| Saswata | Intake page widget slot (Dev C #8) | P1 only | Skip widget |
| Saswata | Onchain service (mock mode is fine) | P1 only | Skip anchoring |

## Q&A I own
Procurement fraud, reference prices, PE nursing-home chains, PECOS / ownership opacity, "why not just NADAC."
- **"Rural homes pay more?"** → Show `big-sky-rural`: price-only red stays yellow.
- **"Invoices aren't public?"** → Public cost reports flag which homes to examine → MFCU subpoenas invoices → tool fuses the signals.
- **Legal hook:** 42 CFR 413.17 ("prudent buyer" / related-party cost rule) lets CMS disallow related-party markups.

## What I do NOT own
- Dashboard shell, tab routing, shared schemas, `data/facilities.json`, onchain service, Voice, Case File (Saswata / Dev C).
- SHIFT pillar (Leo / Dev B).

## Open questions
- **Headline stats** for the pitch need sources: "$12B/yr" (is it really NBER w28474?) and "~$90B Medicaid to nursing homes."
- **ASP units:** ASP is per HCPCS billing unit, not per vial. Normalising and recording the conversion. If insulin turns out weak as the headline example, lead with a higher-gap drug (e.g. Eliquis).
- **Team docs drift:** `AGENTS.md` / `01-project-brief.md` still say "no chain, staffing out", which contradicts `HANDOFF.md` + `saswata.md`.

## Decisions I've made
- (Nov 22) Taking Dev A — Phantom Spend.
- (Nov 22, updated) Building to the locked scaffold: FastAPI `apps/phantom-spend` on :8003, data in `data/spend/`. *Replaces my earlier in-browser-JS plan.*
- (Nov 22) Rural safety case is `big-sky-rural` (MT).
- (Nov 22) Invoice rows framed as supplier → facility invoices feeding the cost report, not Medicaid claims.

## TODO sections (for teammates to drop asks here)

(add your TODO sections at the bottom using the format in `contexts/README.md`)

## TODO from Leo — PBJ data handoff for volume_sanity

### [ ] TODO 1 — Share the 6 facility CCNs and quarterly PBJ resident-day numbers as soon as Task 1 finishes (P0, ~immediate)

The `volume_sanity` scoring function is blocked on the exact shared facility identifiers and resident-day values. Send the finalized six-row dataset in the same shape as `facilities.json` once Leo Task 1 is complete.
