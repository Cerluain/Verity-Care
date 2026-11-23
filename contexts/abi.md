# Abi — context

Role: **Dev A — Phantom Spend** (procurement fraud pillar). Taking the open Dev A seat from `contexts/saswata.md`.

## What I own in this project

The SPEND pillar end to end: data, scoring and SPEND-tab UI. Task list mirrors Dev A in `saswata.md`.

### P0 — Must ship
- [ ] 1. CMS ASP quarterly file → lookup table for ~20 common SNF drugs
- [ ] 2. NADAC (Socrata) for the same drugs, joined to the ASP table
- [ ] 3. Hand-pull 10 Cost Plus Drugs prices
- [ ] 4. Author line items: 6 facilities × 12 rows (3 fraud, 1 ambiguous rural, 2 clean) — **start first**
- [ ] 5. Author ownership graphs for 6 facilities (3 sister-LLC overlap modelled on Portopiccolo / Centers Health Care reporting, 1 clean family, 2 blank) — **start first**
- [ ] 6. Scoring: reference-price delta per line item → red/yellow/green + headline
- [ ] 7. Scoring: ownership overlap → hop count + severity
- [ ] 8. Scoring: volume-vs-census → overbill ratio (PBJ resident-days × diabetic fraction)
- [ ] 9. SPEND tab: 12-row line-item table
- [ ] 10. Three signal cards above the table
- [ ] 11. vis-network ownership graph, rendered on clicking a flagged row
- [ ] 12. Montana rural case: only signal 1 red → overall yellow

### P1 — Should ship
- [ ] 13. Cost-report CSV upload widget on the facility intake page (mock: hash + console log)
- [ ] 14. Citation footer on each signal card
- [ ] 15. Hover tooltips on ownership graph nodes

### P2 — Stretch (cut first)
- [ ] 16. ZK invoice-integrity proof in Noir (one drug, one invoice)

## Q&A I own

Procurement fraud, reference prices, PE nursing-home chains, PECOS / ownership opacity, "why not just NADAC."

## What I do NOT own

- Dashboard shell, tab routing, shared schemas, chain helper, Voice, Case File (Saswata / Dev C).
- SHIFT pillar (Leo / Dev B).
- Chain anchoring — SPEND runs on public CMS data, nothing to anchor at capture time.

## Dependencies on others

- `signal-card.schema.json` + `facilities.json` from Saswata (Dev C task 4). I'll stub against a draft shape until it lands.
- Dashboard shell (Dev C task 5–7) to mount the SPEND tab into.
- Real PBJ resident-day counts + facility CCNs from Leo (Dev B task 1) for signal 3.

## Open questions I'm tracking

- **Stack for scoring:** Python/FastAPI behind an endpoint, or JS in the page? Depends on the schema shape.
- **Demo numbers for signal 3:** `03-demo-plan.md` uses 4,210 resident-days/quarter ≈ 46 residents, not ~1,050 diabetics. Re-derive the overbill ratio with realistic numbers.
- **Framing:** line items are supplier → facility invoices that feed the cost report (Form 2540, Worksheet A-8-1), not Medicaid claim lines (Part A has no drug line items). Label the UI accordingly.
- **Rural tile:** the docs say both Montana and Wyoming. Going with Montana per `saswata.md`.
- **Headline stats** for the pitch need sources: "$12B/yr" (NBER w28474?) and "~$90B Medicaid to nursing homes."

## My ideas / direction

- Cite 42 CFR 413.17 ("prudent buyer" rule, from Leo's doc) as the legal basis for disallowing related-party markups.
- Judge-trap answer for "invoices aren't public": public cost reports flag which facilities to examine → the MFCU subpoenas the invoices → the tool fuses the signals.

## Decisions I've made

- (Nov 22) Taking Dev A — Phantom Spend.

## TODO sections (for teammates to drop asks here)

(empty — add your TODO sections at the bottom using the format in `contexts/README.md`)

## TODO from Leo — PBJ data handoff for volume_sanity

### [ ] TODO 1 — Share the 6 facility CCNs and quarterly PBJ resident-day numbers as soon as Task 1 finishes (P0, ~immediate)

The `volume_sanity` scoring function is blocked on the exact shared facility identifiers and resident-day values. Send the finalized six-row dataset in the same shape as `facilities.json` once Leo Task 1 is complete.
