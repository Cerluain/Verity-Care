# apps/dashboard — Investigator Dashboard (UI 2) + Voice pillar + Case File export

**Owner:** Saswata (Dev C)
**Port:** 8000

Single-page HTML + Tailwind + Alpine + vis-network. FastAPI serves the page, four tab-specific
endpoints, and the Voice + case-file plumbing. No framework scaffold; one `index.html`.

## What this service owns

- `apps/dashboard/index.html` — single page, four tabs (SPEND / SHIFT / VOICE / CASE FILE)
- `apps/dashboard/main.py` — FastAPI proxies to phantom-spend, phantom-shift, voice, onchain
- VOICE pillar — 11Labs conversational agent embedded in VOICE tab
- CASE FILE pillar — aggregator, calls `apps/onchain /sign` for ed25519, calls `/commit` for chain
- Exported PDF via `window.print()` on a styled page
- Pitch narration + 3-slide deck

## Tabs

| Tab        | Data source                                      | Component owner |
|------------|--------------------------------------------------|-----------------|
| SPEND      | GET phantom-spend:8003 /spend/{facility_id}      | Abhi renders via Dev C's shell |
| SHIFT      | GET phantom-shift:8002 /shift/{facility_id} + WS | Leo renders via Dev C's shell  |
| VOICE      | Dev C's internal /voice/{facility_id}            | Dev C                          |
| CASE FILE  | aggregator over all three + chain commits + sig  | Dev C                          |

## Chain + signature integration

Every "Call Mary" → when the call ends, Dev C commits `CLAIM_VOICE` with hash of (resident_id |
call_id | transcript_hash).

Every "Generate MFCU referral packet" → Dev C:
1. Aggregates signals from SPEND/SHIFT/VOICE endpoints.
2. Computes SHA-256 over canonical envelope JSON (keys sorted, `signature`+`sha256` excluded).
3. POST apps/onchain /sign → signature_b64.
4. POST apps/onchain /commit CLAIM_CASEFILE with the SHA-256 hash.
5. Embeds signature + pubkey + tx_hash + explorer URL into the PDF footer.
6. `window.print()` to download.

## Facility Intake (UI 1)

A sibling page `apps/dashboard/facility.html` with three widget slots:
- Cost-Report Upload (Abhi drops widget here)
- Live NFC Tap Feed (Leo drops widget here)
- Resident Enrollment (Dev C)
