"""
apps/onchain/main.py - Verity Care cryptographic trust service.

Owns:
  - The hot wallet signing on-chain commits.
  - The ed25519 key signing exported case files.
  - An append-only local commit log (./data/commit-log.jsonl).

Teammates call this service over HTTP; they never see the keys.

In MOCK=true mode, returns deterministic fake tx hashes so teammates can build
without a funded wallet. No special casing required downstream.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from nacl.signing import SigningKey, VerifyKey

load_dotenv()

CHAIN = os.getenv("CHAIN", "mock")
MOCK = os.getenv("MOCK", "false").lower() == "true" or CHAIN == "mock"
CHAIN_RPC_URL = os.getenv("CHAIN_RPC_URL", "")
VERITY_COMMIT_ADDRESS = os.getenv("VERITY_COMMIT_ADDRESS", "")
EXPLORER_BASE_URL = os.getenv("EXPLORER_BASE_URL", "")
# Three signer private keys (route by claim_type). Keep legacy single-key as fallback.
FACILITY_SIGNER_PRIVATE_KEY = os.getenv("FACILITY_SIGNER_PRIVATE_KEY", "")
OMBUDSMAN_SIGNER_PRIVATE_KEY = os.getenv("OMBUDSMAN_SIGNER_PRIVATE_KEY", "")
VERITY_SERVICE_SIGNER_PRIVATE_KEY = os.getenv("VERITY_SERVICE_SIGNER_PRIVATE_KEY", "")
LEGACY_SINGLE_KEY = os.getenv("VERITY_COMMIT_PRIVATE_KEY", "")
ED25519_SIGNING_KEY_B64 = os.getenv("ED25519_SIGNING_KEY_B64", "")
LOG_FILE = Path(os.getenv("LOG_FILE", "./data/commit-log.jsonl"))
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

CLAIM_TYPES = {1: "tap", 2: "voice", 3: "casefile", 4: "signal_card"}

# claim_type -> which signer role signs it
SIGNER_ROLE = {
    1: "facility",        # TAP
    2: "ombudsman",       # VOICE
    3: "verity_service",  # CASEFILE
    4: "facility",        # SIGNAL_CARD — facility uploaded the data, so facility signs
}

# ---------- ed25519 signing key ----------
if ED25519_SIGNING_KEY_B64:
    _sk = SigningKey(base64.b64decode(ED25519_SIGNING_KEY_B64))
else:
    # Dev-only fallback: generate ephemeral. Not deterministic across restarts.
    _sk = SigningKey.generate()
    print("[onchain] WARNING: no ED25519_SIGNING_KEY_B64 set. Using ephemeral key:",
          base64.b64encode(_sk.encode()).decode())

_PUBKEY_B64 = base64.b64encode(_sk.verify_key.encode()).decode()

# ---- chain signers (one per role) ----
_tx_locks = {"facility": threading.Lock(), "ombudsman": threading.Lock(), "verity_service": threading.Lock()}
_w3 = None
_contract = None
_accounts: dict[str, object] = {}

if not MOCK:
    try:
        from web3 import Web3
        _w3 = Web3(Web3.HTTPProvider(CHAIN_RPC_URL))
        abi = [{
            "type": "function", "name": "commit", "stateMutability": "nonpayable",
            "inputs": [{"name": "claimType", "type": "uint8"},
                       {"name": "claimHash", "type": "bytes32"}],
            "outputs": []
        }]
        _contract = _w3.eth.contract(address=Web3.to_checksum_address(VERITY_COMMIT_ADDRESS), abi=abi)

        role_keys = {
            "facility": FACILITY_SIGNER_PRIVATE_KEY,
            "ombudsman": OMBUDSMAN_SIGNER_PRIVATE_KEY,
            "verity_service": VERITY_SERVICE_SIGNER_PRIVATE_KEY,
        }
        for role, key in role_keys.items():
            # Fallback to legacy single-key if a per-role key is missing — keeps old demos working.
            effective = key or LEGACY_SINGLE_KEY
            if not effective:
                raise RuntimeError(f"missing private key for role {role}")
            _accounts[role] = _w3.eth.account.from_key(effective)
        print(f"[onchain] live mode on {CHAIN}.")
        for role, acct in _accounts.items():
            print(f"  signer[{role}] = {acct.address}")
    except Exception as e:
        print(f"[onchain] live-mode init failed; falling back to MOCK. reason: {e}")
        MOCK = True

app = FastAPI(title="Verity Care — on-chain service")


class CommitRequest(BaseModel):
    claim_type: int = Field(..., ge=1, le=4)
    claim_hash: str = Field(..., description="0x-prefixed 32-byte hex")


class CommitResponse(BaseModel):
    tx_hash: str
    explorer_url: Optional[str]
    block_number: Optional[int]
    claim_type: int
    claim_type_label: str
    signer_role: str
    signer_address: Optional[str]
    committed_at: str
    mocked: bool


class SignRequest(BaseModel):
    content_b64: str


class SignResponse(BaseModel):
    signature_b64: str
    pubkey_b64: str
    algo: str = "ed25519"


def _append_log(entry: dict) -> None:
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _mock_tx_hash(claim_type: int, claim_hash: str) -> str:
    seed = f"{claim_type}:{claim_hash}:{datetime.now(timezone.utc).isoformat()}".encode()
    return "0xmock" + hashlib.sha256(seed).hexdigest()[:60]


@app.get("/health")
def health():
    return {
        "ok": True, "chain": CHAIN, "mock": MOCK,
        "contract": VERITY_COMMIT_ADDRESS or None,
        "signers": {role: acct.address for role, acct in _accounts.items()} if _accounts else None,
        "pubkey_b64": _PUBKEY_B64,
    }


@app.get("/verify-key")
def verify_key():
    return {"pubkey_b64": _PUBKEY_B64, "algo": "ed25519"}


@app.post("/commit", response_model=CommitResponse)
def commit(req: CommitRequest):
    if req.claim_type not in CLAIM_TYPES:
        raise HTTPException(400, "unknown claim_type")
    if not req.claim_hash.startswith("0x") or len(req.claim_hash) != 66:
        raise HTTPException(400, "claim_hash must be 0x + 64 hex chars (bytes32)")

    now = datetime.now(timezone.utc).isoformat()
    label = CLAIM_TYPES[req.claim_type]
    role = SIGNER_ROLE[req.claim_type]

    if MOCK:
        tx_hash = _mock_tx_hash(req.claim_type, req.claim_hash)
        entry = {"tx_hash": tx_hash, "claim_type": req.claim_type, "claim_type_label": label,
                 "signer_role": role, "signer_address": None,
                 "claim_hash": req.claim_hash, "block_number": None, "explorer_url": None,
                 "committed_at": now, "mocked": True}
        _append_log(entry)
        return CommitResponse(**entry)

    account = _accounts[role]
    with _tx_locks[role]:
        try:
            nonce = _w3.eth.get_transaction_count(account.address)
            tx = _contract.functions.commit(req.claim_type, bytes.fromhex(req.claim_hash[2:])).build_transaction({
                "from": account.address, "nonce": nonce,
                "gas": 80_000, "maxFeePerGas": _w3.to_wei(3, "gwei"),
                "maxPriorityFeePerGas": _w3.to_wei(1, "gwei"),
            })
            signed = account.sign_transaction(tx)
            tx_hash_bytes = _w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hash = tx_hash_bytes.hex()
            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash
            # Fire-and-forget: don't wait for receipt in-line (adds 12s+).
            explorer = EXPLORER_BASE_URL + tx_hash if EXPLORER_BASE_URL else None
            entry = {"tx_hash": tx_hash, "claim_type": req.claim_type, "claim_type_label": label,
                     "signer_role": role, "signer_address": account.address,
                     "claim_hash": req.claim_hash, "block_number": None, "explorer_url": explorer,
                     "committed_at": now, "mocked": False}
            _append_log(entry)
            return CommitResponse(**entry)
        except Exception as e:
            print(f"[onchain] live-send failed: {e}; falling back to mock tx for this one request")
            tx_hash = _mock_tx_hash(req.claim_type, req.claim_hash)
            entry = {"tx_hash": tx_hash, "claim_type": req.claim_type, "claim_type_label": label,
                     "signer_role": role, "signer_address": None,
                     "claim_hash": req.claim_hash, "block_number": None, "explorer_url": None,
                     "committed_at": now, "mocked": True, "error": str(e)}
            _append_log(entry)
            return CommitResponse(**{k: v for k, v in entry.items() if k != "error"})


@app.get("/commits")
def list_commits(facility_id: Optional[str] = None, claim_type: Optional[int] = None):
    if not LOG_FILE.exists():
        return []
    out = []
    with LOG_FILE.open() as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if claim_type is not None and row.get("claim_type") != claim_type:
                continue
            # facility_id filtering is best-effort — depends on callers embedding it in claim preimage upstream.
            out.append(row)
    return out


@app.post("/sign", response_model=SignResponse)
def sign(req: SignRequest):
    try:
        content = base64.b64decode(req.content_b64)
    except Exception:
        raise HTTPException(400, "content_b64 must be valid base64")
    sig = _sk.sign(content).signature
    return SignResponse(signature_b64=base64.b64encode(sig).decode(), pubkey_b64=_PUBKEY_B64)
