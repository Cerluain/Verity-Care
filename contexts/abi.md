# Abi — context

Role: **Dev A — Phantom Spend** (procurement fraud pillar). Taking the open Dev A seat from `contexts/saswata.md`.

> **For Saswata / Leo (and your agents):** I own the whole SPEND module: data, scoring and SPEND-tab UI. It runs **standalone** (static JSON + in-page JS, no server) and mounts into Saswata's shell at the end. The two things I need from Saswata are in **"Asks for Saswata"** just below. Everything else I can do without blocking on anyone.

---

## Asks for Saswata (the 2 things I need)

### [ ] ASK 1 — Lock the shared data contracts: `facilities.json` + `signal-card.schema.json` (P0, needed by H1, ~15 min of your time)

Your Dev C task #4. My SPEND data and scoring key off the facility ids, and your CASE FILE consumes my signal cards. If our shapes differ, nothing joins up later.

- **`facilities.json`**: the 6 facility ids, names, CCNs and states. I'll draft it at H0 (3 fraud, 1 Montana rural, 2 clean) and send it to you. Reply "use yours" or send me your ids.
- **`signal-card.schema.json`**: proposed shape below. Reply "ok" or edit it.

```json
{
  "pillar": "spend",                    // "spend" | "shift" | "voice"
  "facility_id": "sunrise-valley",
  "signal": "ref_price_delta",          // "ref_price_delta" | "ownership_overlap" | "volume_sanity" | "overall"
  "severity": "red",                    // "red" | "yellow" | "green"
  "headline": "+412% vs CMS ASP on Eliquis 5mg",
  "evidence": { },                      // signal-specific detail (line ids, ratios, graph path)
  "sources": [{ "label": "CMS ASP Q4 2026", "url": "https://www.cms.gov/..." }],
  "synthetic": false                    // true → UI shows "illustrative" badge
}
```

**If late:** I build against my draft and you adopt it.

### [ ] ASK 2 — Dashboard shell: the SPEND tab mount point + how the selected facility is passed (P0, needed by H3)

Your Dev C tasks #5–7. I need to know where my tab goes and how I hear which facility the left rail selected.

Proposed contract:
```html
<section id="tab-spend"></section>   <!-- I inject spend-tab.html here -->
```
```js
Alpine.store('app').selectedFacility   // facility_id string; SPEND re-renders when it changes
```
In return, CASE FILE calls:
```js
getSpendSignals(facilityId) // → SignalCard[]  (from apps/dashboard/spend.js)
```

**If late:** I demo from my standalone `apps/dashboard/spend-dev.html` (same UI) and mount later.

---

## How I'm building SPEND

### Architecture
- **No server for SPEND.** The page loads static JSON and does all scoring in the browser (`spend.js`), so it works offline if venue WiFi dies.
- **Python only for the one-time price pull** (`scripts/spend/pull_prices.py` → `prices.json`).
- **Real vs synthetic is explicit:** prices are real public data with source URLs. Invoices and ownership graphs are synthetic, carry `"synthetic": true`, and show an "illustrative" badge in the UI.
- **Framing:** rows are **supplier → facility invoices that feed the cost report** (CMS Form 2540, Worksheet A-8-1), *not* Medicaid claim lines. Part A has no drug line items (see `02-fraud-research-brief.md`).

### Files I'm creating
```
scripts/spend/
  pull_prices.py        ← one-time: CMS ASP + NADAC → prices.json
apps/dashboard/
  data/spend/
    prices.json         ← ~20 drugs: ASP, NADAC, Cost Plus (real, with source URL + date)
    facilities.json     ← 6 facilities: id, name, CCN, state, beds, resident-days (draft until ASK 1)
    line_items.json     ← 6 × 12 invoice rows (synthetic)
    ownership.json      ← 6 ownership graphs: nodes + edges (illustrative)
  spend.js              ← 3 scoring functions + getSpendSignals()
  spend-tab.html        ← table + 3 signal cards + ownership graph (mounts into #tab-spend)
  spend-dev.html        ← standalone test page
```

### Scoring logic (`spend.js`)
```js
refPriceDelta(lineItem, prices)        // markup % vs ASP/NADAC → red >200%, yellow >50%, else green
ownershipOverlap(facility, supplier, graph) // shared parent LLC / registered agent? → hop count + severity
volumeSanity(lineItems, facility)      // units bought vs (residents × usage rate) → overbill ratio
combine(signals)                       // RED only if all 3 red; price-only red → YELLOW (Montana rule)
getSpendSignals(facilityId)            // → SignalCard[] for SPEND tab + CASE FILE
```

### The 6 facilities
| Facility | Story | Expected |
|---|---|---|
| 3 fraud homes | Big markups on 3–4 high-volume drugs; supplier shares parent LLC + registered agent; volume ~3× plausible | 🔴 red |
| Montana rural | Big markups, but independent supplier and normal volume | 🟡 yellow |
| 2 clean homes | Near-reference prices, unrelated suppliers, normal volume | 🟢 green |

