from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.config import settings
from src.logging_config import configure_logging, get_logger
from src.persistence.database import init_db, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas import SimulationBatchRequest
from src.persistence.crud import (
    generate_fake_invoices, get_last_email_date, log_audit_event, count_client_replies
)
from src.engine.core_loop import (
    process_simulation_tick, build_recovery_state, apply_state_to_invoice, persist_audit_entries
)
from src.dashboard_api import router as dashboard_router
from src.websocket import manager
from datetime import datetime, timedelta
import hashlib
from src.integrations import razorpay_client
from typing import Optional, Any
from src.rag.seed_data import seed_database
from pydantic import BaseModel, Field
from src.persistence.models import Invoice, InvoiceStatus, AuditLog, WebhookEvent
from sqlalchemy.future import select
from sqlalchemy import delete
from src.graph.builder import reply_graph
from src.simulation.runner import run_simulation, compare

logger = get_logger("revenueguard.api")

# Global state for simulation virtual date
simulation_state = {
    "virtual_date": datetime.utcnow(),
    # Surfaced in the UI so a reproducible run can be repeated exactly.
    "seed": 42,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting RevenueGuard | provider=%s model=%s razorpay=%s",
                settings.active_provider, settings.active_model,
                "live" if settings.razorpay_configured else "mock")
    await init_db()
    # Initialize ChromaDB and seed RAG context on startup
    seed_database()
    yield

app = FastAPI(
    title="RevenueGuard API v2 B2B",
    description="Scalable API for AI Revenue Recovery",
    version="0.1.0",
    lifespan=lifespan
)

# allow_origins=["*"] with allow_credentials=True is a spec violation browsers
# reject outright. Origins now come from CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Demo-Token", "X-Razorpay-Signature"],
)


def require_demo_token(x_demo_token: str = Header(default="")) -> None:
    """
    Gate for destructive and simulation-control endpoints.

    No token configured means local development and the check is skipped; setting
    DEMO_TOKEN in any deployed environment closes /reset, which otherwise deletes
    every row in both tables for anyone who finds it.
    """
    if not settings.demo_token:
        return
    if x_demo_token != settings.demo_token:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Demo-Token")

app.include_router(dashboard_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "v2_b2b"}

@app.post("/api/invoices/simulate_batch")
async def create_simulation_batch(request: SimulationBatchRequest, db: AsyncSession = Depends(get_db),
                                  _: None = Depends(require_demo_token)):
    """Generates fake overdue invoices in the database."""
    count = await generate_fake_invoices(db, request.count)
    await manager.broadcast({"event": "state_updated"})
    return {"status": "success", "message": f"Generated {count} invoices."}

@app.post("/api/simulation/tick")
async def advance_simulation_tick(days: int = 1, db: AsyncSession = Depends(get_db),
                                  _: None = Depends(require_demo_token)):
    """Advances the virtual simulation date and processes the core loop."""
    total_processed = 0

    async def broadcast_tick(virtual_date, invoices, final_states):
        """
        Emit the TICK_UPDATE the visualiser has always listened for.

        LangGraphFlow checks `data.type === 'TICK_UPDATE'` and `payload.active_nodes`,
        but the backend only ever sent {"event": "state_updated"} — which is why the
        graph never animated.
        """
        active_nodes = sorted({n for s in final_states for n in (s.get("visited_nodes") or [])})
        traces = [
            {
                "invoice_id": s["invoice_id"],
                "client_name": s["client_name"],
                "nodes": s.get("visited_nodes") or [],
                "action": (s.get("effective_action") or {}).get("action"),
                "status": s.get("new_status") or s.get("current_status"),
            }
            for s in final_states if s.get("visited_nodes")
        ]
        await manager.broadcast({
            "type": "TICK_UPDATE",
            "event": "state_updated",
            "payload": {
                "virtual_date": virtual_date.isoformat(),
                "active_nodes": active_nodes,
                "processed_count": len(invoices),
                "traces": traces[:20],
            },
        })

    for _ in range(days):
        simulation_state["virtual_date"] += timedelta(days=1)
        processed = await process_simulation_tick(
            db, simulation_state["virtual_date"], broadcast=broadcast_tick
        )
        total_processed += processed

    await manager.broadcast({
        "type": "TICK_COMPLETE",
        "event": "state_updated",
        "virtual_date": simulation_state["virtual_date"].isoformat(),
    })

    return {
        "status": "success",
        "virtual_date": simulation_state["virtual_date"].isoformat(),
        "invoices_processed": total_processed
    }

