# Abi — context

Role: **Dev A — Phantom Spend** (procurement fraud pillar), **backend-only**. (Saswata's files spell it "Abhi". Same person.)

> **For Saswata / Leo (and your agents):** I've read `contexts/answers-to-abi.md` and I'm building to it. SPEND is a FastAPI service in `apps/phantom-spend/` on port 8003, exposing `GET /spend/{facility_id}` → `{ signals: SignalCard[] }` per `packages/schemas/signal-card.schema.json`, keyed off the locked `data/facilities.json` ids. **Dev C draws the ownership graph** from `evidence.ownership_graph`; I don't write any UI. **I won't change shared schemas or `facilities.json`.**
>
> **Saswata, please read "Replies to answers-to-abi.md" below.** One change affects your dashboard roll-up (the `spend_overall` card).

---

## Status — SPEND P0 backend is DONE (Nov 22, evening)

**`GET :8003/spend/{facility_id}` is live, with 17 tests passing.** Saswata: you can build the SPEND tab now. Run instructions and the full response contract are in `apps/phantom-spend/README.md`. Can't run it? `apps/phantom-spend/samples/<facility_id>.json` are the exact responses.

| Facility | price | ownership | volume | **spend_overall** |
|---|---|---|---|---|
| `buffalo-center-centers-health` | 🔴 insulin 4.2× NADAC | 🔴 shares owner Centers Health Care | 🔴 insulin 2.9× | 🔴 |
| `accordius-rose-manor-portopiccolo` | 🔴 quetiapine 4.5× | 🔴 shares owner Portopiccolo | 🔴 quetiapine 2.4× | 🔴 |
| `mi-casa-life-care-az` | 🟡 Januvia 1.6× | 🟢 | 🟢 | 🟡 |
| `crook-county-wy-rural` | 🔴 insulin 3.2× (rural) | 🟢 | 🟢 | 🟡 ← rural check works |
| `terraces-phoenix-humangood` | 🟢 | 🟢 | 🟢 | 🟢 |
| `haven-health-green-valley` | 🟢 | 🟢 | 🟢 | 🟢 |

### Progress log
- **Real prices pulled:** 20 nursing-home drugs from **CMS NADAC 2026** (data.medicaid.gov API, effective 2026-11-18) → `data/spend/prices.json`. Unit-normalised (insulin per 10 mL vial, enoxaparin per 0.4 mL syringe). **Changed from plan: no CMS ASP**, which covers Part B injectables only; NADAC covers all 20 drugs. Example: insulin lispro $24.03/vial, Eliquis 5 mg $5.52/tablet.
- **Demo data generated** by `scripts/build_demo_data.py` from per-facility settings, so numbers stay consistent: `line-items.json` (6 × 12 invoices, Q3 2026), `ownership-graphs.json` (real parents from facility citations, fictional vendor names flagged `illustrative: true`), `census.json` (placeholder resident-days + usage assumptions).
- **Scoring** (`scoring.py`): 3 signals + `spend_overall`, thresholds as below.
- **Cards + API** (`cards.py`, `main.py`): 4 schema-valid cards per facility; `GET /health`, `GET /spend`, `GET /spend/{id}`.
- **Tests** (`test_scoring.py`): expected colours for all 6, every card validated against `packages/schemas/signal-card.schema.json`, graph drawable, 12 table rows, 404 on unknown id.
- **Tested locally by Abi** via curl: output matches the table above.

### Round 2 (Nov 22, late): dashboard + guardian + pitch — agreed with Saswata
Direction is now in `AGENTS.md` and the top of `contexts/01-project-brief.md`. What I built:

- **Colour bug fixed** in `apps/dashboard/index.html`: SPEND's contribution to the facility colour now comes from the `spend_overall` card. `crook-county-wy-rural` shows **YELLOW**. (Saswata: this was your roll-up code, edited with your OK via Abi.)
- **Spending tab** (renamed from SPEND): verdict banner, the 4 cards (your chain buttons untouched), **ownership graph** (vis-network, owners on top, related-party path in red, hover tooltips; `static/spend-extras.js`) and the **invoice table** (12 rows, paid vs fair price, markup + qty-vs-need badges, "same owner" tags).
- **Tabs now:** Spending · Staffing · Guardian reports · Voice · Case file.
- **Staffing tab:** shows **MOCK PBJ** (hours per resident per day by role) and any `/shift` signals once Leo's service is up.
- **Mock PBJ for all 6 facilities**: `data/spend/pbj-mock.json`, served at `GET :8003/pbj/{id}` and proxied by the dashboard at `/pbj/{id}`. `census.json` resident-days come from it. **Leo: drop real numbers into that file (same shape) and re-run `scripts/build_demo_data.py`.**
- **Pitch page `/pitch`**: 6 full-screen slides from `04-spend-evidence.md` (every number cited), space/↓ to advance, "Open the product →". Linked from a **▶ Pitch** button in the top corner of every view.
- **Guardian view `/guardian`**: synthetic resident Rosa D. at Mi Casa, live timeline (polls every 3 s) of meds, meals, therapy, activities, vitals. Each item shows who verified it, the photo, its fingerprint and the tx. "This didn't happen" sends a dispute.
- **Staff check-in `/staff`** (phone): pick a task → phone camera → photo SHA-256 + metadata hashed → `/commit` claim type 1 (facility signer). Photo stays off-chain in `data/care/runtime/` (gitignored). Works over plain http on venue WiFi (uses the native camera input, not getUserMedia).
- **Guardian reports tab**: family disputes + billed therapy with no check-in, per facility.
- **Backend:** `apps/dashboard/care.py` (router in `main.py`) + seed `data/care/residents.json`. `CARE_DEMO_TIME` (default `12:30`) fixes "now" so the demo looks like lunchtime even at 11 PM. `POST /care/reset` clears live check-ins before a run.
- **Tested end to end** with the onchain service in mock mode: check-in → mock tx (facility signer) → guardian flips to verified → dispute → appears in Guardian reports. 18 SPEND tests pass.

### Round 3 (Nov 22, night): guardian + staff on SQLite, Proof-of-Service wiring, new pitch
- **SQLite** (`apps/dashboard/care_db.py`, file `data/care/runtime/care.db`, gitignored, auto-seeded): 5 synthetic residents at Mi Casa (Rosa, Walter, Mae, Harold, Gloria), guardians, 6 staff (RN-1187, LPN-0412, CNA-2231, CNA-2240, PT-0907, OT-0310), assignments, per-resident care plans, history. `POST /care/reset` re-seeds. Replaces `data/care/residents.json`.
- **Staff check-in now uses Saswata's Proof-of-Service pipeline**: `care.py` forwards the photo to onchain `POST /delivery` (IPFS + staff wallet, claim type 5) and stores tx/CIDs against the care-plan item. Fallback: `/commit` claim type 1, then "recorded, not anchored". ⚠️ IPFS is public, so for real use photos must be encrypted before pinning. Demo: props/teammates only.
- **Staff app** `/staff`: sign in with staff ID → your assigned residents (due counts) → your role's tasks for that resident (allergy banner) → photo → confirm. Wrong staff for a resident → 403.
- **Guardian** `/guardian`: full width, 3 columns. "{Name}'s full history" dropdown (stay length, meds, allergies, diet, doctor, care team, therapy billed vs verified, history timeline). Day filter (last 7 days; before go-live = "No records before Verity Care go-live"). ⏳ anchoring → ✓ on-chain status. "verify proof" re-fetches IPFS metadata and recomputes the hash in the browser (Saswata's TODO 2).
- **Dispute routing** (agreed): facility always → State Long-Term Care Ombudsman (medication = safety, immediately; others if not fixed in 24 h) → state investigator **only if billed or 2+ disputes in 7 days**. Guardian sees the route; investigator "Guardian reports" shows only referred ones.
- **Navigation**: floating icon panel bottom-left on every page (🕵️ 👪 🩺 ▶), a slim bar on phones. Top bars removed.
- **Pitch** `/pitch`: one scrolling page; a single diagram on the right builds as you scroll (Medicaid → home → supplier → same owner → profit loop → cost report → rate ↑ → real case → investigator → Verity's 3 checks → family), all numbers cited.
- **Not merged yet:** Saswata's `8a0711d` (Proof-of-Service backend) touches `index.html`, dashboard `main.py`, this file and the brief. To be merged at commit time. His Voice → "proof of service" tab rename wins.

### What's next
- [x] ~~Saswata: build the SPEND tab; use `spend_overall` for the roll-up~~ → done by Abi
- [x] ~~Server-side anchoring of SPEND cards~~ → **not doing it**: the dashboard's "Commit on-chain" button is enough (avoids double receipts). Saswata's TODO 1/2 below are closed by this decision.
- [ ] Saswata: confirm claim type 1 (facility signer) is right for care check-ins, or add a dedicated type
- [ ] Leo: real PBJ → `data/spend/pbj-mock.json`
- [ ] Together: wording pass on the Spending tab ("rephrasing")
- [ ] Rehearse the demo arc (in `01-project-brief.md`) on the real venue WiFi with a phone on `/staff`
- [ ] Optional: Cost Plus Drugs prices; "3 hops" → "shares an owner"

---

## Replies to `answers-to-abi.md` (decisions — Nov 22)

### 1. Real facility names with authored SPEND evidence: DEFERRED
I'm going with the 6 real facilities as locked. Invoices, markups and volumes on SPEND are authored by us. Concern noted (it shows invented numbers under real names), but we've decided to defer it for the demo. Revisit only if time allows (fallback: "modelled on …" fictional names for the 2 SPEND-red facilities).

### 2. Dashboard roll-up: SPEND returns a pillar-level `spend_overall` card — ACTION FOR SASWATA
The rule "red if any pillar has a red signal" turns `crook-county-wy-rural` red, because its price signal is red, and that breaks the rural false-positive check. Fix:

- `/spend/{facility_id}` returns **one extra card** with `signal_type: "spend_overall"`:
  - **red** = all 3 SPEND signals red
  - **yellow** = at least one SPEND signal red or yellow, but not all 3 red
  - **green** = all 3 green
- **Dashboard roll-up: use the `spend_overall` card as SPEND's contribution** and ignore the three individual SPEND signal severities when computing the left-rail facility colour. Individual cards still render in the SPEND tab.
- `crook-county-wy-rural` → `spend_overall: yellow` → stays yellow as long as SHIFT/VOICE have no reds for it.

### 3. `data_provenance`: `demo_grounded` for price-gap and volume cards
Only the *reference* side is real (CMS ASP/NADAC prices, PBJ resident-days). The *facility* side (invoice prices, units bought) is authored. So:

| Card | `data_provenance` | `citation` |
|---|---|---|
| `ref_price_delta` | `demo_grounded` | CMS ASP / NADAC file URL |
| `ownership_overlap` | `demo_grounded` | the facility's `citation` from `facilities.json` (NY AG / ProPublica / CMS) |
| `volume_sanity` | `demo_grounded` | PBJ dataset URL |
| `spend_overall` | `demo_grounded` | — |

`real` is reserved for cards built **entirely** from public data (none on SPEND at P0).

---

## How I'm building SPEND

### Architecture
- **FastAPI service**, `apps/phantom-spend/`, port **8003**. Backend only.
- **Static data, no live fetching at demo time.** Signals are computed on each request from JSON in `data/spend/`, so it's fast and survives bad WiFi.
- **One-off Python script** pulls real CMS NADAC prices into `data/spend/prices.json` (ASP dropped; see progress log).
- **No chain anchoring at P0.** P1 option: `packages/onchain-client` → `commit(CLAIM_SIGNAL_CARD, hash)` per `HANDOFF.md`.
- **Framing:** rows are **supplier → facility invoices that feed the cost report** (CMS Form 2540, Worksheet A-8-1), not Medicaid claim lines. Part A has no drug line items (see `02-fraud-research-brief.md`).

### Files
```
apps/phantom-spend/
  main.py                 ← FastAPI: GET /health, GET /spend, GET /spend/{facility_id}; CORS open
  scoring.py              ← ref_price_delta, ownership_overlap, volume_sanity, spend_overall
  cards.py                ← builds schema-valid SignalCards
  test_scoring.py         ← expected colour per facility + schema validation
  requirements.txt
  scripts/pull_prices.py  ← one-time: CMS NADAC → data/spend/prices.json
  scripts/build_demo_data.py ← generates line-items / ownership-graphs / census from per-facility settings
  samples/<id>.json       ← saved responses for the dashboard
data/spend/
  prices.json             ← 20 drugs: NADAC (real, source URL + effective date)
  line-items.json         ← 6 facilities × 12 invoice rows (authored)
  ownership-graphs.json   ← 6 graphs: nodes + edges + notes (authored, grounded in facility citations)
  census.json             ← resident-days per facility (placeholder → Leo's PBJ numbers)
```
`data/facilities.json` and `packages/schemas/` are read-only for me.

### Response shape — `GET /spend/{facility_id}`
```json
{
  "signals": [
    {
      "signal_id": "spend-ref_price_delta-buffalo-center-centers-health-L003",
      "pillar": "spend",
      "signal_type": "ref_price_delta",
      "facility_id": "buffalo-center-centers-health",
      "severity": "red",
      "headline": "Eliquis 5mg invoiced at 4.1× CMS ASP",
      "detail": "...",
      "data_provenance": "demo_grounded",
      "evidence": { "line_id": "L003", "ndc": "...", "unit_price": 0, "asp": 0, "nadac": 0,
                    "ratio": 4.1, "supplier": "...", "line_items": [ ] },
      "citation": { "source": "CMS ASP pricing file", "url": "https://www.cms.gov/..." },
      "computed_at": "2026-11-22T20:00:00Z"
    },
    { "signal_type": "ownership_overlap",
      "evidence": { "hops": 2, "shared_node": "...", "path": [ ],
                    "ownership_graph": { "nodes": [ ], "edges": [ ], "notes": "..." } } },
    { "signal_type": "volume_sanity",
      "evidence": { "drug": "...", "billed_units": 0, "expected_max": 0, "ratio": 2.9,
                    "resident_days": 0, "assumptions": { } } },
    { "signal_type": "spend_overall", "severity": "red",
      "evidence": { "ref_price_delta": "red", "ownership_overlap": "red", "volume_sanity": "red" } }
  ]
}
```
- Exactly one card each for `ref_price_delta` (the worst line; all 12 rows in `evidence.line_items` for the table), `ownership_overlap`, `volume_sanity` and `spend_overall`.
- Graph nodes/edges are vis-network-ready: `{ id, label, type, details }`, `{ from, to, label, related_party }`.
- Unknown facility id → 404.

### Scoring rules (thresholds from `apps/phantom-spend/README.md`)
| Signal | Red | Yellow | Green |
|---|---|---|---|
| `ref_price_delta` | worst unit price > 3× NADAC | 1.5–3× | < 1.5× |
| `ownership_overlap` | supplier shares an ancestor with the facility within 3 hops | shared registered agent / address only | no overlap |
| `volume_sanity` | billed > 1.5× expected max | 1.2–1.5× | ≤ 1.2× |
| `spend_overall` | all 3 red | some red/yellow, not all 3 red | all green |

### The 6 facilities (locked `data/facilities.json`)
| id | Beds | SPEND story | Expected `spend_overall` |
|---|---|---|---|
| `buffalo-center-centers-health` (NY) | 200 | **Hero.** Owner-controlled vendor LLCs under Centers Health Care (per NY AG complaint); ~3 big markups; ~2.9× volume | 🔴 red |
| `accordius-rose-manor-portopiccolo` (NC) | 111 | Captive pharmacy vendor under Portopiccolo; high pharmacy markups + over-volume | 🔴 red |
| `mi-casa-life-care-az` (AZ) | 180 | Boring. Maybe one modest markup, no ownership overlap. (Red comes from VOICE/SHIFT) | 🟡 or 🟢 |
| `crook-county-wy-rural` (WY) | 32 | +180% markups on 2 items (thin frontier market), county-district owner, normal volume | 🟡 yellow |
| `terraces-phoenix-humangood` (AZ) | 64 | Near-reference prices, unrelated suppliers | 🟢 green |
| `haven-health-green-valley` (AZ) | 111 | Same | 🟢 green |

**Volume maths** (realistic; fixes `03-demo-plan.md`): resident-days ≈ beds × ~90% occupancy × 91 days. E.g. Buffalo: 200 beds → ~180 residents → ~16,400 resident-days/quarter → ~36 insulin users × ~4.5 vials → expected max ~160 vials; billed ~470 → **2.9×**. Assumptions are returned in `evidence.assumptions`; swapped for Leo's PBJ numbers when available.

---

## Build plan

| # | Step | Work | Done when |
|---|---|---|---|
| 1 | Service skeleton | `main.py` with `/health` + stub `/spend/{id}`, `requirements.txt`, CORS | `curl :8003/health` ok |
| 2 | Real prices | `pull_prices.py`: CMS ASP + NADAC for ~20 drugs, unit-normalised; Abi hand-pulls ~10 Cost Plus prices | `data/spend/prices.json` with sources |
| 3 | Census | `census.json` from bed counts (placeholder) | 6 rows |
| 4 | Ownership graphs | `ownership-graphs.json` for 6 facilities, grounded in each facility's citation | Buffalo + Accordius show related-party path |
| 5 | Line items | `line-items.json`, 6 × 12 rows matching the stories above | Reviewed by Abi |
| 6 | Scoring | `scoring.py`: 3 signals + `spend_overall` | Unit tests pass |
| 7 | Cards + API | `cards.py` + wire `/spend/{id}`; validate every card against the schema | All 6 return schema-valid cards with the expected colours |
| 8 | Hand-off | Tell Saswata the endpoint is live; sample responses committed | Dashboard renders SPEND |
| 9 | PBJ swap | Replace placeholder census with Leo's numbers; re-check colours | Tests still pass |
| 10 | P1 | Signal-card chain anchoring; intake CSV-upload endpoint | — |
| 11 | Rehearse | Q&A prep, dry run | — |

**Cut order if behind:** ZK stretch → chain anchoring → intake upload → Cost Plus column.

---

## Task checklist (mirrors Dev A in `saswata.md`, UI tasks moved to Dev C)

### P0 — Must ship
- [x] 1. ~~CMS ASP~~ → replaced by NADAC (ASP covers Part B injectables only)
- [x] 2. NADAC for 20 drugs → `data/spend/prices.json`
- [ ] 3. Hand-pull 10 Cost Plus Drugs prices (optional now)
- [x] 4. Author line items: 6 facilities × 12 rows
- [x] 5. Author ownership graphs for 6 facilities
- [x] 6. Scoring: reference-price delta
- [x] 7. Scoring: ownership overlap
- [x] 8. Scoring: volume-vs-census
- [x] 12. Rural case: `crook-county-wy-rural` → `spend_overall` yellow
- [x] (new) `spend_overall` card + `GET /spend/{id}` returning schema-valid cards
- ~~9–11. SPEND tab table, signal cards, vis-network graph~~ → **Dev C** (per `answers-to-abi.md`). I supply the data in `evidence`.

### P1 — Should ship
- [ ] 13. Cost-report CSV upload (backend endpoint; Dev C hosts the widget)
- [x] 14. Citation on every card (built into the card builder)
- [ ] Anchor signal-card hashes via `packages/onchain-client`

### P2 — Stretch (cut first)
- [ ] 16. ZK invoice-integrity proof in Noir

---

## Other dependencies
| From | What | Needed by | If late |
|---|---|---|---|
| Saswata | Dashboard roll-up uses `spend_overall` (decision 2 above) | Before dry run | Rural tile turns red |
| Leo | Real PBJ resident-days per facility (Dev B #1) | Before dry run | Labelled placeholder in `data/spend/census.json` |
| Saswata | Onchain service (mock mode is fine) | P1 only | Skip anchoring |

## Q&A I own
Procurement fraud, reference prices, PE nursing-home chains, PECOS / ownership opacity, "why not just NADAC."
- **"Rural homes pay more?"** → `crook-county-wy-rural`: price-only red stays yellow.
- **"Invoices aren't public?"** → Public cost reports flag which homes to examine → MFCU subpoenas invoices → tool fuses the signals.
- **Legal hook:** 42 CFR 413.17 ("prudent buyer" / related-party cost rule) lets CMS disallow related-party markups.

## What I do NOT own
- All UI, including the SPEND tab and ownership-graph rendering (Dev C).
- Dashboard shell, shared schemas, `data/facilities.json`, onchain service, Voice, Case File (Saswata / Dev C).
- SHIFT pillar (Leo / Dev B).

## Open questions
- **Headline stats** for the pitch need sources: "$12B/yr" (is it really NBER w28474?) and "~$90B Medicaid to nursing homes."
- **ASP units:** ASP is per HCPCS billing unit, not per vial. Normalising and recording the conversion.
- **Team docs drift:** `AGENTS.md` / `01-project-brief.md` still say "no chain, staffing out", which contradicts `HANDOFF.md` + `saswata.md`.

## Decisions I've made
- (Nov 22) Taking Dev A — Phantom Spend.
- (Nov 22, updated) Building to the locked scaffold: FastAPI `apps/phantom-spend` on :8003, data in `data/spend/`.
- (Nov 22, updated) Backend-only. Dev C renders the SPEND tab + graph from my card `evidence`.
- (Nov 22) SPEND returns a `spend_overall` card; the dashboard should roll up from it.
- (Nov 22) Price-gap, volume, ownership and overall cards are `data_provenance: "demo_grounded"`.
- (Nov 22) Real-facility-names concern deferred for the demo.
- (Nov 22) Rural safety case is `crook-county-wy-rural` (WY).
- (Nov 22) Reference price = CMS NADAC only (dropped ASP).
- (Nov 22) Demo data is generated from settings in `scripts/build_demo_data.py`, not hand-typed; edit the settings and re-run.

## TODO sections (for teammates to drop asks here)

(add your TODO sections at the bottom using the format in `contexts/README.md`)

## TODO from Leo — PBJ data handoff for volume_sanity

### [ ] TODO 1 — Share the 6 facility CCNs and quarterly PBJ resident-day numbers as soon as Task 1 finishes (P0, ~immediate)

The `volume_sanity` scoring function is blocked on the exact shared facility identifiers and resident-day values. Send the finalized six-row dataset in the same shape as `facilities.json` once Leo Task 1 is complete.

## TODO from Saswata — on-chain commitment of your SPEND signal cards (chain infra is live)

### [ ] TODO 1 — Anchor each signal card you compute (P0 for chain demo, ~10 min)

The Base Sepolia contract is deployed and the local onchain service is wired. You call one HTTP endpoint per card; keys live inside Dev C's service, you never touch them.

**Setup (one time):**

```bash
# Dev C runs this; you don't. Just point your service at it.
# apps/onchain on port 8001 holds the three signer private keys.
# Flip your local .env to NOT skip chain if you have one.

# Add the client to your service:
pip install httpx    # already in your deps
```

**In your `apps/phantom-spend/cards.py`**, right before returning each card:

```python
import hashlib, json, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "onchain-client"))
from onchain_client import commit, CLAIM_SIGNAL_CARD

def _anchor(card: dict) -> dict:
    """Attach a chain_commit block to a signal card. Idempotent; returns the card."""
    if card.get("chain_commit"):
        return card
    canon = json.dumps({k: v for k, v in card.items() if k != "chain_commit"},
                       sort_keys=True, separators=(",", ":")).encode()
    claim_hash = "0x" + hashlib.sha256(canon).hexdigest()
    try:
        tx = commit(CLAIM_SIGNAL_CARD, claim_hash)
    except Exception as e:
        # Never fail the response because chain is flaky; log and skip.
        print(f"[spend] chain anchor failed, skipping: {e}", file=sys.stderr)
        return card
    card["chain_commit"] = {
        "tx_hash": tx["tx_hash"],
        "explorer_url": tx["explorer_url"],
        "block_number": tx.get("block_number"),
        "committed_at": tx["committed_at"],
        "signer_role": tx["signer_role"],         # "facility" for SIGNAL_CARD
        "signer_address": tx["signer_address"],
        "mocked": tx["mocked"],
    }
    return card
```

Then wrap your four card returns (`ref_price_delta`, `ownership_overlap`, `volume_sanity`, `spend_overall`):

```python
return _anchor(build_ref_price_delta_card(...))
```

**Why `CLAIM_SIGNAL_CARD` (type 4)?** The service routes claim type 4 to the FACILITY signer (`0xB281013450EE41d4634246A927A7663f12153cB3`), semantic: "the facility submitted the data this signal was computed from." On Basescan the judges will see the facility is the on-chain attestor. That matches the architectural story.

**Fallback behaviour:** if `apps/onchain` isn't running, the `commit()` call throws, `_anchor()` logs and returns the card without a `chain_commit` field. Your service still responds 200. Dev C's dashboard just skips the Basescan badge for cards without `chain_commit`.

**Mock mode:** if Dev C has `MOCK=true` in `apps/onchain/.env`, the returned `tx_hash` starts with `0xmock...` and `explorer_url` is null. Your card still carries the commit block with `mocked: true`; the dashboard renders a grey badge. No special casing on your side.

**Verification:** after re-running `make build-data` or regenerating samples, every sample JSON under `apps/phantom-spend/samples/` should have four non-null `chain_commit` blocks per facility (24 total chain commits).

### [ ] TODO 2 — Re-generate your sample JSONs with chain_commit populated (P0, ~2 min after TODO 1)

```bash
cd apps/phantom-spend
# make sure Dev C's onchain service is running at localhost:8001
curl -s http://localhost:8001/health | python3 -m json.tool  # should show 3 signers
python scripts/build_demo_data.py --regenerate-samples
```

Push the updated samples so the dashboard has them for a full-offline demo path.

### Non-goals for you on chain

- Do NOT add a wallet, do NOT touch private keys, do NOT install web3.py. The onchain service handles all of that.
- Do NOT add chain signing for the invoice-upload widget on the facility intake page — that lands on me (Dev C) since I own that page.

## TODO from Saswata — PROOF-OF-SERVICE tab UI (chain + IPFS are live, backend is done)

### Context — what we agreed on with you

Replacing the Voice pillar. Staff member delivers a specific thing to a specific patient (meal tray, insulin dose, PT visit, wound dressing), opens the app, snaps a photo, submits. The backend:

1. Pins the image to IPFS (Pinata), gets `image_cid`
2. Builds a metadata JSON with that `image_cid` + facility/patient/service details
3. Pins the metadata to IPFS, gets `metadata_cid`
4. Computes `sha256(canonical(metadata))` = `claim_hash`
5. Calls `commit(claim_type=5, claim_hash)` signed by the **staff wallet** (`0xdbbF6AF9F46E85ee39c2448bc807A51cfc4d497B`)

Verifier can refetch metadata from any IPFS gateway, recompute the hash, and confirm it matches what's on-chain. Walmart-receipt-photo pattern, done properly with content-addressing.

Note on contract: we redeployed. New VerityCommit lives at `0x7aa14919C7b2d127F755E048682a6f5A1b57Fcdb` (old `0xF806…` is dead). Everything in `shared.env.example` already references the new address.

### [ ] TODO 1 — Build the Proof-of-Service tab UI (P0, backend already works)

The dashboard already has a "proof of service" tab registered (replaces the old "voice" tab). The placeholder is at `apps/dashboard/index.html` inside the `activeTab === 'proof of service'` template.

Everything you need to build is UI. The backend is live:

- **POST /delivery** (multipart form) — upload a photo + record a delivery. Form fields: `facility_id`, `patient_pseudonym`, `service_type`, `service_detail`, `staff_pseudonym`, optional `delivered_at` (ISO), `image` (file). Returns JSON with `tx_hash`, `claim_hash`, `metadata_cid`, `image_cid`, `signer_role: "staff"`, `signer_address`, `explorer_url`, `image_url` (Pinata gateway), `metadata_url`.
- **GET /deliveries?facility_id=…** — list all proofs for a facility (newest first). Same shape as POST response.

Both are proxied by the dashboard at `/delivery` and `/deliveries` — hit those from the browser, no CORS fuss.

Suggested UI for the tab:

1. **Upload widget** at the top: file input + the 4 text fields (patient, service_type, service_detail, staff_pseudonym) + submit button. Service type is a dropdown: `meal | insulin | medication | visit | wound_dressing | pt_session`. On submit, POST multipart to `/delivery`. On success, prepend the returned record to the list below.
2. **Grid of proof cards** below (2-3 per row): each card shows the image (from `image_url`), service type + detail, patient pseudonym, timestamp, staff pseudonym, and a chain footer row with the same state machine the SPEND cards have — pending (yellow) → confirmed (green + block number) → with a Basescan link + "verify" button.
3. **Verify button** fetches `/chain/{tx_hash}` (dashboard already proxies) and shows block number + signer address + source. Same pattern as SPEND verify.
4. **IPFS links** — next to the image, show a small "view on IPFS ↗" link to `image_url`, and "metadata ↗" to `metadata_url`. Click to open Pinata gateway in a new tab.

### [ ] TODO 2 — Verification affordance for the pitch (P0, ~15 min)

For each proof card, add a small "verify hash" button that:

1. Fetches `metadata_url` (the raw JSON from IPFS)
2. Computes `sha256(canonical(metadata))` in the browser using `crypto.subtle.digest` (the same `canonicalHash` helper the SPEND tab uses — see `dashboard()` fn around line 310)
3. Compares to the `claim_hash` returned from `/delivery` and shown on the card
4. Flashes "✓ matches on-chain hash" (green) or "✗ MISMATCH" (red)

**This is the pitch moment.** When a judge asks "how do I know the photo wasn't swapped," you click this button. The browser independently refetches from IPFS, independently recomputes the hash, and the UI proves the match. Nothing trusts our backend — trust is derived from re-execution.

### Non-goals for you on Proof-of-Service

- Do NOT handle the Pinata JWT. If it's missing, the backend falls back to `bafkmock…` deterministic CIDs so the UI builds without an account. Judges will see `pin_mode: "mock"` in the response — fine for now.
- Do NOT handle image compression or resizing. Pinata takes anything up to a few MB; our 1x1-pixel smoke-test shows the pipeline works on anything.
- Do NOT touch the staff wallet or any private key — all signing is in `apps/onchain`.

### Smoke-test it worked (run before styling)

```bash
# 1. Make sure the onchain service is running on 8001 and the dashboard on 8000
curl -s http://localhost:8001/health | python3 -m json.tool  # should show 4 signers incl. "staff"

# 2. Upload a test image via curl
curl -X POST http://localhost:8000/delivery \
  -F "facility_id=buffalo-center-centers-health" \
  -F "patient_pseudonym=patient-A17" \
  -F "service_type=insulin" \
  -F "service_detail=humalog 10u" \
  -F "staff_pseudonym=staff-003" \
  -F "image=@/path/to/any/photo.png" | python3 -m json.tool

# 3. List deliveries for that facility
curl -s "http://localhost:8000/deliveries?facility_id=buffalo-center-centers-health" | python3 -m json.tool
```

If #1 and #2 both return 200 with a `tx_hash` + `metadata_cid`, backend is good. The pitch-ready story: `tx_hash` → Basescan proves staff wallet signed it at a specific block time; `metadata_cid` → IPFS gateway proves you can refetch and rehash; the two tie together because the on-chain `claim_hash` equals `sha256(canonical(metadata))`.

### What Saswata already shipped on this

- VerityCommit redeployed with claim_type range extended to 1..5 at `0x7aa14919C7b2d127F755E048682a6f5A1b57Fcdb`
- Staff signer wallet funded (0.001 ETH)
- `apps/onchain /delivery` + `/deliveries` endpoints live, smoke-tested with a 1×1 PNG: real tx on Base Sepolia block 62402565, hash round-trip verified byte-for-byte
- Dashboard `/delivery` + `/deliveries` proxies live so browser hits one origin
- Proof-of-service tab replaces Voice in the dashboard tab list + placeholder note points to these endpoints
