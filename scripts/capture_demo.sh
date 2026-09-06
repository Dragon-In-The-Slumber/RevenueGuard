#!/usr/bin/env bash
# Capture a demo dataset produced by REAL model decisions, then snapshot it.
#
# Why this exists: Gemini's free tier allows only ~20 model requests per day, so a
# live 5-minute demo cannot afford to call the model on stage. This runs the agent
# once while quota is available, then dumps the resulting database so the demo can
# be replayed from real recorded decisions — not regenerated, and not faked.
set -euo pipefail

COUNT="${COUNT:-5}"
DAYS="${DAYS:-4}"
API="${API:-http://localhost:8000}"
OUT="demo_data/demo_snapshot.sql"

echo "==> Resetting the database"
curl -sf -X POST "$API/api/simulation/reset" > /dev/null

echo "==> Generating $COUNT invoices (4 hero clients + filler)"
curl -sf -X POST "$API/api/invoices/simulate_batch" \
     -H 'Content-Type: application/json' -d "{\"count\": $COUNT}" > /dev/null

echo "==> Advancing $DAYS virtual days with live model decisions (slow: rate-limited)"
curl -sf -X POST "$API/api/simulation/tick?days=$DAYS" | head -c 200; echo

echo "==> Verifying the decisions came from the model, not the fallback"
docker compose exec -T db psql -U postgres -d revenueguard -t -A -c \
  "select count(*) filter (where content_snapshot like '%source: llm%') as model_made,
          count(*) as total
     from audit_logs where event_type = 'AGENT_DECISION';"

echo "==> Writing snapshot to $OUT"
docker compose exec -T db pg_dump -U postgres -d revenueguard \
  --data-only --inserts --table=invoices --table=audit_logs --table=webhook_events \
  > "$OUT"
wc -l "$OUT"
echo "Done. Restore with: bash scripts/restore_demo.sh"
