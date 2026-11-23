"""
packages/onchain-client/onchain_client.py - thin HTTP wrapper over apps/onchain.

Usage (Leo / Abhi):

    from onchain_client import commit, CLAIM_TAP
    import hashlib
    preimage = f"{nurse_license}|{door_id}|{timestamp}".encode()
    claim_hash = "0x" + hashlib.sha256(preimage).hexdigest()
    tx = commit(CLAIM_TAP, claim_hash)
    # tx = {tx_hash, explorer_url, claim_type, claim_type_label, committed_at, mocked}
"""
from __future__ import annotations
import os
from typing import Optional

import httpx

ONCHAIN_SERVICE_URL = os.getenv("ONCHAIN_SERVICE_URL", "http://localhost:8001")

CLAIM_TAP = 1
CLAIM_VOICE = 2
CLAIM_CASEFILE = 3
CLAIM_SIGNAL_CARD = 4

_client = httpx.Client(base_url=ONCHAIN_SERVICE_URL, timeout=10.0)


def commit(claim_type: int, claim_hash_hex: str) -> dict:
    """Commit a 32-byte hash on-chain. claim_hash_hex must be '0x' + 64 hex chars."""
    r = _client.post("/commit", json={"claim_type": claim_type, "claim_hash": claim_hash_hex})
    r.raise_for_status()
    return r.json()


def sign(content_b64: str) -> dict:
    """Sign content with Verity Care's ed25519 key. Returns {signature_b64, pubkey_b64, algo}."""
    r = _client.post("/sign", json={"content_b64": content_b64})
    r.raise_for_status()
    return r.json()


def verify_key() -> dict:
    """Return the public ed25519 verify key."""
    r = _client.get("/verify-key")
    r.raise_for_status()
    return r.json()


def list_commits(facility_id: Optional[str] = None, claim_type: Optional[int] = None) -> list[dict]:
    params = {}
    if facility_id:
        params["facility_id"] = facility_id
    if claim_type is not None:
        params["claim_type"] = claim_type
    r = _client.get("/commits", params=params)
    r.raise_for_status()
    return r.json()
