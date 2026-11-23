# Saswata — context

GitHub: SD170. Role: Dev C — integrator, chain / launchpad owner, voice pillar, case file aggregation, pitch narration.

## Background relevant to this hack

- ASU MS CS. Fall 2026 CPT at Vapi Inc (SF, remote from AZ) — comfortable with Vapi agents, webhooks, Twilio integration end-to-end.
- Backend / systems focused: APIs, data pipelines, SDKs, integrations. Can do frontend when needed, less interested.
- Comfortable with Solidity + ethers.js + anvil (AttentionRank, keeper bots, verifiable credentials demos).
- TS + Python both fluent.

## The product (locked)

**Verity Care** — nursing home fraud detection for state Medicaid Fraud Control Units. Three pillars, one case file:

1. **Phantom Spend** — procurement fraud (reference delta + ownership graph + volume sanity). Owner: Dev A.
2. **Phantom Shift** — staffing fraud (NFC tap trails + cross-facility license collision + credential validity + impossible-travel). Owner: Dev B (Leo).
3. **Resident Voice** — Vapi + 11Labs call to random residents to cross-verify facility claims. Owner: Dev C (me).

Capstone: signed + hashed + chain-anchored MFCU referral packet. Owner: me.

Target buyer: state MFCU (53 across states + territories, recover ~$1B/yr nationally with spreadsheets).

## Two UIs

- **UI 1 — Investigator Dashboard** (public demo surface). Single page, 4 tabs (SPEND / SHIFT / VOICE / CASE FILE), left-rail facility list. I own the shell. Dev A owns SPEND tab components. Dev B owns SHIFT tab components. I own VOICE + CASE FILE tabs.
- **UI 2 — Facility Intake Console** (data-in surface, minimal). One page, 3 widget slots (cost-report upload, live NFC tap feed, resident enrollment). I scaffold the page. Dev A drops cost-report upload widget. Dev B drops live NFC tap feed widget.

## Chain architecture

One tiny Solidity contract `VerityCommit.sol` deployed to Base Sepolia. One function: `commit(uint8 claimType, bytes32 claimHash)` emits an event. Shared JS helper `commit(claimType, hash) → txHash`. Everyone imports; everyone anchors their own claims.

- Dev B anchors every NFC tap at capture time. One line in `/live-tap` handler. Facility cannot retroactively edit the log.
- Dev C (me) anchors every Voice attestation + the final case file. Shown as Basescan links in the PDF.
- Dev A does NOT anchor. Spend signals run on public CMS data; no claims-at-capture-time to anchor. Honest answer in Q&A.

No multisig tonight. Roadmap slide only.

---

## Dev A — Phantom Spend tasks (priority order)

### P0 — Must ship (pitch dies without these)
1. Pull CMS ASP quarterly file for 20 common SNF drugs. Normalize to one lookup table.
2. Pull NADAC via Socrata API for the same drugs. Join to ASP table.
3. Hand-pull 10 Cost Plus Drugs prices manually.
4. Author line items for 6 facilities: 12 drug/supply rows each. Three facilities carry fraud patterns, one is ambiguous rural, two are clean.
5. Author ownership graphs for 6 facilities. Three show sister-LLC overlap (model on Portopiccolo + Centers Health Care from ProPublica). One shows clean family ownership. Two blank.
6. Write scoring function: reference-price delta per line item, returns red/yellow/green with headline string.
7. Write scoring function: ownership overlap. Walks the graph, returns hop count, severity.
8. Write scoring function: volume-vs-census. Takes billed units, PBJ resident-days from shared data, assumed diabetic fraction, returns overbill ratio.
9. Build SPEND tab: 12 rows of line items in a table.
10. Build three signal cards stacked above the table.
11. Build the ownership force-graph using vis-network. Clicking a flagged row renders it.
12. Montana rural case: force the overall severity to yellow when only signal 1 is red.

