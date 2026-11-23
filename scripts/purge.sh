#!/usr/bin/env bash
# scripts/purge.sh — one-command demo reset.
#
# Wipes:
#   1) The Postgres index (deliveries + commits tables)
#   2) The care-plan sqlite (staff + guardian universe)
#   3) Local JSONL commit log (rotated with .bak timestamp)
#   4) Photo cache under data/care/runtime/photos/
#
# Chain data on Base Sepolia stays forever — we just stop surfacing it, so
# every demo run starts with a clean verify loop.
#
# Usage:
#   bash scripts/purge.sh              # wipe everything (default)
#   bash scripts/purge.sh deliveries   # only PoS rows + care sqlite
#   bash scripts/purge.sh commits      # only tx rows (cascades deliveries)
#
# Prereq: apps/onchain on :8001 AND apps/dashboard on :8000 (or set ONCHAIN_URL / DASH_URL).

set -euo pipefail
scope="${1:-all}"
onchain="${ONCHAIN_URL:-http://localhost:8001}"
dash="${DASH_URL:-http://localhost:8000}"

case "$scope" in
  all|deliveries|commits) ;;
  *) echo "usage: $0 [all|deliveries|commits]" >&2; exit 2 ;;
esac

echo "→ POST $onchain/admin/reset-demo?scope=$scope"
curl -fsS -X POST "$onchain/admin/reset-demo?scope=$scope" | python3 -m json.tool

# Also wipe the care-plan sqlite + photos so the staff/guardian universe is clean.
if [[ "$scope" == "all" || "$scope" == "deliveries" ]]; then
  echo
  echo "→ POST $dash/care/reset"
  curl -fsS -X POST "$dash/care/reset" | python3 -m json.tool || echo "(skipped: dashboard /care/reset not reachable)"
fi
