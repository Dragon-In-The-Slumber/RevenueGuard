#!/usr/bin/env bash
# Restore the recorded demo dataset. Makes zero model calls, so it works with an
# exhausted quota, no API key at all, or no internet.
set -euo pipefail

SNAP="${1:-demo_data/demo_snapshot.sql}"
[ -f "$SNAP" ] || { echo "No snapshot at $SNAP — run scripts/capture_demo.sh first."; exit 1; }

echo "==> Clearing current data"
docker compose exec -T db psql -U postgres -d revenueguard -q -c \
  "TRUNCATE webhook_events, audit_logs, invoices RESTART IDENTITY CASCADE;"

echo "==> Loading $SNAP"
# -o /dev/null suppresses the set_config/setval result tables the dump emits.
docker compose exec -T db psql -U postgres -d revenueguard -q -o /dev/null < "$SNAP"

docker compose exec -T db psql -U postgres -d revenueguard -t -A -c \
  "select 'invoices: ' || count(*) from invoices
   union all select 'audit rows: ' || count(*) from audit_logs
   union all select 'model-made decisions: ' || count(*) from audit_logs
     where event_type='AGENT_DECISION' and content_snapshot like '%source: llm%';"
echo "Restored. The dashboard now shows recorded real-model decisions."
