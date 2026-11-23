# Project Brief — VillageHacks '26 Lite

**Status:** LOCKED. Research complete. Build phase starting.

Read this file first, then `02-fraud-research-brief.md` (what the fraud actually is), then `03-demo-plan.md` (what we're building in 6h).

## Pitch (locked)

**Phantom Spend — a transparency layer for nursing home money trails, built for state Medicaid Fraud Control Units.**

Last year, Medicaid paid ~$90B to US nursing homes. Harvard 2021 (Gupta/Howell/Yannelis, NBER WP 28474) estimated PE-owned facilities alone extract ~$12B/yr through related-party transactions: the home buys supplies, drugs, pharmacy, management, and rent from LLCs it secretly owns, at marked-up prices, inflates its CMS Form 2540 cost report, and that ratchets up the state Medicaid per-diem rate forever.

Nothing in market catches this in real time. MFCUs prosecute 4–8 years late with spreadsheets and subpoenas. We fuse three public-data signals — reference-price delta (CMS ASP / NADAC), ownership-graph overlap (CMS PECOS + SOS filings), and volume-vs-census sanity (PBJ staffing) — and produce a signed, hashed evidence packet an MFCU investigator can attach to a subpoena.

## Why the original "$50 insulin vs $5 Amazon" framing is a strawman (CRITICAL — read this)

Medicare Part A SNF is a **bundled per-diem under PDPM** — individual drugs/supplies are NEVER line-itemed on the claim. There is no "$50 insulin" row anywhere in Medicare Part A to compare against NADAC/ASP. See `02-fraud-research-brief.md` for the full mechanics.

The $45 markup actually lives in TWO places:

1. **Cost-report inflation (biggest dollar vector, rarely prosecuted):** sister LLC sells insulin to the home at $50 → home reports $50 as operating cost on CMS Form 2540 Worksheet A-8-1 → next year's state Medicaid per-diem rate goes up for every resident-day forever. The $45 lands as sister-LLC profit, distributed up to PE/ParentCo. *This is the dominant pattern.*

2. **Service-code / MDS upcoding (most-prosecuted vector):** Life Care Centers $145M, Kindred $125M, Ensign $48M, SavaSeniorCare, Signature, Consulate — all were therapy-minute / RUG-IV upcoding, now shifting to PDPM NTA tier gaming.

Reference-price comparison alone catches NEITHER. Nobody prosecutes it because the facility shows a real signed invoice from its sister LLC and defends the transfer price as "arm's-length."

## What we're building (demo arc — locked)

Single dashboard. Left-rail = 6 facilities. Main pane = Claim Pack Inspector. Clicking a facility walks through 3 fused signals in 75 seconds:

1. **Reference delta** — CMS ASP says this insulin vial should cost $6. They billed $52. Flagged red. But a rural-supplier defense can kill this signal alone.
2. **Ownership-graph aha** — Trace counterparty. Vis-network graph renders: facility → parent LLC → supplier LLC. Same registered agent in Dover, DE. 3-hop ownership overlap. This is the demo's photographable moment.
3. **Volume-vs-census sanity** — PBJ shows 4,210 resident-days this quarter → ~1,050 diabetic residents → expected max 6,300 units of insulin. They billed 18,400. 2.9x overbill.

Three signals aligned = red = "generate MFCU referral packet." Click → signed JSON (ed25519) + SHA-256 hash + PDF for subpoena workflow.

Backup "legit variance" tile: rural WY facility with +180% markup, no ownership overlap, volume matches census → stays yellow, not red. Demonstrates we don't false-positive rural facilities.

## Target buyer (locked)

State Medicaid Fraud Control Units (53 of them across states + territories). They recover ~$1B/yr nationally with spreadsheets. Secondary: Long-Term Care Ombudsman offices. Explicitly NOT consumer families in this pitch — business case is cleaner B2G.

## Scope (locked)

**IN:**
- Procurement / phantom-spending detection (the 3-signal fusion above).
- Static JSON data + pre-baked fraud scenarios.
- Signed JSON + hash evidence pack.

**OUT for tonight:**
- Staffing-fraud module. Noted on competitive slide as "future module," not built.
- Resident voice attestation via Vapi. Stretch only if H5 finishes clean.
- Facility EHR integration (never in scope — that's the moat).
- Real HIPAA / PHI (synthetic / illustrative only, labeled in UI).
- Blockchain, ZK proofs, multisig. Judge-trap bait; we defend against them in Q&A.

## Stack (locked)

- Frontend: plain HTML + Tailwind CDN + Alpine.js + vis-network. One `index.html`. No Next.js scaffolding.
- Backend: FastAPI + static JSON in `/data/`. 4 endpoints.
- Crypto: ed25519-signed JSON envelope (PyNacl, ~20 lines) + SHA-256 content hash. NO chain.
- PDF: WeasyPrint or `window.print()`.

## Data plan

**Pull live in first hour:**
- CMS ASP quarterly file (cms.gov/medicare/payment/part-b-drugs/asp-pricing-files)
- NADAC Socrata API (data.medicaid.gov/resource/dkr3-3z4t.json)
- CMS Nursing Home Compare (data.cms.gov/provider-data/dataset/4pq5-n9py) — 6 real facilities + CCNs
- PBJ staffing (data.cms.gov/quality-of-care/payroll-based-journal-daily-nurse-staffing)
- Cost Plus Drugs — hand-scrape 10 prices

**Hand-author (defensibly):**
- Ownership graphs. PECOS is messy, DE SOS has no free API. Base 2 scenarios on real ProPublica Portopiccolo / Centers Health Care reporting so names are defensible. Label in UI: "Ownership edges illustrative; production pulls PECOS + state SOS."
- Claim packs. 6 facilities × ~12 line items. Mimic real PE-chain markup pattern.

## Hour-by-hour (6h, 3 ppl)

See `03-demo-plan.md` §5 for the full schedule. Short version:
- H0 (0:00–0:30) — lock schema, scaffold shells, start data pulls
- H1–H2 — core signals (3 scoring functions, 3-panel UI, populate /data/facilities.json)
- H3–H4 — ownership graph (the aha moment, spend polish time here) + signed JSON + PDF referral
- H5 — end-to-end dry run, add "legit variance" tile, footer with source URLs
- H6 — 3 pitch rehearsals, OBS screen-capture fallback, 3-slide deck

## Rejected-ideas log

- "Government transparency in general" — too broad, no demo moment.
- "Verify every Walmart receipt" — nursing homes don't buy from Walmart; wrong supply chain.
- "NFC clock-in for staffing" — PBJ already exists; doesn't catch gaming vectors.
- "FOIA Merkle-commit tool" — photogenically weak.
- "Darkroom (ZK-threshold campaign finance)" — strong idea but ZK tooling eats >2h scaffold and team hasn't shipped Noir/Circom.
- "SealedBid (commit-reveal procurement)" — kept as back-pocket fallback if phantom-spending blocks on data.
- **"$50-vs-$5 price-scraper"** — the research killed this: Part A has no line items; price-scraping catches none of the dominant fraud vectors.

## Judge-trap answers (rehearse verbatim)

- **"What about legitimate rural price variation?"** → Signal 1 alone would flag them. We require all three signals aligned for red. Our rural-WY tile shows +180% markup but no ownership overlap and matching volume → stays yellow.
- **"HIPAA?"** → No PHI. NDC drug codes + aggregate PBJ resident-days — both already public. Patient identifiers never leave the facility.
- **"PECOS ownership data — is it really this clean?"** → PECOS is messy and 18 months stale. Production pulls state SOS + ProPublica Nonprofit Explorer. Demo graphs are hand-authored on real reported structures. That's the real engineering work — not the UI.
- **"Why not blockchain?"** → Chain of custody needs tamper-evidence, not decentralization. ed25519-signed JSON + published hash in 20 lines. MFCUs run on Windows laptops; a chain adds friction without evidentiary value.
- **"Why no MetaMask / browser wallet?"** → This isn't a consumer product — there's no user signing their own asset. The claims we anchor are institutional: the facility attests to its own tap logs, the ombudsman attests to its own call logs, we attest to our own computations. Those are backend attestations by legally-responsible entities, not personal signatures. The one place a human belongs on-chain is the MFCU investigator confirming they reviewed the case — that's a passkey or hardware-wallet moment at CASEFILE export time, on the production roadmap as a 2-of-2 (investigator + service) signature.

## Competitive matrix (for the slide)

| Solution | Reference-price? | Related-party ownership? | Census/staffing cross-check? | Investigator-ready packet? |
|---|---|---|---|---|
| PointClickCare family portal | ❌ | ❌ | ❌ | ❌ |
| CMS Nursing Home Compare | ❌ | ❌ | Partial | ❌ |
| LifeLoop / CarePredict | ❌ | ❌ | ❌ | ❌ |
| MFCU manual audits | ✅ (slow) | ✅ (slow) | ✅ (slow) | They *are* the investigator |
| **Phantom Spend** | ✅ | ✅ | ✅ | ✅ (signed + hashed) |

Pitch line: *"Everyone else protects the resident's experience. We protect the resident's dollars. We're the first tool built for the investigator, not the family."*
