# Leo — context

GitHub: Cerluain. Role: **Dev B — Phantom Shift** (staffing fraud pillar).

## What I own in this project

The SHIFT pillar end to end: PBJ baseline data, synthetic nurse rosters/schedules/AZ Board of Nursing suspensions, spatial-temporal & credential scoring functions, SHIFT-tab UI components, and the `/live-tap` NFC capture pipeline built on top of Saswata's Base Sepolia `commit` helper (`VerityCommit.sol`). Task list mirrors Dev B in `saswata.md`.

### P0 — Must ship
- [ ] 1. Pull real PBJ CSV from `data.cms.gov` → extract resident-day counts and CCNs for the 6 facilities — **start first (unblocks Abi's Signal 3)**
- [ ] 2. Author nurse roster: 40 nurses × 6 facilities (`AZ-RN` license format, hire date, role)
- [ ] 3. Author 30-day shift schedule per facility with 3 cross-facility collisions and 2 post-suspension shifts baked in
- [ ] 4. Author synthetic AZ Board of Nursing registry with 2 suspension events on specific dates
- [ ] 5. Author door geometry for 1 facility: 5 coordinates (feet from origin) for `Entrance`, `Med Room`, `Wing C`, `Supply Closet`, and `Memory Care`
- [ ] 6. Scoring: cross-facility license collision (overlapping shift hours for same license across facilities)
- [ ] 7. Scoring: credential validity at shift time (shift date vs. board suspension date)
- [ ] 8. Scoring: impossible-travel ($d(\text{Door}_A, \text{Door}_B) / \Delta t > v_{\max}$ across consecutive taps)
- [ ] 9. SHIFT tab: top summary card with `Claimed HPRD → Adjusted HPRD` breakdown after stripping ghost/suspended hours
- [ ] 10. SHIFT tab: `vis-network` license-collision force graph (nurses ↔ facilities)
- [ ] 11. SHIFT tab: suspended-license table with timeline
- [ ] 12. Build `POST /live-tap` endpoint receiving NFC tap events from phones
- [ ] 13. Configure phones (Android HTTP POST automation or iPhone Shortcuts on NTAG215 stickers) and test hitting `/live-tap` before H4
- [ ] 14. Build live tap panel in SHIFT tab animating the nurse's floor path in real time
- [ ] 15. Rehearse live tap demo 3× in the venue room (verify WiFi + phone-to-endpoint reachability)

### P1 — Should ship
- [ ] 16. Wire Saswata's `commit(claimType, claimHash) → txHash` helper inside `/live-tap` so every NFC tap is anchored on Base Sepolia at capture time with a clickable tx hash
- [ ] 17. Drop live-tap feed widget into the facility intake console (`facility.html`)
- [ ] 18. Lock two-phone cross-facility collision rehearsal and sticker layout

### P2 — Stretch (cut first)
- [ ] 19. Live impossible-travel trigger during stage demo (requires physical NFC stickers in room)
- [ ] 20. Role-misclassification signal using acuity-vs-staffing anomaly

## Q&A I own

- **2024 CMS minimum staffing rule:** Rescinded effective Feb 2, 2026 via CMS Interim Final Rule (leaving state staffing floors, enhanced facility assessments, and Care Compare Five-Star staffing ratings as the primary accountability levers).
- **PBJ limitations:** Quarterly, self-reported, uses facility-local IDs (missing cross-facility RN license collisions), and doesn't cross-check state nursing board suspension dates in real time (June 2026 HHS-OIG audit A-09-24-02005 found 45% of sampled RNs had unsupported PBJ hours).
- **"Nursing homes already use NFC badges — what's new?":** Legacy readers log locally in mutable facility databases and miss badge handoffs at a single desk; Verity Care enforces multi-door physical travel bounds and anchors every tap hash to Base Sepolia at capture time so facilities cannot retroactively edit shift logs.

## What I do NOT own

- Dashboard shell (`index.html`), intake console shell (`facility.html`), tab routing, shared schemas, Base Sepolia `VerityCommit.sol` contract/helper, Voice, and Case File aggregation (Saswata / Dev C).
- SPEND pillar (Abi / Dev A).
- Zero-Knowledge circuits (cut per team decision — trajectory invariants run in plain code with a roadmap asterisk).

## Dependencies on others (and what others need from me)

- **Saswata (Dev C):** `facilities.json` + `signal-card.schema.json` (task 4), dashboard shells (tasks 5–8), and the `commit(claimType, claimHash) → txHash` helper (task 3, due end of H1) so `/live-tap` can anchor taps on Base Sepolia.
- **Abi (Dev A) depends on me:** Needs my Task 1 PBJ resident-day counts + facility CCNs to compute Signal 3 (`volume_sanity`).

## Open questions I'm tracking

- **NFC hardware lock (H0):** Do we have physical NTAG215 stickers in hand, or are we using two Android phones via HTTP POST / HCE fallback?
- **Chain helper runtime:** Is Saswata exposing `commit()` as a JS helper called from the frontend on tap, or should `/live-tap` call it server-side in Python (`web3.py`) so phone POSTs only need one lightweight HTTP request?
- **Shared 6-facility list:** Confirming exact CCNs/states with Abi and Saswata (including Abi's Montana rural facility) so PBJ pulls align across SPEND and SHIFT.

## My ideas / direction

- Ship the static spine (Tasks 1–11) first so the SHIFT tab, HPRD math breakdown, collision graph, and suspended-license timeline are 100% demo-ready before relying on live phone WiFi.
- Hash each tap payload (`facility_id`, `license_id`, `door_id`, `timestamp`) and pass it to Saswata's `commit()` helper at capture time so both the Investigator Dashboard and Facility Intake Console show live Basescan links per scan.

## Decisions I've made

- (Nov 22) Taking Dev B — Phantom Shift.
- (Nov 22) Dropped Noir ZK staffing circuit; building plain-code spatial-temporal + license checks on top of Saswata's Base Sepolia tap anchoring.

## TODO sections (for teammates to drop asks here)

(empty — add your TODO sections at the bottom using the format in `contexts/README.md`)