#!/usr/bin/env bash
# Seed the guardian/staff demo around the current time (run ~10 min before the demo).
#   bash scripts/seed_demo.sh            # anchor on now
#   bash scripts/seed_demo.sh --at 10:00 # anchor on a specific demo time
# Resets check-ins, disputes and photos, re-times every task, pre-fills morning check-ins
# (placeholder photos, not on-chain), leaves 2 tasks due for Priya and 2 for Marcus.
set -euo pipefail
BASE="${DASHBOARD_URL:-http://localhost:8000}"
AT=""
if [[ "${1:-}" == "--at" && -n "${2:-}" ]]; then AT="?at=$2"; fi
curl -sf -X POST "$BASE/care/seed$AT" | python3 -m json.tool