- ~70% of each fraud home's rows are priced normally, so the fraud looks realistic.
- Two fraud ownership graphs are modelled on real reported structures (Portopiccolo, Centers Health Care, from ProPublica / NY AG reporting) with fictional entity names.
- **Realistic volume numbers** (fixes the `03-demo-plan.md` maths): 120 beds × ~90% occupancy ≈ 108 residents ≈ 9,800 resident-days/quarter. ~20 insulin users × ~4–5 vials/quarter → expected max ~110 vials. Billed ~320 → **2.9×**. Swapped for Leo's real PBJ numbers when available.

### SPEND tab UI
1. Three signal cards (price gap / ownership / volume): colour, headline, "Source: …" link.
2. Invoice table: 12 rows, flagged rows highlighted. Header reads "Supplier invoices → cost report".
3. Ownership graph (vis-network): click a flagged row to draw facility → parent LLC → supplier, with the related-party edge in red and tooltips (LLC, state, registered agent). **Most polish time goes here.**
4. "Illustrative / synthetic" badges on everything that isn't real public data.

---

## Build plan (6h)

| Time | Step | Work | Done when |
|---|---|---|---|
| 0:00–0:15 | 1. Contracts | Draft `facilities.json` + signal-card shape, send to Saswata (ASK 1) | Saswata says ok, or we proceed with mine |
| 0:15–0:45 | 2. Real prices | `pull_prices.py`: ASP + NADAC for ~20 drugs, unit-normalised; I hand-pull 10 Cost Plus prices | `prices.json` with sources |
| 0:45–2:00 | 3. Author data | `line_items.json` + `ownership.json` for 6 facilities (slowest step) | Stories reviewed, names clearly fictional |
| 2:00–3:00 | 4. Scoring | 3 signal functions + `combine` + `getSpendSignals`, plus a check of all 6 colours | All 6 match the table above, Montana = yellow |
| 3:00–4:30 | 5. SPEND UI | Cards + table + ownership graph in `spend-dev.html` | Clickable end to end, standalone |
| 4:30–5:15 | 6. Integrate | Mount into `#tab-spend`, listen to `selectedFacility`, CASE FILE pulls my cards (ASK 2) | Works inside the shell |
| 5:15–6:00 | 7. Rehearse | Team dry run, Q&A practice, deck screenshots | — |

**Cut order if behind:** ZK stretch → graph tooltips → intake upload widget → citation footers → (last resort) static graph image.

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

### P2 — Stretch (cut first)
- [ ] 16. ZK invoice-integrity proof in Noir

### Checkpoints
- [ ] H0 — ASK 1 sent to Saswata
- [ ] H1 — data drafts in repo; facility ids match Saswata's
- [ ] H2 — `getSpendSignals` returns correct colours for all 6
- [ ] H3 — standalone SPEND page works end to end
- [ ] H4 — mounted in shell (ASK 2); CASE FILE pulls my cards
- [ ] H5 — full-team dry run

---

## Other dependencies
| From | What | Needed by | If late |
|---|---|---|---|
| Leo | Real PBJ resident-days per facility CCN (Dev B #1) | H2 | Labelled realistic placeholder |
| Saswata | Intake page widget slot (Dev C #8) | P1 only | Skip widget |
| Saswata | Chain helper (Dev C #3) | **Not needed.** SPEND doesn't anchor | — |

## Q&A I own
Procurement fraud, reference prices, PE nursing-home chains, PECOS / ownership opacity, "why not just NADAC."
- **"Rural homes pay more?"** → Show Montana: price-only red stays yellow.
- **"Invoices aren't public?"** → Public cost reports flag which homes to examine → MFCU subpoenas invoices → tool fuses the signals.
- **Legal hook:** 42 CFR 413.17 ("prudent buyer" / related-party cost rule) lets CMS disallow related-party markups.

## What I do NOT own
- Dashboard shell, tab routing, shared schemas, chain helper, Voice, Case File (Saswata / Dev C).
- SHIFT pillar (Leo / Dev B).
- Chain anchoring. SPEND runs on public CMS data, so there's nothing to anchor at capture time.

## Open questions
- **Headline stats** for the pitch need sources: "$12B/yr" (is it really NBER w28474?) and "~$90B Medicaid to nursing homes."
- **ASP units:** ASP is per HCPCS billing unit, not per vial. Normalising and recording the conversion. If insulin turns out weak as the headline example, switch to a higher-gap drug (e.g. Eliquis).
- **Team docs drift:** `AGENTS.md` / `01-project-brief.md` still say "no chain, staffing out", which contradicts the 3-pillar + Base Sepolia plan in `saswata.md`.

## Decisions I've made
- (Nov 22) Taking Dev A — Phantom Spend.
- (Nov 22) SPEND scoring runs in-browser JS on static JSON; Python only for the one-time price pull.
- (Nov 22) Rural safety case is Montana (per `saswata.md`).
- (Nov 22) Invoice rows framed as supplier → facility invoices feeding the cost report, not Medicaid claims.

## TODO sections (for teammates to drop asks here)

(empty — add your TODO sections at the bottom using the format in `contexts/README.md`)

## TODO from Leo — PBJ data handoff for volume_sanity

### [ ] TODO 1 — Share the 6 facility CCNs and quarterly PBJ resident-day numbers as soon as Task 1 finishes (P0, ~immediate)

The `volume_sanity` scoring function is blocked on the exact shared facility identifiers and resident-day values. Send the finalized six-row dataset in the same shape as `facilities.json` once Leo Task 1 is complete.