### P1 — Should ship
13. Add "upload cost report CSV" widget on the facility intake page. Mock — accepts file, computes hash, logs to console.
14. Add citation footer to each signal card ("Source: CMS ASP Q3 2026 [link]").
15. Add hover-over tooltips on the ownership graph showing LLC details.

### P2 — Stretch (cut first)
16. ZK invoice-integrity proof in Noir. One drug, one invoice. Pre-generated proof, in-browser verify button.

Notes for Dev A:
- Tasks 1–3, 6–8, 9–12 are the pitch spine. If any is missing, SPEND tab cannot be demoed.
- Tasks 4–5 are the data authoring — takes longer than estimated. Start first.
- Dev A owns Q&A for: procurement fraud, reference prices, PE nursing home chains, PECOS, ownership opacity, "why not just NADAC."

---

## Dev B (Leo) — Phantom Shift tasks (priority order)

### P0 — Must ship
1. Pull a real PBJ CSV from data.cms.gov. Use it to get real resident-day counts and facility CCNs for the 6 facilities.
2. Author nurse roster: 40 nurses × 6 facilities, each with an AZ-RN format license number, hire date, role.
3. Author 30-day shift schedule for each facility from the roster. Bake in 3 cross-facility collisions, 2 post-suspension patterns.
4. Author AZ Board of Nursing synthetic registry with 2 suspension events on specific dates.
5. Author door geometry for one facility: 5 door coordinates (feet from origin) representing Entrance, Med Room, Wing C, Supply Closet, Memory Care.
6. Write scoring function: cross-facility license collision. Scans all shifts, finds overlapping hours for same license across facilities.
7. Write scoring function: credential validity at shift time. Checks each shift against licensure registry on that date.
8. Write scoring function: impossible-travel. Takes consecutive taps, computes speed, flags over v_max.
9. Build SHIFT tab: top card with claimed HPRD → adjusted HPRD math breakdown.
10. Build license-collision force-graph. Nurses as nodes, facilities as nodes, edges where they appear.
11. Build suspended-license table with timeline.
12. Build `/live-tap` POST endpoint receiving tap events from phones.
13. Configure phones: iPhone Shortcuts automation OR Android app that POSTs tap event on NTAG scan. Test end-to-end before H4.
14. Build live tap panel in SHIFT tab that animates the path in real time.
15. Rehearse the live demo 3× in the actual room. Confirm WiFi, confirm phones hit the endpoint.

### P1 — Should ship
16. Call Dev C's `commit` helper on every tap. Show returned tx hash next to each tap in the live panel.
17. Add live-tap widget to the facility intake page (same data, different page).
18. Build the cross-facility collision scenario rehearsal: pre-configure two phones, lock the sticker layout.

### P2 — Stretch
19. Impossible-travel scenario in the live demo. Only runs if NFC stickers are sourced.
20. Add role-misclassification signal using statistical acuity-vs-staffing anomaly.

Notes for Dev B:
- Tasks 1–11 = the on-paper demo. Static data + graph. Lands even without live NFC.
- Tasks 12–15 = live-on-stage moment. Highest-risk, highest-reward. Rehearse early.
- NFC sticker sourcing is a H0 decision. If no stickers by H1, fall back to phone-HCE between two Androids. If neither works, cut live and show pre-recorded animation.
- Dev B owns Q&A for: 2024 CMS minimum staffing rule, PBJ limitations, state nursing boards, "nursing homes already use NFC badges — what's new."

---

## Dev C (me) — Integrator + Launchpad + Voice + Case File tasks (priority order)

