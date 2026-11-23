# VerityCommit — on-chain append-only commitment log

Solidity contract that anchors fraud-detection claims from Verity Care's three pillars.
One function: `commit(uint8 claimType, bytes32 claimHash)` emits an indexed event.
No PHI on-chain, ever. Only hashes.

## Deploy

```bash
# From repo root:
cd contracts
cp .env.example .env
# Fill DEPLOYER_PRIVATE_KEY (freshly-generated wallet funded from faucet)
# Fill CHAIN_RPC_URL from the chain we picked at H0 (see shared.env)

forge install foundry-rs/forge-std --no-git
forge build

source .env
forge script script/Deploy.s.sol \
  --rpc-url $CHAIN_RPC_URL \
  --private-key $DEPLOYER_PRIVATE_KEY \
  --broadcast

# Copy deployed address into shared.env VERITY_COMMIT_ADDRESS
```

## Claim types

| ID | Label        | Who commits                       | When                    |
|----|--------------|-----------------------------------|-------------------------|
| 1  | TAP          | Dev B (phantom-shift)             | Each NFC tap            |
| 2  | VOICE        | Dev C (onchain service)           | End of each Vapi/11Labs call |
| 3  | CASEFILE     | Dev C (dashboard export)          | "Generate MFCU packet" click |
| 4  | SIGNAL_CARD  | Dev A (phantom-spend) — optional  | Per-signal computation  |

## Verifying a case file against this contract

An MFCU reviewer with a Verity Care PDF can:
1. Read the SHA-256 hex from the footer.
2. Query `Committed(claimType=3, claimHash=0x<sha256>)` on the explorer.
3. Confirm the block timestamp matches the "generated_at" in the PDF.
4. Confirm the ed25519 signature against `signature_pubkey` embedded in the envelope.

No API keys, no login, no Verity Care trust required.
