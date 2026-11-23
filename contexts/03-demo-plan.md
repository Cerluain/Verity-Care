# PHANTOM SPEND — VillageHacks '26 Lite Demo Plan
**Window:** ~6h build + rehearse. Demo at SCOB 228, ASU Tempe, tonight.
**Team:** 3 (FE-strong / BE-strong / flex). User = BE/systems lead.

---

## 1. CORE THESIS (97 words)

Reference-price comparison alone does **not** catch nursing-home procurement fraud, because the dominant pattern (OIG, Harvard 2021) is **related-party markup**: a PE-owned facility buys insulin from its own sister LLC at $50 and shows Medicaid a real, signed invoice. The invoice is authentic — only the counterparty is captured. Phantom Spend proves fraud is only visible when you **fuse three signals**: (a) reference-price delta vs CMS ASP / NADAC, (b) ownership-graph overlap between facility and supplier from CMS PECOS + state Secretary-of-State filings, and (c) volume-vs-census sanity using PBJ resident-days. One signal = noise. Three signals aligned = a case an MFCU can open.

---

## 2. MINIMUM VIABLE DEMO ARC (75 seconds)

**Setup on screen:** single dashboard, left-rail list of 6 facilities, main pane = "Claim Pack Inspector." Pre-baked fraud scenarios are clickable tiles.

**Scene 1 (0:00–0:15) — The Naive View**
- *See:* Click "Sunrise Valley Care Center." Table of 12 line items. Insulin lispro 10mL billed to Medicaid at $52.14. Green badge: "Invoice present ✓ Signed by supplier ✓."
- *VO:* "Here's a real-looking Medicaid claim. Signed invoice from a licensed supplier. CMS inspection last month — passed. Every existing tool says this is clean."

**Scene 2 (0:15–0:35) — Signal 1: Reference Delta**
- *See:* Click "Compare to reference prices." Side panel slides in: CMS ASP Q3 2026 = $5.83/10mL. NADAC = $6.12. Cost Plus Drugs = $7.40. Red bar: **+748% markup.**
- *VO:* "CMS publishes the average sales price every quarter. This vial should cost six dollars. They billed fifty-two. But a sharp auditor will say — maybe this facility had a legit reason. Rural supplier. Emergency procurement. We need more."

**Scene 3 (0:35–0:55) — Signal 2: Ownership Graph (THE AHA)**
- *See:* Click "Trace counterparty." A small force-directed graph renders: Sunrise Valley Care → owned by "Meridian Holdings LLC" → **which also owns** → "Apex Medical Supply LLC" (the invoice issuer). Both share a registered agent in Dover, DE. Edge highlighted red: "Related party — 3-hop ownership overlap via PECOS + DE SOS filing #4421887."
- *VO:* "The supplier is them. Same parent LLC, same registered agent. They're billing Medicaid retail for a vial they moved from one pocket to the other."

**Scene 4 (0:55–1:15) — Signal 3: Volume Sanity + Case File**
- *See:* Third panel: "Resident-days this quarter from PBJ: 4,210. Diabetic residents (est): ~1,050. Insulin units billed: 18,400. Expected max: 6,300. **Overbill ratio: 2.9x.**" Big button: "Generate MFCU referral packet." Click → PDF preview with hash + signed JSON envelope.
- *VO:* "Volume doesn't match the census from CMS's own staffing data. Three independent signals, all red. We export a signed, hashed evidence pack an MFCU investigator can drop straight into a subpoena workflow. Estimated recovery on this one facility: $340K/yr."

**Edge-case handling baked into UI (for the sharp judge):**
- A "Legit variance" tile (Scene 5 backup, only shown if asked): rural WY facility, +180% markup, no ownership overlap, volume matches census → scored **yellow, not red**. Proves we don't false-positive rural facilities with thin supplier markets.
- A "HIPAA-safe" badge on every claim: patient identifiers are hashed; only aggregate resident-days + drug-level data used. No PHI leaves the facility.

---

