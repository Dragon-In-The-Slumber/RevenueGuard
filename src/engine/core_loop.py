import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.persistence.crud import (
    get_actionable_invoices, log_audit_event, build_audit_log, get_last_email_date,
    count_client_replies, get_interaction_history, get_tick_context
)
from src.persistence.models import Invoice, InvoiceStatus
from datetime import datetime, timedelta

from src.graph.builder import compiled_graph


def build_recovery_state(invoice: Invoice, virtual_date: datetime, last_email_dt: datetime | None,
                         client_reply: str | None = None, client_replies: int = 0,
                         interaction_history: list | None = None) -> dict:
    """
    Build a complete RecoveryState for one invoice.

    Every key the graph and its routing functions read must be present — the routers
    dereference `days_overdue` and `virtual_date` unconditionally, so a partial dict
    raises KeyError on the first edge. Shared by the tick loop and the reply endpoint.
    """
    return {
        "invoice_id": invoice.id,
        "client_name": invoice.client_name,
        "client_email": invoice.client_email,
        "amount": invoice.amount,
        "due_date": invoice.due_date.isoformat(),
        "current_status": invoice.status.value if hasattr(invoice.status, "value") else invoice.status,
        "days_overdue": (virtual_date - invoice.due_date).days,
        "escalation_stage": invoice.escalation_stage or "STAGE_1",
        "last_email_date": last_email_dt.isoformat() if last_email_dt else None,
        "virtual_date": virtual_date.isoformat(),
        "promised_date": invoice.promised_date.isoformat() if invoice.promised_date else None,
        "contact_attempts": invoice.contact_attempts or 0,
        "client_replies": client_replies,
        "client_profile": None,
        "stop_reason": None,
        "notify_payload": None,
        "interaction_history": interaction_history or [],
        "proposed_action": None,
        "action_validated": None,
        "veto_reason": None,
        "substituted_action": None,
        "effective_action": None,
        "offer_context": None,
        "visited_nodes": [],
        "relationship_score": invoice.relationship_score if invoice.relationship_score is not None else 1.0,
        "tool_calls": [],
        "client_reply": client_reply,
        "classified_intent": None,
        "intent_confidence": None,
        "extracted_entities": None,
        "retrieved_context": None,
        "drafted_email": None,
        "compliance_verdict": None,
        "compliance_reason": None,
        "compliance_retries": 0,
        "payment_link_id": None,
        "payment_link_url": None,
        "virtual_account_details": None,
        "action_taken": None,
        "new_status": None,
        "rule_applied": None,
        "audit_entries": [],
        "should_send_email": True,
    }


def apply_state_to_invoice(invoice: Invoice, final_state: dict) -> None:
    """Write the graph's decisions back onto the invoice row. Does not commit."""
    if final_state.get("new_status"):
        invoice.status = InvoiceStatus(final_state["new_status"])

    if final_state.get("escalation_stage"):
        invoice.escalation_stage = final_state["escalation_stage"]

    # id and URL are stored in their own columns.
    if final_state.get("payment_link_id"):
        invoice.razorpay_payment_link_id = final_state["payment_link_id"]
    if final_state.get("payment_link_url"):
        invoice.razorpay_payment_link_url = final_state["payment_link_url"]
    va = final_state.get("virtual_account_details")
    if va and va.get("id"):
        invoice.razorpay_virtual_account_id = va["id"]

    # The promise date the graph settled on. Written from state rather than from
    # extracted_entities alone so the PTP gate reads back what the gate wrote.
    if final_state.get("promised_date"):
        invoice.promised_date = datetime.fromisoformat(final_state["promised_date"])

    # Contact attempts only ever increase; stopping rule 5 caps them.
    attempts = final_state.get("contact_attempts")
    if attempts is not None and attempts > (invoice.contact_attempts or 0):
        invoice.contact_attempts = attempts

    # Relationship damage from over-escalation persists across ticks.
    score = final_state.get("relationship_score")
    if score is not None and score < (invoice.relationship_score if invoice.relationship_score is not None else 1.0):
        invoice.relationship_score = score


