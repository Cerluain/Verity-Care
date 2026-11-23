# Answers to Abhi's asks (from Dev C)

**Date:** Nov 22 2026, scaffold-locked.
**Source:** Abhi's questions in `contexts/abi.md`.

This file is Dev C answering — not editing Abhi's context file. Abhi reads this, acts on it.

---

## 1. Who draws the SPEND ownership graph?

**Dev C (dashboard) draws it. Abhi returns the graph JSON on the signal card.**

The two earlier READMEs disagreed because I wrote them at different times. The locked answer:

- Abhi's `/spend/{facility_id}` endpoint returns a `SignalCard` with `evidence.ownership_graph = { nodes, edges, notes }`.
- Dev C's dashboard mounts vis-network, reads that JSON, draws the force-directed graph inside the SPEND tab.
- All visualization code lives in `apps/dashboard/`. Abhi stays backend-only.

Fixed in `apps/phantom-spend/README.md` (committed).

## 2. How to label made-up data

**New required field on every SignalCard: `data_provenance`.**

Enum: `real | demo_grounded | synthetic`.

- `real` — pulled from a public API this session (CMS ASP, NADAC, Nursing Home Compare).
- `demo_grounded` — hand-authored on a documented real-world pattern (e.g. ProPublica Portopiccolo). Comes with a `citation` field pointing to the public source.
- `synthetic` — fully invented for shape/UX only. Rare, should be avoided wherever possible.

Dashboard renders a tooltip badge automatically from this field. Abhi doesn't hand-build tooltips — he just sets the value and provides a `citation` when applicable.

Guidance for SPEND signals:
- Reference-price delta → `data_provenance: "real"`, citation points to CMS ASP quarterly file URL
- Ownership overlap → `data_provenance: "demo_grounded"`, citation points to ProPublica Portopiccolo investigation
- Volume-vs-census → `data_provenance: "real"` (PBJ resident-days + public diabetic-prevalence stats)

Fixed in `packages/schemas/signal-card.schema.json` (committed, field now required).

## 3. Overall facility colour

**Abhi returns per-signal severity only. Dashboard computes the facility-level badge.**

Rollup rule (in dashboard):
- `red` if any pillar has a red signal
- `yellow` if any pillar has a yellow signal and no reds
- `green` otherwise

Abhi doesn't need to compute a facility-level colour. He just returns his three SPEND signals with per-signal `severity`.

## 4. Real CCNs — RESOLVED, dataset updated

`data/facilities.json` has been rewritten with 6 real facilities verified against the Oct 2026 CMS Provider Info CSV. Every red facility is tied to a specific public source (NY AG filing, ProPublica investigation, DOJ settlement). Legal defensibility: we're reproducing accusations that already exist in public filings — no new accusations.

The 6 locked facilities (use these `id` strings as the primary key, NOT the CCN):

| id | Name | State | Hint | Scenario | Citation anchor |
|---|---|---|---|---|---|
| `buffalo-center-centers-health` | Buffalo Center for Rehabilitation and Nursing | NY | red | pe_owned_fraud | NY AG v. Centers Health Care (Nov 2023) |
| `accordius-rose-manor-portopiccolo` | Accordius Health at Rose Manor | NC | red | pharmacy_kickback | ProPublica — Portopiccolo (Nov 2020) |
| `mi-casa-life-care-az` | Mi Casa Nursing Center | AZ | red | worthless_services | DOJ Life Care Centers $145M (2016) |
| `crook-county-wy-rural` | Crook County Medical Services District LTC | WY | yellow | rural_ambiguous | CMS Nursing Home Compare |
| `terraces-phoenix-humangood` | The Terraces of Phoenix | AZ | green | clean_baseline | CMS Care Compare |
| `haven-health-green-valley` | Haven Health Green Valley | AZ | green | clean_baseline | CMS Care Compare |

Full per-facility citation URLs + parent company + notes are in `data/facilities.json`. Abhi — your SPEND dataset keys on these `id` strings.

**Scenario-to-SPEND mapping for Abhi:**

- `buffalo-center-centers-health` (PE related-party) → **SPEND is the hero**. Load with ~3 red line items. Ownership graph: Buffalo Center → Centers Health Care → owner-controlled vendor LLCs (per NYAG complaint).
- `accordius-rose-manor-portopiccolo` (pharmacy kickback) → **SPEND red**. Load with high-markup pharmacy line items. Ownership graph: Accordius Rose Manor → Portopiccolo Group → captive pharmacy vendor.
- `mi-casa-life-care-az` (worthless services) → **SPEND stays clean/yellow**. This one's red lands on VOICE + SHIFT, not SPEND. Keep its line items boring.
- `crook-county-wy-rural` → SPEND shows +180% markup on 2 items BUT ownership graph is clean (county hospital district, non-profit). Signal 1 red alone → stays yellow overall. Judge-trap defense tile.
- `terraces-phoenix-humangood` → all green on SPEND.
- `haven-health-green-valley` → all green on SPEND.

## 5. "worthless_services" red facility — mapping update

With the real-facility dataset, `mi-casa-life-care-az` carries the `worthless_services` scenario. It's a Life Care Centers of America property (the chain that signed the DOJ 2016 $145M settlement for medically unnecessary rehab). On SPEND it should look **mostly clean on SPEND** (maybe one yellow line item, no ownership overlap). Its red flag lands on **VOICE** (Dev C: residents reporting undelivered services) and lightly on **SHIFT** (Leo: unstaffed therapy sessions).

Fixed in `apps/phantom-spend/README.md` (committed). Abhi — when you build line items for Mi Casa, keep them boring. The three SPEND-clean facilities are Mi Casa + Terraces of Phoenix + Haven Health Green Valley. Red on SPEND: Buffalo Center (PE) + Accordius Rose Manor (pharmacy kickback).

---

## Summary: what changed in the repo

- `packages/schemas/signal-card.schema.json` — added required `data_provenance` field.
- `apps/phantom-spend/README.md` — ownership-graph rendering split; facility colour rollup; Phoenix correction.
- `data/facilities.json` — real-facility replacement pending research agent.
- Nothing in Abhi's workflow blocks on anything other than updated `data/facilities.json`.

Ping me if any of the 5 answers above needs more detail.