@app.get("/api/simulation/state")
async def get_simulation_state():
    """Returns the current virtual date and seed for the UI."""
    return {
        "virtual_date": simulation_state["virtual_date"].isoformat(),
        "seed": simulation_state.get("seed", 42),
    }

@app.post("/api/simulation/reset")
async def reset_simulation(db: AsyncSession = Depends(get_db),
                           _: None = Depends(require_demo_token)):
    """Clears all invoices and audit logs, and resets virtual date."""
    await db.execute(delete(AuditLog))
    await db.execute(delete(Invoice))
    await db.commit()
    
    simulation_state["virtual_date"] = datetime.utcnow()
    await manager.broadcast({"event": "state_updated"})
    return {"status": "success", "message": "Database reset."}

@app.post("/api/simulation/run")
async def run_reproducible_simulation(
    policy: str = "agent",
    seed: int = 42,
    count: int = 100,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_demo_token),
):
    """
    Run one full simulation from a blank slate, reproducibly.

    Same seed and count produce the same portfolio and the same environment dice,
    so `policy=agent` and `policy=ladder` are a controlled comparison rather than
    two unrelated runs. Destroys existing data — it is a benchmark, not a tick.
    """
    if policy not in ("agent", "ladder"):
        raise HTTPException(status_code=400, detail="policy must be 'agent' or 'ladder'")

    metrics = await run_simulation(db, policy=policy, seed=seed, count=count, days=days)
    simulation_state["virtual_date"] = datetime(2026, 1, 1) + timedelta(days=days)
    simulation_state["seed"] = seed
    await manager.broadcast({"event": "state_updated"})
    return metrics


@app.post("/api/simulation/ab")
async def run_ab_comparison(
    seed: int = 42,
    count: int = 100,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_demo_token),
):
    """
    The headline result: the agent against a fixed-schedule chaser.

    Runs both policies over an identical portfolio with identical environment
    dice, and returns both sets of metrics plus the deltas. The database is left
    holding the agent run so the UI has something to show afterwards.
    """
    ladder = await run_simulation(db, policy="ladder", seed=seed, count=count, days=days)
    agent = await run_simulation(db, policy="agent", seed=seed, count=count, days=days)

    simulation_state["virtual_date"] = datetime(2026, 1, 1) + timedelta(days=days)
    simulation_state["seed"] = seed
    await manager.broadcast({"event": "state_updated"})

    return {"seed": seed, "count": count, "days": days,
            "agent": agent, "ladder": ladder, "comparison": compare(agent, ladder)}


@app.get("/api/approvals")
async def get_approval_queue(db: AsyncSession = Depends(get_db)):
    """
    Cases the agent handed to a person, with the agent's case attached.

    The human-in-the-loop pillar had no UI at all: STAGE_4 gating and guard vetoes
    routed work to humans that nobody could see, let alone act on.
    """
    result = await db.execute(
        select(Invoice)
        .where(Invoice.status.in_([InvoiceStatus.HUMAN_ESCALATED, InvoiceStatus.DISPUTE]))
        .order_by(Invoice.amount.desc())
    )
    invoices = result.scalars().all()
    if not invoices:
        return {"approvals": []}

    ids = [i.id for i in invoices]
    logs = await db.execute(
        select(AuditLog)
        .where(AuditLog.invoice_id.in_(ids))
        .where(AuditLog.event_type.in_([
            "AGENT_DECISION", "ACTION_VETOED", "HUMAN_ESCALATED", "STATUS_CHANGED",
            "COMPLIANCE_FAILED", "INTENT_CLASSIFIED",
        ]))
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
    )
    by_invoice: dict[int, list] = {}
    for log in logs.scalars().all():
        by_invoice.setdefault(log.invoice_id, []).append(log)

    approvals = []
    for inv in invoices:
        entries = by_invoice.get(inv.id, [])
        decision = next((e for e in entries if e.event_type == "AGENT_DECISION"), None)
        veto = next((e for e in entries if e.event_type == "ACTION_VETOED"), None)
        handoff = next((e for e in entries if e.event_type == "HUMAN_ESCALATED"), None)

        approvals.append({
            "invoice_id": inv.id,
            "client_name": inv.client_name,
            "amount": float(inv.amount),
            "status": inv.status.value,
            "escalation_stage": inv.escalation_stage,
            "contact_attempts": inv.contact_attempts or 0,
            "relationship_score": inv.relationship_score if inv.relationship_score is not None else 1.0,
            "reason": (handoff.rule_applied if handoff else None) or "Requires human review",
            "detail": handoff.agent_reasoning if handoff else None,
            # The agent's case, so a reviewer decides with the same information.
            "agent_proposed": decision.action_taken if decision else None,
            "agent_reasoning": decision.agent_reasoning if decision else None,
            "guard_veto": veto.rule_applied if veto else None,
            "guard_detail": veto.agent_reasoning if veto else None,
        })
    return {"approvals": approvals}


