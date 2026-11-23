# Project Brief — VillageHacks '26 Lite

**Status:** LOCKED, then updated Nov 22 evening (see Direction update below).

## ⚠️ Direction update (Nov 22, evening) — supersedes the "locked" text below where they conflict

Agreed by Abi + Saswata. Older text is kept below for history.

**Product = Verity Care, one website (`apps/dashboard`, :8000) with three views + a pitch page:**

| Route | Who | What |
|---|---|---|
| `/pitch` | judges | Static story built from `contexts/04-spend-evidence.md` (every number sourced). The demo **starts here**, then "Open the product →". |
| `/` | state investigator (MFCU) | Facility list + tabs: **Spending** (Dev A: 3 signals, ownership graph, invoice table), **Staffing** (Dev B: mock PBJ until Leo's SHIFT lands), **Guardian reports** (family disputes + billed-but-unverified care), Voice, Case file. Chain buttons per card (Dev C). |
| `/guardian` | family member | Live daily timeline for their relative: meds, meals, therapy, activities, vitals. Each item is **photo-verified by staff** and anchored on-chain; the family can press "This didn't happen". |
| `/staff` | facility staff (phone) | Pick a care task → take a **live photo** → photo SHA-256 + metadata hashed → `/commit` (claim type 1, facility signer). Photo stays off-chain. |

**Demo arc:** pitch page → investigator: Buffalo Center (all 3 SPEND signals red, ownership graph) → Crook County stays yellow (rural check) → guardian view for a synthetic resident at Mi Casa → staff takes a live photo at lunch, the guardian timeline flips to verified in real time → guardian disputes the billed physical therapy → it shows up in the investigator's Guardian reports for Mi Casa.

**Changes vs. the locked brief:** a chain IS used (Base Sepolia, 3 signers, see `HANDOFF.md`); staffing is in scope (Leo); guardian/consumer view added alongside the MFCU buyer. Facility colour roll-up takes SPEND's contribution from the `spend_overall` card. Correct headline stats are in `04-spend-evidence.md` (~$64B Medicaid, not $90B; $11.23B related-party, not "$12B Harvard").

**Honest caveat for "no facility cooperation":** the investigator side needs none. The guardian timeline is what an honest facility opts into, and a facility that won't, or whose timeline doesn't match its billing, is itself a signal.

---


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

## Scope (locked, updated Nov 22 mid-build)

**IN:**
- Procurement / phantom-spending detection (the 3-signal fusion above).
- Static JSON data + pre-baked fraud scenarios.
- Signed JSON + hash evidence pack.
- **On-chain commitment layer.** VerityCommit contract on Base Sepolia. Four claim-type signers (facility / ombudsman / verity_service / staff). Dashboard commits every signal card + exported case file + proof-of-service event. Judges click Basescan links from the UI.
- **Proof-of-Service pillar** (replaces the Voice pillar — rejected mid-build). Staff uploads a photo of a delivered service (meal, insulin shot, visit) → image pinned to IPFS (Pinata) → metadata JSON pinned to IPFS → sha256(canonical metadata) committed on-chain via the staff wallet. Verifier can refetch metadata from IPFS and recompute the hash independently; the on-chain record proves the facility committed to that exact service event at that exact time.

**OUT for tonight:**
- Staffing-fraud module. Noted on competitive slide as "future module," not built.
- Voice attestation (Vapi / 11Labs) — CUT mid-build. Replaced by Proof-of-Service (staff-side) which is architecturally stronger (no PHI, verifiable image hash, no transcription uncertainty).
- Facility EHR integration (never in scope — that's the moat).
- Real HIPAA / PHI (pseudonymous IDs only in any UI or IPFS payload).
- ZK proofs. Judge-trap bait; defended in Q&A.
- Multisig. Honest "one key per signer role is correct" answer in Q&A.

## Stack (locked, updated Nov 22 mid-build)

- Frontend: plain HTML + Tailwind CDN + Alpine.js + vis-network. One `apps/dashboard/index.html`. No Next.js scaffolding.
- Backend services:
  - `apps/dashboard` (FastAPI, :8000) — serves the UI, proxies `/spend`, `/chain`, `/delivery` to other services.
  - `apps/onchain` (FastAPI, :8001) — holds all four signing wallets + ed25519 case-file key + Pinata uploader. Every commit flows through here.
  - `apps/phantom-spend` (Abhi's FastAPI, :8003) — SPEND signals.
  - `apps/phantom-shift` (Leo's, :8002) — not yet shipped.
- Crypto: Solidity `VerityCommit` on Base Sepolia (`0x052934b9db3677b5943a8882CA6bd93868245729 (redeployed Nov 22 for claim_type=6)`). Four distinct signer wallets. Ed25519 envelope sig on exported case files. SHA-256 content hashes. IPFS via Pinata for proof-of-service.
- PDF: `window.print()` on the case-file view.

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
- **"Why not blockchain?"** → DECISION REVERSED mid-build. We DO use chain for append-only attestation anchors. Not for storage, not for payments, not for consensus. One contract, one function (`commit(uint8, bytes32)`), four distinct signer wallets so Basescan shows "separation of attestation authority" per claim type.
- **"Why no MetaMask / browser wallet?"** → This isn't a consumer product — there's no user signing their own asset. The claims we anchor are institutional: the facility attests to its own tap logs, the ombudsman attests to its own call logs, we attest to our own computations, and staff attest to services they delivered. Those are backend attestations by legally-responsible entities, not personal signatures. The one place a human belongs on-chain is the MFCU investigator confirming they reviewed the case — that's a passkey or hardware-wallet moment at CASEFILE export time, on the production roadmap as a 2-of-2 (investigator + service) signature.
- **"Why IPFS for the delivery photos and not S3?"** → Content addressing. The on-chain record contains `sha256(canonical(metadata))` where metadata includes the IPFS CID of the photo. If anyone changes the photo or the metadata, the CID changes and the hash no longer matches what's on-chain. S3 can't give you that property — the facility could swap the photo and the URL would still work. This is the Walmart-receipt-photo pattern applied properly: the receipt is addressable by what it IS, not where it's stored.

## Competitive matrix (for the slide)

| Solution | Reference-price? | Related-party ownership? | Census/staffing cross-check? | Investigator-ready packet? |
|---|---|---|---|---|
| PointClickCare family portal | ❌ | ❌ | ❌ | ❌ |
| CMS Nursing Home Compare | ❌ | ❌ | Partial | ❌ |
| LifeLoop / CarePredict | ❌ | ❌ | ❌ | ❌ |
| MFCU manual audits | ✅ (slow) | ✅ (slow) | ✅ (slow) | They *are* the investigator |
| **Verity Care** | ✅ | ✅ | ✅ | ✅ (signed + hashed + chain-anchored) |

Pitch line: *"Everyone else protects the resident's experience. We protect the resident's dollars. We're the first tool built for the investigator, not the family."*

## Mid-build decision log (Nov 22, in build order)

- Added **VerityCommit** Solidity contract + on-chain anchoring. Was explicitly OUT; teammate push to add chain made it a win: judges click Basescan links from every signal.
- Added **three signer wallets** (facility / ombudsman / verity_service) to give distinct `committer` addresses per claim type → "separation of attestation authority."
- Added **fourth signer (staff)** when we added Proof-of-Service.
- **Killed Voice pillar.** Replaced with **Proof-of-Service** (staff photo + IPFS + chain commit). Architecturally stronger: no PHI, deterministic verification, Walmart-receipt-photo semantic maps cleanly.
- **IPFS via Pinata** for Proof-of-Service metadata + images. Hash of canonical metadata is the on-chain claim. Verifier can refetch from any IPFS gateway and recompute the hash.
- Locked **backend-signed per institution, no browser wallet.** Judge-trap answer above.