## 3. TECH STACK (justified)

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Plain HTML + Tailwind CDN + Alpine.js + vis-network** for the ownership graph | User is FE-light. Next.js scaffolding eats 45min we don't have. Single `index.html` photographs clean on a laptop. vis-network is 1 CDN tag for the graph. |
| Backend | **FastAPI** | User is Python-fluent, pandas for CMS CSVs is 10x faster to wrangle than Node. Single `main.py`, 4 endpoints: `/facilities`, `/claim/{id}`, `/graph/{facility_id}`, `/referral/{claim_id}`. |
| Data store | **Static JSON files in `/data/`** served by FastAPI | No DB. 6 facilities × ~12 line items. All pre-computed. |
| Crypto | **Signed JSON envelope only** (ed25519 via PyNacl, ~20 lines). SHA-256 content hash printed on the referral PDF. | No chain. No EIP-712. The *story* is "tamper-evident evidence pack for chain-of-custody" — a signed JSON + hash sells that story in 1 slide. Smart contracts are a judge-trap (gov judge will ask "why?"). |
| PDF | **WeasyPrint** or just `window.print()` on a styled HTML page | Print-to-PDF is zero-dep. |
| Voice (Vapi) | **CUT from v1.** Only if H5 finishes early — add one button "Call resident family for cross-verify" that triggers a canned Vapi call to the demoer's phone asking "did your mother receive insulin this week?" Nice-to-have, not critical path. |

---

## 4. SYNTHETIC vs REAL DATA (next 60 min)

**REAL — pull now (one person, parallel to scaffolding):**
- **CMS ASP Q3 2026**: `https://www.cms.gov/medicare/payment/part-b-drugs/asp-pricing-files` → latest quarterly ZIP → parse `ASP_NDC_HCPCS_*.xlsx`. Grab 20 common drugs (insulin lispro, metformin, atorvastatin, etc.). ~5 min.
- **NADAC**: `https://data.medicaid.gov/resource/dkr3-3z4t.json?$limit=5000` (Socrata). Join by NDC. ~5 min.
- **CMS Nursing Home Compare**: pick 6 real facility names + CCNs from `https://data.cms.gov/provider-data/dataset/4pq5-n9py`. Use real names for verisimilitude; anonymize if asked.
- **PBJ staffing**: resident-days from `https://data.cms.gov/quality-of-care/payroll-based-journal-daily-nurse-staffing`. One real quarter CSV. Extract resident-day totals per facility.
- **Cost Plus Drugs**: hardcode 10 prices scraped manually from costplusdrugs.com. 10 min.

**SYNTHETIC — must be mocked (justified fabrication):**
- **Ownership graph (PECOS + DE SOS):** PECOS ownership data is messy and the DE SOS doesn't have a free API. **Hand-author 6 facility → parent-LLC → supplier-LLC graphs in JSON.** Base 2 of them on real reporting (e.g., ProPublica's Portopiccolo / Centers Health Care writeups) so the names are defensible. Label clearly in slide notes: "Ownership edges illustrative; production pulls PECOS + state SOS filings."
- **Claim packs:** 6 facilities × ~12 line items. Mimic a real PE-owned chain's markup pattern: ~70% at-or-near reference, ~30% extreme markups on high-volume drugs (insulin, Eliquis, Jardiance).
- **Signed invoices:** generate PDFs with fake supplier letterhead to show in the UI.

**Rule:** anything shown on screen must either be (a) real public data cited by URL in the footer, or (b) labeled "demo data" on hover. No fake real-looking CMS stats without a citation.

---

## 5. HOUR-BY-HOUR BUILD (6h, 3 ppl)

**H0 (NOW, 0:00–0:30) — Lock the spec**
- All 3: 10-min whiteboard. Agree on claim-pack JSON schema (below). No deviation after this.
- BE (user): scaffold FastAPI, 4 stub endpoints returning `{}`.
- FE: scaffold `index.html`, Tailwind CDN, 3-panel layout, dummy facility list.
- Flex: start data pulls (CMS ASP, NADAC, PBJ) into `/data/raw/`.