### P0 — Must ship
1. Write Solidity contract: `VerityCommit.sol` with one `commit(uint8 claimType, bytes32 claimHash)` function emitting an event. ~40 lines.
2. Deploy `VerityCommit` to Base Sepolia. Fund wallet from faucet.
3. Write JS helper: `commit(claimType, claimHash) → txHash`. Export to Dev A and Dev B. **Must land by end of H1 — Dev A and Dev B wait on it.**
4. Author shared JSON schemas: `signal-card.schema.json`, `case-file.schema.json`, `facilities.json`.
5. Scaffold `apps/dashboard/index.html` with Tailwind + Alpine + vis-network from CDN.
6. Build left-rail facility list reading from `facilities.json`.
7. Build tab routing: SPEND, SHIFT, VOICE, CASE FILE.
8. Scaffold `apps/dashboard/facility.html` — the facility intake console with 3 widget slots.
9. Configure Vapi agent: prompt = "Jenny, ombudsman, open-ended questions, 60-second limit." Phone number provisioned.
10. Record 2 fallback 11Labs voice clips (20 seconds each) in case Vapi fails live.
11. Build VOICE tab: "Call Mary" button triggers Vapi call to presenter's phone. Transcript streams in.
12. Write reconciliation: keyword match of resident answer against facility's claimed meal/activity. Red flag card on mismatch.
13. Build CASE FILE tab: aggregates signal JSON from SPEND, SHIFT, VOICE into one envelope.
14. ed25519 sign with PyNacl (~20 lines).
15. SHA-256 content hash. Print in PDF footer.
16. Render case file to PDF via `window.print()` on a styled page.
17. Chain-anchor the case file: commit its hash to `VerityCommit` on Base Sepolia. Show tx link.
18. Write pitch script: 90 seconds, opens with $12B figure, ends with the $340K/yr-per-facility ask.
19. Build 3-slide deck: title, competitive matrix, ask.
20. Rehearse the 3× timed run-through.

### P1 — Should ship
21. In CASE FILE tab, show Basescan links for every chain commitment (every tap, every voice attestation, the case file itself).
22. Add "view on-chain" mini-badges next to chain-anchored items.
23. Facility intake page: wire the 3 widget slots to SPEND (cost-report upload), SHIFT (live tap feed), VOICE (resident enrollment list).
24. OBS screen-record the full Vapi call as fallback clip.

### P2 — Stretch
25. Multi-sig stub: show the case file "would be countersigned by MFCU" as a roadmap note in the PDF. Not actually implemented.
26. Auto-DM the chain tx hashes to a demo-room Discord so there's external witness.

Notes for me:
- Tasks 1–3 unblock everyone else. Nail them first. **End of H1 = chain helper live.**
- Tasks 4–8 = the shell. Nobody can preview their components until schemas + facility data land.
- Tasks 9–16 = Voice + Case File.
- Task 17 = chain capstone. "Case file on-chain" is the biggest crypto flex in the pitch.
- Tasks 18–20 = the pitch itself. Nobody cares about the UI if the pitch isn't rehearsed.
- I own Q&A for: integration architecture, voice pillar + dementia stratification, HIPAA, "why not blockchain" (answer: we DO use it, selectively), ed25519 + Merkle commitment choices.

---

## Cross-dev dependencies (the glue)

- My commit helper (task 3) must land by end of H1. Dev A and Dev B wait on it.
- Dev A's SPEND signal cards consume my `signal-card.schema.json` (task 4). Dev A can't stub cleanly until schema is locked.
- Dev B's `/live-tap` endpoint (task 12) depends on shared facility data (task 4) being in place.
- NFC sticker vs phone-HCE decision is a H0 call affecting Dev B tasks 13–15. Lock in the H0 meeting.
- Base Sepolia faucet reachable from venue WiFi — I test this in H0.

## Decisions log

