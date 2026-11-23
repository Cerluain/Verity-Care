# apps/dashboard — Investigator Dashboard (UI 2) + chain proxy

**Owner:** Saswata (Dev C) · **Port:** 8000

Single-page HTML + Tailwind + Alpine. Zero build step. FastAPI serves the page +
four proxy endpoints that bridge the browser to the pillar + chain services.

## Run

```bash
cd apps/dashboard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8000 --reload
# open http://localhost:8000
```

Upstreams expected (fallbacks everywhere, so partial-up is fine):

| Service        | Port | Fallback                                               |
|----------------|------|--------------------------------------------------------|
| `apps/onchain` | 8001 | shows "on-chain: offline" dot; commit buttons disabled |
| `apps/phantom-spend` | 8003 | falls back to `apps/phantom-spend/samples/*.json` |
| `apps/phantom-shift` | 8002 | returns empty signals (SHIFT tab shows placeholder)  |

## Endpoints the dashboard exposes

| Method | Path                        | Does                                              |
|--------|-----------------------------|---------------------------------------------------|
| GET    | `/`                         | serves `index.html`                               |
| GET    | `/facilities`               | reads `data/facilities.json`                      |
| GET    | `/spend/{facility_id}`      | proxies to phantom-spend, falls back to samples   |
| GET    | `/shift/{facility_id}`      | proxies to phantom-shift                          |
| POST   | `/chain/commit`             | proxies to onchain `/commit`                      |
| GET    | `/chain/{tx_hash}`          | proxies to onchain `/commit/{tx_hash}`            |
| GET    | `/chain/verify/by-hash`     | proxies to onchain `/verify?claim_hash=…`         |
| GET    | `/chain/health`             | proxies to onchain `/health`                      |

## Reusable on-chain pattern (any teammate can lift this)

Every UI event (SPEND card commit, SHIFT tap commit, VOICE attestation commit,
CASEFILE export) follows the same three-step shape:

```js
// 1. Compute a canonical hash (sorted JSON → SHA-256)
const claim_hash = await canonicalHash(payload);

// 2. Push on-chain via the proxy
const tx = await fetch('/chain/commit', {
  method: 'POST',
  headers: {'content-type':'application/json'},
  body: JSON.stringify({ claim_type: 4, claim_hash }),
}).then(r => r.json());

// 3. Later, pull for verification
const proof = await fetch('/chain/' + tx.tx_hash).then(r => r.json());
// proof = { verified, block_number, signer_role, signer_address, source, ... }
```

Python side (phantom-spend, phantom-shift) use `packages/onchain-client`:

```python
from onchain_client import commit, get_commit, verify_claim, CLAIM_SIGNAL_CARD
tx = commit(CLAIM_SIGNAL_CARD, "0x" + sha256_hex)
proof = get_commit(tx["tx_hash"])
# or search by claim hash:
hits = verify_claim("0x" + sha256_hex, claim_type=4)
```

Same primitives, same semantic three claim-type signers (facility / ombudsman /
verity_service). Teammates add anchoring to their service by calling one line.