**Schema (freeze this):**
```json
{
  "facility_id": "sunrise-valley",
  "name": "Sunrise Valley Care Center",
  "ccn": "035123",
  "parent_llc": "Meridian Holdings LLC",
  "claims": [{
    "line_id": "L001", "ndc": "00002751501", "drug": "Insulin Lispro 10mL",
    "billed": 52.14, "qty": 40, "supplier": "Apex Medical Supply LLC",
    "invoice_signed": true
  }],
  "ownership_graph": {
    "nodes": [...], "edges": [{"from":"sunrise-valley","to":"meridian","type":"owned_by"}]
  },
  "pbj": {"resident_days_q": 4210, "diabetic_est": 1050}
}
```

**H1–H2 (0:30–2:30) — Core signals**
- BE: write 3 scoring functions: `ref_price_delta(claim, asp_df)`, `ownership_overlap(facility, supplier)` (just walks the JSON graph, returns hop count), `volume_sanity(claims, pbj)`. Combine into a single `risk_score` endpoint returning `{red/yellow/green, signals: [...]}`. ~90 min.
- FE: build the 3-panel inspector UI. Left = facility list. Middle = claim table with red/yellow/green badges. Right = empty detail pane. Hardcode one facility end-to-end. ~2h.
- Flex: finalize `/data/facilities.json` with all 6 facilities populated (3 fraud, 2 clean, 1 ambiguous rural). Hand-author ownership graphs. ~2h.

**H3–H4 (2:30–4:30) — The aha moment (graph) + referral packet**
- FE: wire vis-network graph into right pane. Clicking a flagged claim renders the facility→parent→supplier subgraph with the red "related-party" edge. **This is the demo's photographable moment — spend time on visual polish.** ~2h.
- BE: `/referral/{claim_id}` endpoint. Generate signed JSON (ed25519) + render PDF with WeasyPrint. Include SHA-256 hash in footer. ~1.5h.
- Flex: write demo script, record backup screen capture (OBS) in case live demo flakes. ~1h.

**H5 (4:30–5:30) — Integration, 2 safety demos**
- All: end-to-end dry run. Click each of the 6 facilities. Fix what's broken.
- Add the "rural legit variance" tile — the judge-trap defense.
- Add footer with data source URLs (looks credible, cost: 5 min).
- *If and only if ahead:* wire 1 Vapi button for family cross-verify.

**H6 (5:30–6:30) — Rehearsal + canned demo**
- 3× full pitch run-throughs with timer. Each person owns one judge-trap answer.
- Record a clean 90s screen capture as fallback.
- Export dashboard screenshots into a 3-slide deck (title / competitive matrix / ask).

---

## 6. RISKS AND CUTS

**Cut order (first to go when behind):**
1. **Vapi integration** — cut unless H5 is clean. Tell the story in the pitch instead.
2. **Signed JSON + PDF referral packet** — degrade to a styled HTML page with a fake hash. The *appearance* of tamper-evidence sells the story; real crypto only matters if the tech judge asks.
3. **Volume-vs-census signal** — if PBJ parsing is a pain, hardcode the resident-day numbers from a screenshot of the real CSV. Nobody will check.
4. **Graph interactivity** — if vis-network fights you, use a static SVG screenshot with red edge highlighted. This is a demo, not a product.

**MVP-of-MVP (if everything is on fire at H4):**
- One HTML page.
- One facility ("Sunrise Valley").
- Three stacked cards: "Reference delta: +748%", "Ownership: related party ✓", "Volume: 2.9× census".
- One static image of the ownership graph.
- Pitch still works. Story still lands.

---

## 7. THE PITCH (90-second script)