class ApprovalDecision(BaseModel):
    note: str = ""


@app.post("/api/approvals/{id}/approve")
async def approve_case(id: int, body: ApprovalDecision, db: AsyncSession = Depends(get_db)):
    """A human authorises the agent to continue; the invoice re-enters the loop."""
    result = await db.execute(select(Invoice).where(Invoice.id == id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {id} not found")

    old_status = invoice.status.value
    # Returning it to NOTIFIED_2 puts it back in the actionable set with its
    # escalation history intact.
    invoice.status = InvoiceStatus.NOTIFIED_2
    await log_audit_event(
        db, invoice.id, "HUMAN_APPROVED",
        body.note or "Human approved continued collection.",
        f"Approved by human; released from {old_status} back into the workflow",
        simulation_state["virtual_date"], rule_applied="Human-in-the-loop approval",
    )
    await db.commit()
    await manager.broadcast({"event": "state_updated"})
    return {"status": "approved", "invoice_id": id, "old_status": old_status,
            "new_status": invoice.status.value}


@app.post("/api/approvals/{id}/reject")
async def reject_case(id: int, body: ApprovalDecision, db: AsyncSession = Depends(get_db)):
    """A human stops collection permanently."""
    result = await db.execute(select(Invoice).where(Invoice.id == id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {id} not found")

    old_status = invoice.status.value
    invoice.status = InvoiceStatus.LEGAL_HOLD
    await log_audit_event(
        db, invoice.id, "HUMAN_REJECTED",
        body.note or "Human halted collection on this invoice.",
        f"Rejected by human; moved from {old_status} to LEGAL_HOLD",
        simulation_state["virtual_date"], rule_applied="Human-in-the-loop rejection",
    )
    await db.commit()
    await manager.broadcast({"event": "state_updated"})
    return {"status": "rejected", "invoice_id": id, "old_status": old_status,
            "new_status": invoice.status.value}


class ClientReplyRequest(BaseModel):
    message: str

@app.post("/api/invoices/{id}/reply")
async def client_reply(id: int, request: ClientReplyRequest, db: AsyncSession = Depends(get_db)):
    """Classifies a simulated client reply and persists the resulting state change."""
    result = await db.execute(select(Invoice).where(Invoice.id == id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {id} not found")

    old_status = invoice.status.value

    # A full state — the routing functions dereference days_overdue and virtual_date
    # unconditionally, so a partial dict raises KeyError before any node runs.
    last_email_dt = await get_last_email_date(db, invoice.id)
    replies = await count_client_replies(db, invoice.id)
    state = build_recovery_state(
        invoice,
        simulation_state["virtual_date"],
        last_email_dt,
        client_reply=request.message,
        client_replies=replies,
    )
    # A reply classifies and halts; it must not draft or send anything.
    state["should_send_email"] = False

    final_state = await reply_graph.ainvoke(state)

    # Persist: status, promised_date, escalation stage, and the audit trail.
    apply_state_to_invoice(invoice, final_state)
    entries_written = await persist_audit_entries(
        db, invoice.id, final_state.get("audit_entries", []), simulation_state["virtual_date"]
    )
    await db.commit()
    await db.refresh(invoice)

    await manager.broadcast({"event": "state_updated"})
    return {
        "status": "success",
        "invoice_id": invoice.id,
        "intent": final_state.get("classified_intent"),
        "confidence": final_state.get("intent_confidence"),
        "entities": final_state.get("extracted_entities"),
        "old_status": old_status,
        "new_status": invoice.status.value,
        "audit_entries_written": entries_written,
    }

class RazorpayWebhookEvent(BaseModel):
    """
    Accepts both the Razorpay-native envelope and a flat test shape.

    Native:  {"event": "invoice.paid", "payload": {"invoice": {"entity": {"id": "inv_42"}}}}
    Flat:    {"event": "invoice.paid", "payload": {"invoice_id": "42"}}

    The flat form is documented for manual curl testing; the dashboard always
    sends the native envelope via fireWebhook() in lib/api.ts.
    """
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)

    def resolve_invoice_id(self) -> Optional[int]:
        entity_id = (
            self.payload.get("invoice", {}).get("entity", {}).get("id")
            or self.payload.get("payment", {}).get("entity", {}).get("id")
            or ""
        )
        if isinstance(entity_id, str) and entity_id.startswith("inv_"):
            candidate = entity_id[len("inv_"):]
        else:
            candidate = self.payload.get("invoice_id")

        try:
            return int(candidate)
        except (TypeError, ValueError):
            return None

    def event_id(self) -> Optional[str]:
        """Razorpay's own delivery id, when present, for idempotency."""
        for path in (("payment", "entity", "id"), ("invoice", "entity", "id")):
            node = self.payload
            for key in path:
                node = node.get(key, {}) if isinstance(node, dict) else {}
            if isinstance(node, str) and node:
                return f"{self.event}:{node}"
        return None


# event -> (new status or None to leave unchanged, audit event type, action text)
WEBHOOK_EFFECTS = {
    "invoice.paid":             ("RECOVERED", "PAYMENT_RECEIVED", "Marked as RECOVERED"),
    "payment_link.paid":        ("RECOVERED", "PAYMENT_RECEIVED", "Marked as RECOVERED"),
    "virtual_account.credited": ("RECOVERED", "PAYMENT_RECEIVED", "Marked as RECOVERED"),
    "invoice.partially_paid":   (None,        "PAYMENT_RECEIVED", "Logged partial payment"),
    "payment.dispute.created":  ("DISPUTE",   "STATUS_CHANGED",   "Routed to human for dispute resolution"),
    "payment.failed":           (None,        "PAYMENT_FAILED",   "Logged failed payment attempt"),
}


@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receives Razorpay webhook events and reports what actually changed."""
    raw = await request.body()

    # Verify the signature whenever a secret is configured. Without this the
    # endpoint marks any invoice RECOVERED for anyone who can reach it.
    signature = request.headers.get("X-Razorpay-Signature", "")
    if settings.razorpay_webhook_secret:
        if not signature:
            raise HTTPException(status_code=401, detail="Missing X-Razorpay-Signature")
        if not razorpay_client.verify_webhook_signature(raw, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        body = RazorpayWebhookEvent.model_validate_json(raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Malformed webhook payload: {e}")

    if body.event not in WEBHOOK_EFFECTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported event '{body.event}'. Known: {sorted(WEBHOOK_EFFECTS)}",
        )

    invoice_id = body.resolve_invoice_id()
    if invoice_id is None:
        raise HTTPException(
            status_code=422,
            detail="Could not resolve an invoice id from the payload. Send "
                   "payload.invoice.entity.id as 'inv_<id>' or payload.invoice_id.",
        )

    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        # A webhook naming an invoice we do not have is a real error, not a no-op.
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")

    # Idempotency: Razorpay retries deliveries, and a replayed invoice.paid would
    # otherwise write a duplicate PAYMENT_RECEIVED row on every retry.
    event_id = body.event_id() or f"{body.event}:{invoice_id}:{hashlib.sha256(raw).hexdigest()[:16]}"
    seen = await db.execute(select(WebhookEvent).where(WebhookEvent.event_id == event_id))
    if seen.scalar_one_or_none():
        return {
            "status": "duplicate_ignored",
            "event": body.event,
            "invoice_id": invoice.id,
            "matched": True,
            "old_status": invoice.status.value,
            "new_status": invoice.status.value,
        }

    new_status, audit_event, action = WEBHOOK_EFFECTS[body.event]
    old_status = invoice.status.value

    if new_status:
        invoice.status = InvoiceStatus(new_status)

    await log_audit_event(
        db, invoice.id, audit_event, f"Webhook {body.event}", action,
        simulation_state["virtual_date"],
    )
    db.add(WebhookEvent(event_id=event_id, event_type=body.event, invoice_id=invoice.id))
    await db.commit()
    await db.refresh(invoice)

    await manager.broadcast({"event": "state_updated"})
    return {
        "status": "processed",
        "event": body.event,
        "invoice_id": invoice.id,
        "matched": True,
        "old_status": old_status,
        "new_status": invoice.status.value,
    }
