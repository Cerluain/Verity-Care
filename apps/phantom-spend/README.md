# apps/phantom-spend — Procurement fraud detection

**Owner:** Abhi (Dev A)
**Port:** 8003

Produces SPEND signal cards for each facility via three scoring functions. See
`contexts/saswata.md` (Dev A section) and `contexts/abi.md` for full P0/P1/P2 task list.

## What this service owns

1. Static data under `/data/spend/` — reference prices, line items, ownership graphs.
2. Three scoring functions (reference-price delta, ownership overlap, volume-vs-census).
3. Endpoint `GET /spend/{facility_id}` returning an array of SignalCard JSON objects
   conforming to `packages/schemas/signal-card.schema.json`.
4. One widget on the facility-intake page (cost-report CSV upload).

## What this service does NOT own

- The dashboard shell, tab routing, case file aggregation (Dev C).
- The ownership-graph visualization component itself (Dev C's dashboard renders from the JSON
  Abhi returns; Abhi defines the shape, Dev C draws the vis-network).
- Any chain wallet or signing. If Abhi wants to anchor signal-card hashes (P1), he imports
  `packages/onchain-client` and calls `commit(CLAIM_SIGNAL_CARD, hash)`.

## Reference-price delta signal

Input: a line item with (ndc, qty, billed_total).
Output: red if billed_unit_price > 3x CMS ASP, yellow if 1.5x-3x, green otherwise.
Citation: CMS ASP Q3 2026 file + NDC URL.

## Ownership overlap signal

Input: facility_id, supplier_llc.
Walks the hand-authored graph under `/data/spend/ownership-graphs.json`.
Returns red if shared ancestor within 3 hops.

**Rendering split (clarifies earlier contradiction):**
- Abhi (this service) returns the graph JSON inside `evidence.ownership_graph` on the signal card. Shape: `{ nodes: [...], edges: [...], notes: "..." }`.
- Dev C's dashboard renders the vis-network from that JSON. All visualization code lives in `apps/dashboard/`; Abhi stays backend-only.
- Abhi sets `data_provenance: "demo_grounded"` on the signal card. The dashboard auto-renders a tooltip badge + ProPublica citation from that field. Abhi doesn't hand-build the tooltip.

## Overall facility colour

Abhi returns **per-signal severity only**. The dashboard computes `aggregate_severity` for the left-rail facility badge using:
- red if any pillar has a red signal
- yellow if any pillar has a yellow signal and no reds
- green otherwise

## Phoenix Memory Care / Mi Casa Nursing Center — scenario correction

The red facility carrying `worthless_services` is `mi-casa-life-care-az` (Mi Casa Nursing Center, AZ — a Life Care Centers of America property). `worthless_services` is a service-delivery problem, not a procurement problem. On SPEND Mi Casa should look **mostly clean or yellow** (maybe one modest markup, no ownership overlap). Its red flag lands on **VOICE** (residents/proxies saying services weren't delivered) and lightly on **SHIFT** (unstaffed therapy sessions). Dev C owns that mapping on the VOICE side.

## Volume-vs-census signal

Input: billed units of a drug, PBJ resident-days for the facility (from /data/facilities.json + PBJ), diabetic fraction assumption.
Returns overbill ratio. Red if >1.5x.