async def persist_audit_entries(db: AsyncSession, invoice_id: int, entries: list[dict],
                                virtual_date: datetime) -> int:
    """
    Write a tick's audit entries with a monotonic offset per entry.

    All entries produced in one tick share the same virtual date, so without the
    offset the timeline has no defined order and renders scrambled.
    """
    for idx, entry in enumerate(entries):
        await log_audit_event(
            db,
            invoice_id,
            entry["event_type"],
            entry["reasoning"],
            entry["action"],
            virtual_date + timedelta(milliseconds=idx),
            rule_applied=entry.get("rule"),
            content_snapshot=entry.get("content"),
            compliance_verdict=entry.get("compliance_verdict"),
        )
    return len(entries)


def _audit_rows(invoice_id: int, entries: list[dict], virtual_date: datetime) -> list:
    """Build a tick's audit rows, monotonically ordered, without touching the session."""
    return [
        build_audit_log(
            invoice_id,
            entry["event_type"],
            entry["reasoning"],
            entry["action"],
            virtual_date + timedelta(milliseconds=idx),
            rule_applied=entry.get("rule"),
            content_snapshot=entry.get("content"),
            compliance_verdict=entry.get("compliance_verdict"),
        )
        for idx, entry in enumerate(entries)
    ]


async def process_simulation_tick(db: AsyncSession, virtual_date: datetime,
                                  broadcast=None):
    """
    Advance the simulation by one day.

    Three phases, because an AsyncSession is not concurrency-safe: read everything
    the batch needs, run the graphs concurrently (nodes are pure, so this is safe),
    then apply and write once. Previously this looped sequentially and committed
    per audit row — hundreds of round trips per tick, and a mid-tick failure left
    the database half-updated.
    """
    invoices = await get_actionable_invoices(db)
    if not invoices:
        return 0

    # --- Phase 1: bulk read ---
    ctx = await get_tick_context(db, [inv.id for inv in invoices])

    states = [
        build_recovery_state(
            inv, virtual_date, ctx[inv.id]["last_email"],
            client_replies=ctx[inv.id]["replies"],
            interaction_history=ctx[inv.id]["history"],
        )
        for inv in invoices
    ]

    # --- Phase 2: run graphs concurrently, bounded ---
    semaphore = asyncio.Semaphore(max(1, settings.tick_concurrency))

    async def run_one(state):
        async with semaphore:
            try:
                return await compiled_graph.ainvoke(state)
            except Exception as e:
                # One invoice failing must not abort the tick, but it must be
                # visible rather than silently dropped.
                print(f"Tick error on invoice {state['invoice_id']}: {type(e).__name__}: {e}")
                return {
                    **state,
                    "audit_entries": state.get("audit_entries", []) + [{
                        "event_type": "TICK_ERROR",
                        "reasoning": f"{type(e).__name__}: {e}",
                        "action": "Graph execution failed for this invoice",
                        "rule": None,
                        "content": None,
                    }],
                }

    final_states = await asyncio.gather(*(run_one(s) for s in states))

    # --- Phase 3: apply and write once ---
    rows = []
    for invoice, final_state in zip(invoices, final_states):
        apply_state_to_invoice(invoice, final_state)
        entries = list(final_state.get("audit_entries", []))

        # Record the path through the graph so the Execution Trace shows this
        # invoice's real route instead of six unrelated logs from six invoices.
        visited = final_state.get("visited_nodes") or []
        if visited:
            entries.append({
                "event_type": "GRAPH_PATH",
                "reasoning": " -> ".join(visited),
                "action": f"Traversed {len(visited)} nodes",
                "rule": None,
                "content": None,
            })

        rows.extend(_audit_rows(invoice.id, entries, virtual_date))

    if rows:
        db.add_all(rows)
    await db.commit()

    if broadcast:
        await broadcast(virtual_date, invoices, final_states)

    return len(rows)
