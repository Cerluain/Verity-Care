#!/usr/bin/env bash
# scripts/purge.sh — one-command demo reset.
#
# Wipes the Postgres index (deliveries + commits) and rotates the local JSONL
# log aside. Chain data on Base Sepolia stays forever — we just stop surfacing
# it, so verify/anchor flows feel "fresh" for the next demo run.
#
# Usage:
#   bash scripts/purge.sh              # wipe everything (default)
#   bash scripts/purge.sh deliveries   # only wipe proof-of-service rows
#   bash scripts/purge.sh commits      # only wipe tx rows (also cascades deliveries)
#
# Prereq: apps/onchain service running on :8001 (or ONCHAIN_URL override).

set -euo pipefail
scope="${1:-all}"
url="${ONCHAIN_URL:-http://localhost:8001}"

case "$scope" in
  all|deliveries|commits) ;;
  *) echo "usage: $0 [all|deliveries|commits]" >&2; exit 2 ;;
esac

echo "→ POST $url/admin/reset-demo?scope=$scope"
curl -fsS -X POST "$url/admin/reset-demo?scope=$scope" | python3 -m json.tool
