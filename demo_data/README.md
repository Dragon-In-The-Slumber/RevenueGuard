# Demo data

## Why this exists

Gemini's free tier allows ~20 model requests per day. A live five-minute demo
cannot afford to call the model on stage — a rate limit mid-pitch is fatal. So the
agent is run **once** while quota is available, and the resulting database is
snapshotted here. The demo replays real recorded model decisions; nothing is faked
and nothing is regenerated.

## Files

- `demo_snapshot.sql` — `pg_dump --data-only --inserts` of `invoices`,
  `audit_logs` and `webhook_events`.

## Usage

```bash
# Record a fresh run (needs model quota; takes ~15s on gemini-3.5-flash-lite)
COUNT=5 DAYS=4 bash scripts/capture_demo.sh

# Replay it — zero model calls, works with exhausted quota or no key at all
bash scripts/restore_demo.sh
```

## What the current snapshot contains

5 invoices (the 4 hero clients + 1 filler), 68 audit rows, **8 model-made
decisions** tagged `source: llm`, and a compliance rate of 60% over 5 genuine
verdicts (3 pass / 2 fail / 0 unreviewed) — so the draft → judge → rewrite loop is
demonstrable.

Highlights in this capture:
- **Pinnacle Industries → `SPLIT_INVOICE`**, citing its Milestone 1 / Milestone 2
  contract guardrail.
- **Acme Corp → `SEND_EMAIL STAGE_1`**, citing that its delays are internal
  approval cycles rather than cash flow.

## Known limitation: payment links are mocked in this snapshot

Razorpay test mode caps an account at **30 payment links**, and that cap was
reached during development, so links in this snapshot carry `plink_mock_*` ids and
are labelled `mode: "mock"` in the tool-call audit rows.

Two **genuine** Razorpay links were created by the agent earlier and still exist on
the Razorpay side. They can be fetched live to prove the integration is real:

| Invoice | Client | Payment link id | Amount |
|---|---|---|---|
| 1274 | NovaTech Labs | `plink_TYQcw2OgIH28IS` | INR 72,000 (80,000 less the agent's 10% discount) |
| 1272 | Globex Solutions | `plink_TYQd9XmvG0dFxm` | INR 340,000 |

```bash
# Prove a link is real, live, during the demo
docker compose exec -T api python -c "
import asyncio
from src.integrations.razorpay_client import get_client
print(asyncio.run(asyncio.to_thread(get_client().payment_link.fetch, 'plink_TYQcw2OgIH28IS')))"
```

They are deliberately **not** spliced into the snapshot: NovaTech chose
`SEND_EMAIL` in this capture, not `OFFER_DISCOUNT`, so a 72,000 discounted link
would not match the recorded decision. Showing them from the Razorpay dashboard or
the fetch above keeps the demo data honest.

To restore link creation, delete old test links in the Razorpay dashboard or use a
different test account.
