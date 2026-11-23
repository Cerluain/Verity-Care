"""Rebalance signer wallets on Base Sepolia.

Any signer below MIN_BALANCE gets topped up to TARGET_BALANCE by whichever
signer is currently richest (minus a safety reserve). Runs idempotently —
if everyone's above MIN_BALANCE, no txs are broadcast.

Invoked by:
  - scripts/rebalance.sh (manual, one-shot)
  - apps/onchain/main.py @app.on_event("startup") (auto, every restart)

Reads config from apps/onchain/.env. Idempotent, no side effects when
balances are healthy. Total gas cost per rebalance = ~0.00005 ETH per donor.
"""
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

MIN_BALANCE_ETH    = Decimal("0.0005")   # below this → needs top-up
TARGET_BALANCE_ETH = Decimal("0.0020")   # top-up to here
DONOR_RESERVE_ETH  = Decimal("0.0005")   # donor must keep at least this after sending


def _signers(w3: Web3) -> dict[str, Account]:
    env_keys = {
        "facility":       "FACILITY_SIGNER_PRIVATE_KEY",
        "ombudsman":      "OMBUDSMAN_SIGNER_PRIVATE_KEY",
        "verity_service": "VERITY_SERVICE_SIGNER_PRIVATE_KEY",
        "staff":          "STAFF_SIGNER_PRIVATE_KEY",
    }
    out = {}
    for role, env in env_keys.items():
        key = os.environ.get(env)
        if not key:
            continue
        out[role] = Account.from_key(key)
    return out


def _bal(w3, addr) -> Decimal:
    return Decimal(w3.from_wei(w3.eth.get_balance(addr), "ether"))


def rebalance(quiet: bool = False) -> dict:
    """Pull from whoever is richest → top up anyone below MIN_BALANCE.
    Returns a summary dict (used by both CLI and startup hook)."""
    load_dotenv()
    rpc = os.environ.get("CHAIN_RPC_URL")
    if not rpc:
        return {"skipped": "CHAIN_RPC_URL not set"}
    w3 = Web3(Web3.HTTPProvider(rpc))
    signers = _signers(w3)
    if not signers:
        return {"skipped": "no signer private keys in .env"}

    balances = {r: _bal(w3, a.address) for r, a in signers.items()}
    if not quiet:
        print("balances:")
        for r, bal in balances.items():
            flag = "  LOW" if bal < MIN_BALANCE_ETH else ""
            print(f"  {r:14s} {signers[r].address}  {bal:.4f} ETH{flag}")

    needs = [r for r, b in balances.items() if b < MIN_BALANCE_ETH]
    if not needs:
        if not quiet:
            print("\nall signers above MIN_BALANCE — nothing to do.")
        return {"transfers": [], "rebalanced": False}

    transfers = []
    chain_id = w3.eth.chain_id
    gas_price = w3.eth.gas_price

    for needy in needs:
        # Recompute balances each iteration (prior transfers may have moved donor).
        balances = {r: _bal(w3, a.address) for r, a in signers.items()}
        donors = sorted(
            [r for r in signers if r != needy
             and balances[r] >= MIN_BALANCE_ETH + DONOR_RESERVE_ETH],
            key=lambda r: balances[r], reverse=True,
        )
        if not donors:
            if not quiet:
                print(f"\n  ⚠ no donor can cover {needy} — all other wallets too low")
            transfers.append({"role": needy, "status": "no_donor"})
            continue
        donor_role = donors[0]
        donor = signers[donor_role]
        deficit = TARGET_BALANCE_ETH - balances[needy]
        # Cap at donor's surplus above its own reserve.
        donor_surplus = balances[donor_role] - MIN_BALANCE_ETH - DONOR_RESERVE_ETH
        amount = min(deficit, donor_surplus)
        if amount <= 0:
            transfers.append({"role": needy, "status": "donor_tight"})
            continue
        value = w3.to_wei(float(amount), "ether")
        tx = {
            "to":       signers[needy].address,
            "value":    value,
            "gas":      21000,
            "gasPrice": gas_price,
            "nonce":    w3.eth.get_transaction_count(donor.address),
            "chainId":  chain_id,
        }
        signed = donor.sign_transaction(tx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        transfers.append({
            "role": needy, "donor": donor_role,
            "amount_eth": f"{amount:.4f}", "tx": h.hex(), "status": "sent",
        })
        if not quiet:
            print(f"  → {donor_role} → {needy}  {amount:.4f} ETH  tx={h.hex()[:14]}…")

    if not quiet:
        print("\ndone.")
    return {"transfers": transfers, "rebalanced": True}


if __name__ == "__main__":
    result = rebalance(quiet=False)
    if result.get("skipped"):
        print(f"skipped: {result['skipped']}")
        sys.exit(0)
    sys.exit(0 if all(t.get("status") == "sent" for t in result.get("transfers", []))
             or not result.get("transfers") else 1)
