# packages/onchain-client — thin HTTP clients for the on-chain service

Dev A (phantom-spend) and Dev B (phantom-shift) import from here. No keys, no RPC, no web3.
Just HTTP calls to `apps/onchain` (default port 8001).

## Python (Leo + Abhi)

```python
from onchain_client import commit, CLAIM_TAP, CLAIM_SIGNAL_CARD

tx = commit(CLAIM_TAP, claim_hash_hex="0x" + sha256(preimage).hexdigest())
print(tx["tx_hash"], tx["explorer_url"])
```

## TypeScript (dashboard if needed)

```ts
import { commit, CLAIM_TAP } from "@verity/onchain-client";

const tx = await commit(CLAIM_TAP, "0x" + sha256Hex(preimage));
console.log(tx.tx_hash, tx.explorer_url);
```

## Mock mode (no wallet needed)

If `apps/onchain` is running with `MOCK=true`, every call returns `tx_hash` prefixed with `0xmock...`
and `explorer_url=null`. Treat these as normal. The UI renders them with a grey "⚠ mock" badge.
