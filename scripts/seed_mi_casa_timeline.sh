#!/usr/bin/env bash
# scripts/seed_mi_casa_timeline.sh
#
# Pre-anchors Mi Casa Sept + Oct 2026 inventory snapshots on Base Sepolia
# (facility wallet signer) so the demo can open on a populated timeline.
# Nov 2026 is deliberately LEFT UNANCHORED so the operator can land it live
# during the pitch (one real tx in front of the judges).
#
# Reuses /facility/inventory/snapshot (the legacy one-shot: parse + commit
# fused) so we don't have to orchestrate parse → commit from bash.
#
# Idempotent at the hash level — re-running anchors the exact same hashes,
# which /verify finds in Postgres and won't double-spend gas on.

set -euo pipefail
BASE="${DASHBOARD_URL:-http://localhost:8000}"
FACILITY="mi-casa-life-care-az"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

anchor() {
  local period="$1"
  local photo="$REPO_ROOT/data/demo/inventory-sample-mi-casa-${period}.jpg"
  if [[ ! -f "$photo" ]]; then
    echo "  ⚠ skipping $period: photo not found at $photo"
    return
  fi
  echo "  → anchoring $period from $(basename "$photo")..."
  curl -sf -X POST "$BASE/facility/inventory/snapshot" \
    -F "facility_id=$FACILITY" \
    -F "period=$period" \
    -F "staff_pseudonym=FACILITY-ADMIN-MICASA" \
    -F "image=@$photo;type=image/jpeg" \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
tx    = d.get('tx_hash','?')[:14]
sig   = d.get('signer_role','?')
block = d.get('block_number','pending')
print(f'    tx={tx}  signer={sig}  block={block}  signed={not d.get(\"mocked\", True)}')"
}

echo "=== Mi Casa timeline seed ==="
echo "Anchoring Sep + Oct 2026 (Nov stays un-anchored for live demo click)"
echo
anchor "2026-09"
anchor "2026-10"
echo
echo "Done. Run: GET $BASE/facility/inventory?facility_id=$FACILITY to list."
echo "Nov 2026 is READY TO UPLOAD from the /facility UI during the demo."
