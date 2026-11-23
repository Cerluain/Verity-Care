# Verity Care — Scaffold Handoff (Dev C → Dev A + Dev B)

Signatures are locked. Pull, read, start building. This file explains everything you need
to integrate without talking to Dev C.

## What's in the repo now

```
contracts/                           # one Solidity contract (deploys at H1)
  src/VerityCommit.sol
  script/Deploy.s.sol
  foundry.toml
  README.md

apps/
  onchain/        (Dev C, port 8001) # cryptographic trust service — wallet + ed25519
    main.py
    requirements.txt
    README.md
    .env.example
  dashboard/      (Dev C, port 8000) # UI 2 + VOICE + CASE FILE
    README.md
    .env.example
  phantom-spend/  (Abhi, port 8003)  # SPEND signals
    README.md
  phantom-shift/  (Leo, port 8002)   # SHIFT signals + /live-tap
    README.md

packages/
  schemas/                           # shared JSON schemas — DO NOT CHANGE without coord
    signal-card.schema.json
    case-file.schema.json
    facility.schema.json
  onchain-client/                    # thin HTTP wrapper — import this to anchor hashes
    onchain_client.py                #   Python (Leo + Abhi)
    index.ts                         #   TypeScript (if anyone's in Node)
    README.md

data/
  facilities.json                    # LOCKED. 6 facilities everyone keys off.

shared.env.example                   # non-secret service URLs + deployed addresses
.gitignore
AGENTS.md
contexts/                            # project brief + research + per-dev task lists
```

## Chain decision

Pending. Dev C is researching faucet UX right now. Will update `shared.env.example`
+ this file as soon as deployed address exists.

Until then, **run onchain service in MOCK mode**:
```bash
cd apps/onchain
cp .env.example .env
# leave VERITY_COMMIT_PRIVATE_KEY, CHAIN_RPC_URL empty; set MOCK=true
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

All downstream integration work (Leo's /live-tap, Abhi's optional signal-card commit) works
fine against mock — the response shape is identical, tx hashes are prefixed `0xmock...`.

## For Leo (Dev B): how to anchor every NFC tap

```python
# apps/phantom-shift/live_tap.py
import hashlib
from onchain_client import commit, CLAIM_TAP     # from packages/onchain-client/

async def on_tap(nurse_license: str, door_id: str, ts: float, nonce: str) -> dict:
    preimage = f"{nurse_license}|{door_id}|{ts}|{nonce}".encode()
    claim_hash = "0x" + hashlib.sha256(preimage).hexdigest()
    tx = commit(CLAIM_TAP, claim_hash)
    return {
        "nurse_license_hashed": claim_hash[:18],   # for UI, don't leak full license in frontend
        "door_id": door_id,
        "ts": ts,
        "tx_hash": tx["tx_hash"],
        "explorer_url": tx["explorer_url"],
        "mocked": tx["mocked"],
    }
```

## For Abhi (Dev A): how to (optionally, P1) anchor signal cards

```python
# apps/phantom-spend/api.py
import hashlib, json
from onchain_client import commit, CLAIM_SIGNAL_CARD

def anchor_signal_card(card: dict) -> dict:
    canon = json.dumps(card, sort_keys=True, separators=(",", ":")).encode()
    claim_hash = "0x" + hashlib.sha256(canon).hexdigest()
    tx = commit(CLAIM_SIGNAL_CARD, claim_hash)
    card["chain_commit"] = {
        "tx_hash": tx["tx_hash"],
        "explorer_url": tx["explorer_url"],
        "committed_at": tx["committed_at"],
    }
    return card
```

## Signatures everyone must respect

### SignalCard (packages/schemas/signal-card.schema.json)

Required fields:
- `signal_id` (string, unique within case)
- `pillar` (enum: spend | shift | voice)
- `signal_type` (string)
- `severity` (enum: red | yellow | green)
- `headline` (string, <120 chars)
- `computed_at` (ISO 8601 UTC)

Optional but recommended:
- `facility_id`, `detail`, `evidence`, `citation`, `chain_commit`

### Facility (data/facilities.json)

LOCKED. Six facilities with scenarios already assigned. Everyone keys off `id`.

### Endpoints every pillar service MUST expose

- `GET /spend/{facility_id}` → `{ signals: SignalCard[] }` (Abhi)
- `GET /shift/{facility_id}` → `{ signals: SignalCard[] }` (Leo)
- `POST /live-tap` → `{ tx_hash, explorer_url, ... }` (Leo)

Dashboard consumes these.

## Secrets rule

Every new API key gets a `.env.example` entry in the same commit. Never commit a real key.

## Unblocking order

If Dev C hasn't deployed the chain yet (he's researching faucets), run everything in
mock mode and keep building. Nothing is actually blocked — mock mode returns valid
response shapes. When the real contract is deployed, Dev C will update `shared.env.example`
+ announce in the team chat and you re-point your `.env` to `MOCK=false`.
