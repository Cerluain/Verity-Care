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

- (Nov 22) Scope locked: 3 pillars (Spend + Shift + Voice), not 2. Voice ships via Vapi+11Labs+Twilio live call during pitch.
- (Nov 22) Project named **Verity Care**.
- (Nov 22) Chain pick: Base Sepolia. Public, free, Basescan links credible in PDF.
- (Nov 22) No multisig tonight. Roadmap slide only.
- (Nov 22) No ZK staffing circuit tonight. Trajectory invariants computed in plain code. UI says "verifiable" with roadmap asterisk.
- (Nov 22) ZK invoice proof on Spend = P2 stretch for Dev A. Cut first if behind.
- (Nov 22) Target buyer = state MFCU. B2G framing.
- (Nov 22) Montana rural yellow safety tile is P0 — kills "rural thin-market" judge-trap.
- (Nov 22) Each dev owns Q&A for their pillar; I own pitch narration + architecture Q&A.

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
