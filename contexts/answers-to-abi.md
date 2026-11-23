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

## 4. Real CCNs — the defamation question

**Resolved: using real CCNs tied to documented public fraud cases.**

A background research agent is pulling 6 real facilities from CMS Nursing Home Compare where the CCN + facility name match documented DOJ settlements, ProPublica investigations, or state AG filings. Per-facility citation URLs included.

Legal defensibility: we're only reproducing accusations that are already public on DOJ, state AG, or ProPublica. No new accusations. The demo shows how a continuous system would flag what historical investigations found years later.

Research result lands in `data/facilities.json` (replacing the current placeholder list) within the hour. The locked `scenario_tag` enum stays the same; only names + CCNs + `parent_llc_hint` + per-facility citations change.

**Abhi — hold the SPEND dataset keyed on facility `id` strings, not on CCN numbers.** The `id` strings in the current `data/facilities.json` (sunrise-valley, desert-palms, phoenix-memory-care, big-sky-rural, pine-valley, lakeview) MAY also change when real facilities replace them. If they do, I'll push an update to `data/facilities.json` and ping. Until then, the current 6 IDs are the source of truth.

## 5. Phoenix Memory Care — SPEND should NOT be red

My scaffold mistake. `worthless_services` is service non-delivery, not procurement. Phoenix Memory Care should look **mostly clean on SPEND** (maybe one yellow line item, no ownership overlap). Its red flag lands on **VOICE** (Dev C: residents reporting undelivered services) and lightly on **SHIFT** (Leo: under-visited dementia residents).

Fixed in `apps/phantom-spend/README.md` (committed). Abhi — when you build line items for Phoenix, keep them boring. Pine Valley + Lakeview + Phoenix are the three SPEND-clean facilities. Red on SPEND: only Sunrise Valley + Desert Palms.

---

## Summary: what changed in the repo

- `packages/schemas/signal-card.schema.json` — added required `data_provenance` field.
- `apps/phantom-spend/README.md` — ownership-graph rendering split; facility colour rollup; Phoenix correction.
- `data/facilities.json` — real-facility replacement pending research agent.
- Nothing in Abhi's workflow blocks on anything other than updated `data/facilities.json`.

Ping me if any of the 5 answers above needs more detail.