- (Nov 22) Scope locked: 3 pillars (Spend + Shift + Voice), not 2. Voice later REPLACED by Proof-of-Service pillar mid-build (see below).
- (Nov 22) Project named **Verity Care**.
- (Nov 22) Chain pick: **Base Sepolia** (chainId 84532). Coinbase CDP faucet (https://portal.cdp.coinbase.com/products/faucet) — email signup, 0.05 ETH, no mainnet-balance gate. Alchemy + QuickNode faucets ruled out (both require 0.001 mainnet ETH). Thirdweb is backup. Solana devnet rejected: public-RPC airdrop returns 410, no Solana reps on team.
- (Nov 22) No multisig tonight. Roadmap slide only.
- (Nov 22) No ZK staffing circuit tonight. Trajectory invariants computed in plain code. UI says "verifiable" with roadmap asterisk.
- (Nov 22) ZK invoice proof on Spend = P2 stretch for Dev A. Cut first if behind.
- (Nov 22) Target buyer = state MFCU. B2G framing.
- (Nov 22) Montana rural yellow safety tile is P0 — kills "rural thin-market" judge-trap.
- (Nov 22) Each dev owns Q&A for their pillar; I own pitch narration + architecture Q&A.
- (Nov 22) Signing model LOCKED: **backend wallets per legally-responsible institution** (facility / ombudsman / verity_service), one wallet per claim type. No browser wallet for TAP / SIGNAL_CARD / VOICE because those are institutional attestations, not personal. CASEFILE roadmap: 2-of-2 (MFCU investigator passkey/hardware wallet + verity_service backend) because that's the one human-in-the-loop moment. This kills the "why no MetaMask" judge question.
- (Nov 22, mid-build) **VOICE pillar CUT, Proof-of-Service pillar ADDED.** 11Labs / voice attestation was architecturally weak (PHI risk, transcription uncertainty, no deterministic verification). Replaced with staff-side photo-of-delivery: staff takes a photo of a delivered service (meal / insulin shot / visit), the service pins the image to IPFS via Pinata, builds a metadata JSON {facility_id, patient_pseudonym, service_type, service_detail, staff_pseudonym, delivered_at, image:{cid, sha256, mime, size}}, pins the metadata to IPFS, sha256 of canonical metadata is committed on-chain with claim_type=5 signed by the STAFF wallet. Verifier can refetch metadata from any IPFS gateway and recompute the hash — this is the Walmart-receipt-photo pattern applied with content-addressing.
- (Nov 22, mid-build) **Fourth signer added: STAFF** (`0xdbbF6AF9F46E85ee39c2448bc807A51cfc4d497B`). Funded 0.001 ETH from deployer. Signs claim_type=5 (PROOF_OF_SERVICE).
- (Nov 22, mid-build) **Contract redeployed** at `0x052934b9db3677b5943a8882CA6bd93868245729 (redeployed Nov 22 for claim_type=6)` to extend claim_type range to 1..5. Old deployment `0xF806…` is dead; everywhere references the new address.
- (Nov 22, mid-build) **Pinata selected** as IPFS provider (free tier 1 GB, JWT-based, fast gateway). Service falls back to `bafkmock…` deterministic CIDs when no JWT is set, so UI builds without a Pinata account. User has filled the real JWT into `apps/onchain/.env` → uploads now produce real `QmXXX…` CIDs visible at `gateway.pinata.cloud`.
- (Nov 22, mid-build) **Chain is the database.** No Postgres / Supabase added. Local `apps/onchain/data/commit-log.jsonl` is the fast cache; chain is the trust root. Dashboard rehydrates every card on load by canonical-hashing the signal card, calling `GET /chain/verify/by-hash?claim_type=4&claim_hash=…`, and attaching the committed `chain_commit` if found. Refresh never loses state.
- (Nov 22, mid-build) **Server-side `block_number` backfill.** `/commits`, `/deliveries`, and `/verify` all resolve pending transaction receipts from chain BEFORE responding, so the UI never has to poll for confirmation. Fire-and-forget commits at write time (sub-second response) + on-read backfill (block number appears automatically). Three endpoints write log rows with `block_number=null` and the three GETs promote them to real block numbers before returning.
- (Nov 22, mid-build) **UI reactivity rule: enrich-then-assign.** Alpine proxies arrays/objects on assignment. If you set `this.spend = j` first and then mutate `j.signals[i].chain_commit`, the mutation never hits the proxy and the UI never re-renders. Fix: rehydrate / enrich ALL nested fields on `j` first, THEN assign to `this.spend`. Same pattern applies to `this.shiftSignals`. Hit this twice, locked as a rule.
- (Nov 22, mid-build) **Investigator-side form defaults from the backend.** `GET /delivery/defaults` returns rotating patient/staff/service values (per-second deterministic). The PoS tab fetches this on facility select and after every submit, pre-filling the form with the exact values a blank POST would substitute. Fields marked `required` — no `(auto)` / `(optional)` placeholders. User explicitly asked for backend-owned defaults, not UI affordances.
- (Nov 22, mid-build) **CASE FILE tab shipped.** Aggregator pattern: SPEND signals + SHIFT signals + Delivery proofs → canonical-JSON envelope → SHA-256 → ed25519 sign via `/sign` → `commit(claim_type=3)` signed by `verity_service` wallet → poller backfills block → "Print to PDF" via `window.print()`. Same four-state chain footer SPEND cards use (idle → committing → pending → confirmed + re-verify). Tab deeplinking via `#tab=case%20file` for pitch slide links.
- (Nov 22, mid-build) **Staff ↔ Guardian ↔ Investigator thread, one patient.** Vishak's `/care/*` sqlite subsystem (`care.py` + `care_db.py`) pins the staff+guardian views to `mi-casa-life-care-az` and uses real resident IDs (`res-rosa`, `res-walter`, `res-mae`, …). Staff login IDs are `RN-1187` / `LPN-0412` / `CNA-2231` / `CNA-2240` / `PT-0907` / `OT-0310`. When staff POSTs to `/care/events` with a photo, the handler forwards to `apps/onchain /delivery` with `patient_pseudonym=res-rosa`, pins to Pinata, commits to chain. The investigator's PoS tab for **Mi Casa Nursing Center** then shows that exact upload with the real `res-rosa` patient ID + Basescan link, AND the guardian timeline for Rosa flips `res-rosa:insulin-am` from `upcoming` to `verified` with that same tx hash. One real event threads all three views. **Caveat:** PoS-tab's upload form (on Buffalo, Accordius, etc.) uses stock pseudonyms (`patient-A17`, `patient-Z99`), NOT resident IDs — different subsystem, different facility. The staff↔guardian thread ONLY works on Mi Casa.
- (Nov 22, mid-build) **Three-wallet signer map, locked:**
  - `facility` `0xB281013450EE41d4634246A927A7663f12153cB3` → claim types 1 (TAP), 4 (SIGNAL_CARD)
  - `ombudsman` `0xD138267Fd0FD4Ecd44dbeF7a1b720176792e538F` → claim type 2 (VOICE, dormant — pillar cut)
  - `verity_service` `0x113B1E33d5DeE49e2e91Bd869A2CFA501B12269F` → claim type 3 (CASEFILE)
  - `staff` `0xdbbF6AF9F46E85ee39c2448bc807A51cfc4d497B` → claim type 5 (PROOF_OF_SERVICE)
  Each funded 0.001 ETH from deployer `0x90ECCC…`. Four distinct `committer` addresses on Basescan — "separation of attestation authority" pitch line.
- (Nov 22, late-build) **Inventory pillar added. Contract redeployed at `0x052934b9db3677b5943a8882CA6bd93868245729` to add claim_type=6 (INVENTORY_SNAPSHOT) signed by facility wallet.** New `/facility` operator route — monthly receipt-photo upload → IPFS pin → canonical JSON hash → facility-wallet commit. Two-click flow (parse photo → edit line items → sign & anchor) so the operator can correct OCR drift before signing. Legacy one-shot `/facility/inventory/snapshot` retained for the seed script only.
- (Nov 22, late-build) **SIGNER_ROLE map updated: claim_type=4 (SIGNAL_CARD) now signed by verity_service, not facility.** Analytics outputs belong to Verity Care — the facility didn't compute them. Dashboard `/spend` + `/shift` were briefly auto-anchoring on first fetch; both reverted because the 3-signal SPEND cards have been folded into the drug-level view (see below).
- (Nov 22, late-build) **Postgres (Neon) index layer.** `apps/onchain/db.py` with ThreadedConnectionPool, tables `commits` + `deliveries`. Dual-write from `/commit` and `/delivery`; reads prefer DB, fall back to JSONL. `/verify?claim_hash=…` now hits Postgres FIRST — kills the chain-RPC tax on facility-switch rehydration (3s → 0.9s on second click). `_db_url()` is lazy so `load_dotenv()` ordering is safe. Migrations via `scripts/migrate.py up|down|reset|status`. `psycopg2-binary==2.9.10` in `apps/onchain/requirements.txt`.
- (Nov 22, late-build) **`scripts/purge.sh` one-command demo reset.** Wipes Postgres (`commits` + `deliveries`), rotates both JSONLs (`commit-log.jsonl` + `inventory-log.jsonl`) with `.bak` timestamps, nukes care sqlite + photo cache via `/care/reset`, AND re-anchors Mi Casa Sep + Oct inventory snapshots via `scripts/seed_mi_casa_timeline.sh`. Nov deliberately left un-anchored so the live-pitch upload lands the third tx in front of the judges. Casefile dummy history at `data/demo/casefile-history/mi-casa-life-care-az.json` is static — survives purge, renders the audit timeline on first paint.
- (Nov 22, late-build) **Time-window classifier + 6-status care model.** `apps/dashboard/care.py` `CATEGORY_WINDOW`: medication ±10, vitals ±20/30, meal ±20/45, therapy ±60/120, activity ±60/180. Status set: `upcoming` / `due` / `delayed` / `verified` / `verified_late` / `disputed`. `_classify()` uses `(now, scheduled, window, event_ts)`; `_hhmm_from_iso()` converts UTC → local via `datetime.fromisoformat().astimezone()`. `/care/reports` surfaces `kind=delayed` + `kind=verified_late` + `kind=dispute` to the investigator GUARDIAN REPORTS tab (pill colors: dispute/delayed=red, verified_late=yellow). Guardian timeline uses 5-col counts grid.
- (Nov 22, late-build) **Dashboard no-cache headers on `/` and `/facility`.** `Cache-Control: no-store, must-revalidate`. Users were seeing stale UI (removed tabs still appearing) because browser cached the old `index.html`. Static `/static/` assets unaffected.
- (Nov 22, late-build) **Three-tab investigator view, default for every facility.** Dropped `staffing` + `proof of service` from `tabs` entirely — neither has demo data, and keeping them required a per-facility override map. Default tabs now: `['spending', 'guardian reports', 'case file']`. Both the investigator dashboard AND the facility operator UI default-select Mi Casa on page load (`facilities.find(f => f.id === 'mi-casa-life-care-az') || facilities[0]`).
- (Nov 22, late-build) **SPENDING tab unified: 3-signal view REMOVED, drug-level IS the view.** Earlier toggle between "3-signal fraud view" and "drug-level view" was confusing — both flagged Mi Casa but with different numbers (3-signal from stale Abhi fixture, drug-level from fresh inventory). Dropped the toggle, deleted the 3-signal block (~336 lines in index.html), kept drug-level. Per-drug tile now 6-col grid: residents · expected · invoiced · **NADAC fair price** · on-hand Δ · disparity. NADAC value pulled inline from `data/clinical/drug_rates.json` with "CMS Nov 2026" label. Markup pill color-coded red/amber by `>1.5x`.
- (Nov 22, late-build) **On-chain inventory snapshot strip above drug tiles.** 3-card row (one per anchored period), each showing: IPFS-pinned receipt photo (clickable → gateway), period · supplier · receipt total · block pill (or 'pending' pulse) · Basescan + metadata links · truncated tx hash. `isNew(s)` returns true for snapshots < 2min old → red "NEW" badge. Seeded Sep + Oct never trigger the badge; the live-pitch Nov upload does.
- (Nov 22, late-build) **Drug tile source link: DailyMed only.** Tested CMS NADAC Socrata API (query filter syntax doesn't match, dataset is 2022 archive), SearchRx (now redirects to Optum perks), api.fda.gov JSON (not human-readable). Only DailyMed-by-name consistently returns a working FDA-registered label page. Backend emits `search_name` stripped of dose/packaging ("Insulin lispro 10 mL vial" → "Insulin lispro") via `re.split(r"\s+\d|\s+\(", raw, maxsplit=1)[0]`. One "View FDA label ↗" button per tile, NDC printed inline.
- (Nov 22, late-build) **CASE FILE audit timeline + per-facility KPIs.** Case file tab now opens on cumulative data regardless of entry point (`x-init` + `x-effect` call `loadSnapshotCards + loadDrugDisparity + loadGuardianReports + loadCaseFileHistory`). 4-col KPI strip: **inventory anchors** · **phantom spend** (from `drug.data.roll_up.combined_phantom_spend`) · **guardian flags** (dispute + delayed counts) · **prior sign-offs** (count + relative-time "last X ago"). Audit timeline is a vertical dot-per-commit list with `claim_type=3` rows from `/chain/commits?facility_id=…&claim_type=3`. Dummy history for Mi Casa has 2 pre-staged rows (12d / 4d ago, verity_service signer, real-shaped tx hashes).
- (Nov 22, late-build) **UTF-8-safe base64 in `generateCaseFile()`.** `btoa()` was crashing on em-dashes and check-marks inside the envelope JSON. Switched to `btoa(String.fromCharCode(...new TextEncoder().encode(canon)))`.
- (Nov 22, late-build) **Mi Casa 3-month inventory narrative.** Pre-staged fixtures + Gemini-generated receipt photos at `data/demo/inventory-sample-mi-casa-2026-{09,10,11}.jpg` + matching JSON at `data/demo/inventory-fixtures/mi-casa-life-care-az-2026-{09,10,11}.json`. Sep: AmeriSourceBergen SW, insulin 72 @ $28.40, $2,878.80 total (NADAC-compliant). Oct: **supplier switched** to MedSupply Southwest, insulin 88 @ $47.80, $5,628.30 (+68% unit price jump). Nov: MedSupply Southwest, insulin 102 @ $50.20, $6,738.70 (markup climbing). Other facilities' fixtures deleted — Mi Casa is the only demo narrative. Facility UI period dropdown discovered from backend via new `GET /facility/inventory/periods/{facility_id}` endpoint.
- (Nov 22, late-build) **Backend wallet redistribute.** Facility wallet ended up with $0.0053 while verity_service was down to $0.0002 (insufficient-gas error during /commit). One-shot Python script sent 0.002 ETH each from facility → verity_service / staff / ombudsman. Capacity restored to ~20 txs per wallet.
- (Nov 22, late-build) **Reads prefer DB, chain is write-only.** `/verify`, `/commits`, `/facility/inventory` all read Postgres first; chain-backfill only runs when at least one row is missing `block_number`. When backfill succeeds, `db.update_block_number(tx, block, signer_role, signer_address)` persists it → every subsequent read is pure DB.

## Open questions

- Third dev (Dev A) name? Need it to create their context file.
- NFC sticker sourcing: physical NTAG215s in hand, or Android-HCE fallback?
- Vapi phone number already provisioned, or do I spin one up in H0?
- OBS pre-recorded fallback clip — who records it (me) and when (H5)?

## Blockers / needs

- Base Sepolia wallet funded before H1 ends.
- Vapi + 11Labs + Twilio keys in `.env` by H1 end.
- Confirmation venue WiFi reaches data.medicaid.gov + base-sepolia RPC + openpaymentsdata.cms.gov + github.com.

## TODO from Leo — lock live-tap chain and capture hardware

### [ ] TODO 1 — Confirm `/live-tap` commit runtime and lock the NFC capture mechanism (P0, ~10 min)

Decide whether `POST /live-tap` calls `VerityCommit.commit()` directly from the FastAPI backend with `web3.py`, or whether the browser/phone-side flow calls Saswata's existing JS helper. Confirm the H0 hardware choice: physical NTAG215 stickers or phone-to-endpoint HTTP triggers (including Android HCE or iOS Shortcuts). Record the decision and the exact payload path so `/live-tap`, the SHIFT tab, and the facility intake feed use one implementation.
