# apps/phantom-shift — Staffing fraud detection + live NFC

**Owner:** Leo (Dev B)
**Port:** 8002

Produces SHIFT signal cards for each facility. Hosts the live NFC tap endpoint.

## What this service owns

1. Static data under `/data/shift/` — PBJ-derived shifts, nurse roster with AZ-RN license
   numbers, synthetic AZ Board of Nursing suspension registry, door geometry for one facility.
2. Three scoring functions (cross-facility license collision, credential validity, impossible-travel).
3. Endpoint `GET /shift/{facility_id}` returning SignalCard JSON per
   `packages/schemas/signal-card.schema.json`.
4. Endpoint `POST /live-tap` receiving tap events from NFC phones.
5. WebSocket `/live-tap/stream` broadcasting taps to the dashboard + facility-intake page.
6. One widget on the facility-intake page (live NFC tap feed).

## Chain integration

Every incoming `/live-tap` **must** also commit its hash on-chain before replying:

```python
from onchain_client import commit, CLAIM_TAP
import hashlib

preimage = f"{tap.nurse_license}|{tap.door_id}|{tap.ts}|{nonce}".encode()
claim_hash = "0x" + hashlib.sha256(preimage).hexdigest()
tx = commit(CLAIM_TAP, claim_hash)
# attach tx["tx_hash"] + tx["explorer_url"] to the response + WS broadcast
```

The dashboard renders each tap with a Basescan/Solana Explorer link in the SHIFT tab and
facility-intake widget. This is the pitch's live chain-anchoring moment.

## What this service does NOT own

- The dashboard shell, tab routing, case file (Dev C).
- The live force-graph component (Dev C's dashboard renders from the JSON Leo returns).
- Any chain wallet. `apps/onchain` holds the hot wallet; Leo calls over HTTP.

## NFC phone setup

- 2x phones (iPhone Shortcuts automation or Android HCE app).
- 5x NTAG215 stickers labeled: Entrance, Med Room, Wing C Door, Supply Closet, Memory Care.
- Each tag's URL is `http://<laptop-ip>:8002/live-tap?door=<id>&nurse=<id>`.
- iPhone Shortcuts: NFC trigger → Get URL → return.
- If no stickers available, Android HCE fallback: two Androids broadcast the same payload at
  two "doors" set by UI buttons on the phone.

Rehearse the three scenarios in-place before H5:
1. Legitimate walk (all green).
2. Impossible travel (two taps far apart, <5s delta).
3. Cross-facility collision (two phones as same nurse at two facilities).