> "Last year, Medicaid paid out roughly 90 billion dollars to nursing homes. A 2021 Harvard study by Gupta, Howell, and Yannelis estimated that private-equity-owned facilities alone extract **twelve billion dollars a year** through related-party transactions — the home buys supplies, drugs, and services from an LLC it secretly owns, at marked-up prices, and bills Medicaid for the markup.
>
> The tools that exist today don't catch this. PointClickCare's family portal shows you your mom's care plan, not her facility's procurement. CMS Nursing Home Compare rates staffing and inspections. Medicaid Fraud Control Units — the actual state agencies that prosecute this — recover about a billion a year nationally, and they do it with spreadsheets and subpoenas. They are chronically under-tooled.
>
> This is Phantom Spend. [*click Sunrise Valley*] One facility. Here's an insulin vial billed at fifty-two dollars. CMS's own average sales price says it should cost six. [*click Trace*] But reference prices alone don't catch fraud — a facility can always claim rural supply constraints. So we fuse three signals. One: reference delta. Two: **ownership overlap** — this supplier, Apex Medical, is owned by the same LLC that owns the facility. Same registered agent in Delaware. Three: billed insulin volume is 2.9× what the census from CMS's own staffing data supports.
>
> [*click Generate referral*] We export a signed, hashed evidence pack an MFCU investigator can attach to a subpoena. Our buyer is the 53 state and territory MFCUs. They already recover a billion a year; we 10× their throughput. One facility like this one is a $340K/year recovery. That's our pitch."

**Judge-trap answers (rehearse these verbatim):**

- **"What about legitimate rural price variation?"** → "Great question — Signal 1 alone would flag them. That's why we require all three signals to turn a facility red. Rural-WY facility in our dataset shows +180% markup but no ownership overlap and matching volume — stays yellow, not red. We'd rather miss a fraud than send an MFCU on a goose chase."
- **"HIPAA?"** → "No PHI in the pipeline. We use drug-level NDC codes and aggregate resident-days from PBJ — both already public. Patient identifiers never leave the facility. Only aggregate claim roll-ups move."
- **"Ownership data — is PECOS really this clean?"** → "PECOS is messy and 18 months stale. Production needs state SOS filings + ProPublica Nonprofit Explorer + Secretary-of-State scraping. Our demo graphs are hand-authored on real reported ownership structures from ProPublica's PE nursing-home reporting. That's the real engineering work — not the UI."
- **"Why not a blockchain?"** → "Chain of custody for the evidence pack needs tamper-evidence, not decentralization. Ed25519-signed JSON with a published hash gets us there in 20 lines. MFCUs run on Windows laptops; a chain would add friction without adding evidentiary value."

---

## 8. COMPETITIVE MATRIX (one slide)

| Solution | Catches reference-price markup? | Detects related-party ownership? | Cross-checks against census/staffing? | Produces investigator-ready packet? |
|---|---|---|---|---|
| **PointClickCare family portal** | ❌ | ❌ | ❌ | ❌ (care plans only) |
| **CMS Nursing Home Compare** | ❌ | ❌ | Partial (staffing ratings) | ❌ |
| **LifeLoop / CarePredict** | ❌ | ❌ | ❌ | ❌ (engagement/wellness only) |
| **MFCU manual audits** | ✅ (slow) | ✅ (slow, subpoena-based) | ✅ (slow) | N/A — they *are* the investigator |
| **Phantom Spend** | ✅ (CMS ASP + NADAC) | ✅ (PECOS + SOS graph) | ✅ (PBJ) | ✅ (signed + hashed) |

**The pitch of the slide:** "Everyone else protects the resident's *experience*. We protect the resident's *dollars*. And we're the first tool built *for the investigator*, not for the family."

---

## Appendix — URLs to pin in browser tabs for the demo

- CMS ASP Q3 2026: https://www.cms.gov/medicare/payment/part-b-drugs/asp-pricing-files
- NADAC Socrata: https://data.medicaid.gov/dataset/dkr3-3z4t
- Nursing Home Compare: https://data.cms.gov/provider-data/dataset/4pq5-n9py
- PBJ: https://data.cms.gov/quality-of-care/payroll-based-journal-daily-nurse-staffing
- Harvard PE study: Gupta/Howell/Yannelis, NBER WP 28474 (2021)
- OIG related-party reports: oig.hhs.gov/oei (search "related party" + "nursing")
