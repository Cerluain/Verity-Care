# apps/onchain — Verity Care cryptographic trust service

**Owner:** Dev C (Saswata)
**Port:** 8001

Single service that holds the two private keys for Verity Care:
1. The hot wallet signing all on-chain commits.
2. The ed25519 key signing every exported case file.

Other services (phantom-shift, phantom-spend, dashboard) never touch keys directly —
they POST to this service's HTTP endpoints.

## Why a separate service, not a library

- **Private-key isolation.** Keys live in ONE process's env.
- **Nonce management.** A single signer avoids tx-nonce races when Leo's tap commits
  and Dev C's voice commits fire simultaneously.
- **Chain failures don't kill the dashboard.** If the RPC flakes mid-demo, this service
  returns a cached mock tx_hash and queues retry. UI keeps going.
- **Mock mode.** Set `MOCK=true` in `.env` and this service returns deterministic fake
  tx hashes so Abhi + Leo can build without a funded wallet.
- **Chain portability.** Swap base_sepolia → arbitrum_sepolia or anything else by
  changing this service's env; nothing else in the repo changes.

## Endpoints

### POST /commit
Anchor a claim hash on-chain.
```
Request:  { "claim_type": 1|2|3|4, "claim_hash": "0x...32 bytes hex..." }
Response: {
  "tx_hash": "0x...",
  "explorer_url": "https://sepolia.basescan.org/tx/0x...",
  "block_number": 12345678,
  "claim_type": 1,
  "claim_type_label": "tap",
  "committed_at": "2026-11-22T22:30:00Z",
  "mocked": false
}
```

### GET /commit/{tx_hash}
Check confirmation status of a prior commit.

### GET /commits?facility_id=&claim_type=
List commits (reads local append-only log). Used by the case-file aggregator.

### POST /sign
Sign arbitrary content with the Verity Care ed25519 key.
```
Request:  { "content_b64": "..." }
Response: { "signature_b64": "...", "pubkey_b64": "...", "algo": "ed25519" }
```

### GET /verify-key
Return the public verify key.

## Running locally

```bash
cd apps/onchain
cp .env.example .env
# Fill VERITY_COMMIT_PRIVATE_KEY (hot wallet funded from faucet) and
#      ED25519_SIGNING_KEY_B64 (generated at H1, see parent README)

uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

## Mock mode (teammates without wallet keys)

```bash
MOCK=true uvicorn main:app --port 8001 --reload
```

In mock mode, /commit returns deterministic `0xmock...` hashes with explorer_url=null.
Everything else in the system treats them as normal — no special casing required.
