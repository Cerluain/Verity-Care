#!/usr/bin/env bash
# scripts/rebalance.sh — one-shot gas-rebalance across all 4 signer wallets.
#
# Any signer below MIN_BALANCE (0.0005 ETH) gets topped up to TARGET_BALANCE
# (0.0020 ETH) from whichever signer is currently richest. Idempotent.
#
# Usage:
#   bash scripts/rebalance.sh
#
# Call this after funding any single wallet — Hermes will pull from the fat
# one and distribute to the lean ones.

set -euo pipefail
cd "$(dirname "$0")/.."
cd apps/onchain
source .venv/bin/activate
exec python rebalance.py
