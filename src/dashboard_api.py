from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import timedelta
from src.persistence.database import get_db
from src.persistence.models import Invoice, AuditLog, InvoiceStatus
from src.websocket import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't really expect the client to send much, but we listen to keep connection open
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.get("/api/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    # Total at risk (all invoices that are not recovered)
    result = await db.execute(select(func.sum(Invoice.amount)).where(Invoice.status != InvoiceStatus.RECOVERED))
    total_at_risk = result.scalar() or 0

    # Total recovered
    result_recovered = await db.execute(select(func.sum(Invoice.amount)).where(Invoice.status == InvoiceStatus.RECOVERED))
    total_recovered = result_recovered.scalar() or 0

    # Counts
    total_invoices_result = await db.execute(select(func.count(Invoice.id)))
    total_invoices = total_invoices_result.scalar() or 0

    recovered_invoices_result = await db.execute(select(func.count(Invoice.id)).where(Invoice.status == InvoiceStatus.RECOVERED))
    recovered_invoices = recovered_invoices_result.scalar() or 0

    recovery_rate = 0
    if (total_at_risk + total_recovered) > 0:
        recovery_rate = (total_recovered / (total_at_risk + total_recovered)) * 100

    return {
        "totalAtRisk": total_at_risk,
        "totalRecovered": total_recovered,
        "recoveryRate": recovery_rate,
        "totalInvoices": total_invoices,
        "recoveredInvoices": recovered_invoices
    }

@router.get("/api/funnel")
async def get_funnel(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Invoice.status, func.count(Invoice.id), func.sum(Invoice.amount))
        .group_by(Invoice.status)
    )
    funnel_data = []
    for row in result:
        funnel_data.append({
            "status": row[0],
            "count": row[1],
            "amount": row[2]
        })
    return {"funnel": funnel_data}
@router.get("/api/invoices/{invoice_id}/audit-logs")
async def get_invoice_audit_logs(invoice_id: str, db: AsyncSession = Depends(get_db)):
    # If it's a sample request, find the invoice with the most activity
    target_id = invoice_id
    if invoice_id == "sample":
        # Find invoice with most logs
        count_query = await db.execute(
            select(AuditLog.invoice_id, func.count(AuditLog.id).label("c"))
            .group_by(AuditLog.invoice_id)
            .order_by(func.count(AuditLog.id).desc())
            .limit(1)
        )
        row = count_query.first()
        if row:
            target_id = str(row[0])
        else:
            return {"trail": []}

    try:
        numeric_id = int(target_id)
    except ValueError:
        return {"trail": []}

    result = await db.execute(
        select(AuditLog, Invoice.client_name)
        .join(Invoice, AuditLog.invoice_id == Invoice.id)
        .where(AuditLog.invoice_id == numeric_id)
        # id breaks ties: entries within one tick are milliseconds apart, and a
        # timestamp-only sort lets Postgres return them in any order.
        .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
    )
    
    trail = []
    for audit, client_name in result:
        trail.append({
            "id": audit.id,
            "invoice_id": audit.invoice_id,
            "client_name": client_name,
            "timestamp": audit.timestamp.isoformat(),
            "event_type": audit.event_type,
            "agent_reasoning": audit.agent_reasoning,
            "action_taken": audit.action_taken,
            "rule_applied": audit.rule_applied,
            "content_snapshot": audit.content_snapshot
        })
    return {"trail": trail, "invoice_id": target_id}
@router.get("/api/audit-logs")
async def get_recent_audit_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditLog, Invoice.client_name)
        .join(Invoice, AuditLog.invoice_id == Invoice.id)
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .limit(20)
    )
    
    logs = []
    for audit, client_name in result:
        logs.append({
            "id": audit.id,
            "invoice_id": audit.invoice_id,
            "client_name": client_name,
            "timestamp": audit.timestamp.isoformat(),
            "event_type": audit.event_type,
            "agent_reasoning": audit.agent_reasoning,
            "action_taken": audit.action_taken,
            "rule_applied": audit.rule_applied,
            "content_snapshot": audit.content_snapshot
        })
    return {"logs": logs}

COOLDOWN_DAYS = 4


@router.get("/api/invoices")
async def get_all_invoices(status: str = None, db: AsyncSession = Depends(get_db)):
    query = select(Invoice)
    if status:
        query = query.where(Invoice.status == InvoiceStatus(status))
    query = query.order_by(Invoice.due_date.desc())
    result = await db.execute(query)
    invoices = result.scalars().all()

    # Real cooldown data. The Cooldown Board previously fabricated this with
    # `(inv.id * 17) % 7` — a hash of the primary key on the panel whose whole
    # purpose is proving the frequency limit is enforced.
    last_contacts = await db.execute(
        select(AuditLog.invoice_id, func.max(AuditLog.timestamp))
        .where(AuditLog.event_type == "EMAIL_SENT")
        .group_by(AuditLog.invoice_id)
    )
    last_map = {inv_id: ts for inv_id, ts in last_contacts}

    blocked_counts = await db.execute(
        select(AuditLog.invoice_id, func.count(AuditLog.id))
        .where(AuditLog.event_type == "ESCALATION_BLOCKED")
        .group_by(AuditLog.invoice_id)
    )
    blocked_map = {inv_id: c for inv_id, c in blocked_counts}

    payload = []
    for inv in invoices:
        last = last_map.get(inv.id)
        payload.append({
            "id": inv.id,
            "amount": float(inv.amount),
            "client_name": inv.client_name,
            "client_email": inv.client_email,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "status": inv.status,
            "promised_date": inv.promised_date.isoformat() if inv.promised_date else None,
            "escalation_stage": inv.escalation_stage,
            "contact_attempts": inv.contact_attempts or 0,
            "relationship_score": inv.relationship_score if inv.relationship_score is not None else 1.0,
            "razorpay_payment_link_id": inv.razorpay_payment_link_id,
            "razorpay_payment_link_url": inv.razorpay_payment_link_url,
            "razorpay_virtual_account_id": inv.razorpay_virtual_account_id,
            "last_contact_date": last.isoformat() if last else None,
            "next_contact_allowed_date": (
                (last + timedelta(days=COOLDOWN_DAYS)).isoformat() if last else None
            ),
            "escalations_blocked": blocked_map.get(inv.id, 0),
        })
    return {"invoices": payload}

from fastapi import HTTPException
from src.rag.vector_store import search_client_context, search_client_context_with_metadata
from src.domain.clients import HERO_CLIENTS, get_profile, is_hero, profile_as_dict

@router.get("/api/invoices/{invoice_id}")
async def get_invoice_by_id(invoice_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    return {
        "id": inv.id,
        "amount": float(inv.amount),
        "client_name": inv.client_name,
        "client_email": inv.client_email,
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "status": inv.status,
        "promised_date": inv.promised_date.isoformat() if inv.promised_date else None,
        "escalation_stage": inv.escalation_stage,
        "razorpay_payment_link_id": inv.razorpay_payment_link_id,
        "razorpay_virtual_account_id": inv.razorpay_virtual_account_id
    }

@router.get("/api/clients/{name}/context")
async def get_client_rag_context(name: str):
    # Retrieval returns a joined string plus the metadata stored with the document.
    retrieved = await search_client_context_with_metadata(
        name, "contract terms payment history risk"
    )
    profile = get_profile(name)

    return {
        "context": retrieved["context"] or "No profile on file for this client.",
        "matched": retrieved["matched"],
        # Read structurally from the roster — never sniffed out of the prose.
        "profile": {
            "tier": profile.tier,
            "contact": profile.contact,
            "risk_level": profile.risk_level,
            "terms": profile.terms,
            "is_hero": profile.is_hero,
            "max_autonomous_stage": profile.max_autonomous_stage,
            "discount_authority_pct": profile.discount_authority_pct,
            "allow_payment_plan": profile.allow_payment_plan,
            "requires_split_billing": profile.requires_split_billing,
            "escalation_patience_days": profile.escalation_patience_days,
            "relationship_value": profile.relationship_value,
            "guardrails": list(profile.guardrails),
            "history_summary": (
                retrieved["context"].strip().splitlines()[0].strip("- ")
                if retrieved["context"] else "No history on file."
            ),
        },
    }


@router.get("/api/clients/roster")
async def get_client_roster():
    """The hero roster itself, so the frontend never hardcodes client names."""
    return {"clients": [profile_as_dict(p) for p in HERO_CLIENTS]}

@router.get("/api/clients")
async def get_clients(hero: bool = False, db: AsyncSession = Depends(get_db)):
    # Aggregate in Python rather than SQL: the roster is small and this stays
    # portable across Postgres and SQLite.
    all_invs = await db.execute(select(Invoice))
    invs = all_invs.scalars().all()

    c_map = {}
    for inv in invs:
        c = inv.client_name
        if c not in c_map:
            # Identity and policy come from the roster, not from hardcoded
            # overrides that named clients which never existed in the database.
            profile = get_profile(c)
            c_map[c] = {
                "name": c,
                "invoice_count": 0,
                "total_amount": 0,
                "recovered_amount": 0,
                "risk_level": profile.risk_level,
                "tier": profile.tier,
                "terms": profile.terms,
                "contact": profile.contact,
                "is_hero": profile.is_hero,
                "max_autonomous_stage": profile.max_autonomous_stage,
                "discount_authority_pct": profile.discount_authority_pct,
                "relationship_value": profile.relationship_value,
                "guardrails": list(profile.guardrails),
            }

        c_map[c]["invoice_count"] += 1
        c_map[c]["total_amount"] += float(inv.amount)
        if inv.status == InvoiceStatus.RECOVERED:
            c_map[c]["recovered_amount"] += float(inv.amount)

    clients = list(c_map.values())
    if hero:
        clients = [c for c in clients if c["is_hero"]]

    # Hero clients first, in roster order, so the four written profiles are the
    # four cards the demo shows — not whichever Faker names happened to sort first.
    hero_order = {p.name: i for i, p in enumerate(HERO_CLIENTS)}
    clients.sort(key=lambda c: (hero_order.get(c["name"], len(hero_order)), c["name"]))

    return {"clients": clients}

@router.get("/api/compliance/stats")
async def get_compliance_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).where(AuditLog.compliance_verdict != None))
    logs = result.scalars().all()

    passed = sum(1 for l in logs if l.compliance_verdict == "PASS")
    failed = sum(1 for l in logs if l.compliance_verdict == "FAIL")
    # A draft that went out without a review is neither a pass nor a fail. Counting
    # it either way would misstate the rate.
    unreviewed = sum(1 for l in logs if l.compliance_verdict == "UNREVIEWED")
    deterministic = sum(1 for l in logs if l.verdict_source == "deterministic")

    # The rate is over genuine verdicts only: PASS + FAIL.
    total_checked = passed + failed
    # None, not 100.0. An empty database is not a perfect compliance record, and
    # the gauge previously showed a green 100% before a single draft existed.
    rate = (passed / total_checked * 100) if total_checked > 0 else None

    return {
        "total_checked": total_checked,
        "passed": passed,
        "failed": failed,
        "unreviewed": unreviewed,
        # How many of the verdicts came from DEMO_FAST scaffolding rather than a
        # model, so the UI can avoid presenting scaffolding as agent performance.
        "deterministic": deterministic,
        "rate": rate,
    }

@router.get("/api/compliance/rejected")
async def get_compliance_rejected(db: AsyncSession = Depends(get_db)):
    # UNREVIEWED belongs here too: a draft that went out unchecked is exactly the
    # thing a compliance reviewer needs to see, and it was previously invisible.
    result = await db.execute(
        select(AuditLog, Invoice.client_name)
        .join(Invoice, AuditLog.invoice_id == Invoice.id)
        .where(AuditLog.compliance_verdict.in_(["FAIL", "UNREVIEWED"]))
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
    )
    rows = result.all()

    # Resolving the approved rewrite needs the surrounding trail, but only for the
    # invoices actually listed. This previously loaded every audit row in the
    # database into memory on every request.
    invoice_ids = {audit.invoice_id for audit, _ in rows}
    all_logs = []
    if invoice_ids:
        all_logs = (await db.execute(
            select(AuditLog)
            .where(AuditLog.invoice_id.in_(invoice_ids))
            .where(AuditLog.event_type.in_(["EMAIL_SENT", "COMPLIANCE_PASSED"]))
            .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
        )).scalars().all()

    rejected = []
    for audit, client_name in rows:
        # Find the next EMAIL_SENT or COMPLIANCE_PASSED log for this invoice.
        # Compare (timestamp, id): a rejection and its approved rewrite happen in
        # the same tick, so timestamp alone never orders them.
        # An UNREVIEWED row has no rewrite — nothing was rejected, so nothing was
        # redrafted. Only a FAIL can have an approved successor.
        approved_content = None
        if audit.compliance_verdict == "FAIL":
            for log in all_logs:
                if log.invoice_id == audit.invoice_id and (log.timestamp, log.id) > (audit.timestamp, audit.id):
                    if log.content_snapshot:
                        approved_content = log.content_snapshot
                        break

        rejected.append({
            "id": audit.id,
            "invoice_id": audit.invoice_id,
            "client_name": client_name,
            "timestamp": audit.timestamp.isoformat(),
            "event_type": audit.event_type,
            "agent_reasoning": audit.agent_reasoning,
            "action_taken": audit.action_taken,
            "rule_applied": audit.rule_applied,
            "content_snapshot": audit.content_snapshot,
            "compliance_verdict": audit.compliance_verdict,
            "verdict_source": audit.verdict_source,
            "approved_content": approved_content,
        })

    return {"rejected": rejected}


# Events that describe what happened *after* a decision was taken.
_OUTCOME_EVENTS = {
    "EMAIL_SENT", "AGENT_WAIT", "CHANNEL_SWITCHED", "PAYMENT_RECEIVED",
    "NO_RESPONSE", "INTENT_CLASSIFIED", "STATUS_CHANGED", "HUMAN_ESCALATED",
    "RELATIONSHIP_DAMAGED", "PTP_BROKEN",
}


@router.get("/api/invoices/{invoice_id}/decisions")
async def get_decision_explorer(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """
    Every decision point for one invoice, reconstructed from the audit trail.

    A decision point is: what the agent considered, what it chose and why, what
    the policy guard said about it, which tools ran, and what actually happened
    afterwards. The audit trail already records all of this; it was only ever
    rendered as a flat list, so the causal chain was invisible.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")

    logs = (await db.execute(
        select(AuditLog)
        .where(AuditLog.invoice_id == invoice_id)
        .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
    )).scalars().all()

    decisions = []
    current = None

    def close(node):
        if node:
            decisions.append(node)

    for log in logs:
        if log.event_type == "AGENT_DECISION":
            close(current)
            # content_snapshot carries "Expected outcome: ...\nDecision source: ..."
            expected, source = None, None
            for line in (log.content_snapshot or "").splitlines():
                if line.startswith("Expected outcome:"):
                    expected = line.split(":", 1)[1].strip()
                elif line.startswith("Decision source:"):
                    source = line.split(":", 1)[1].strip()

            current = {
                "timestamp": log.timestamp.isoformat(),
                "chose": log.action_taken,
                "reasoning": log.agent_reasoning,
                # rule_applied holds "Alternatives considered: A, B, C"
                "considered": (log.rule_applied or "").replace("Alternatives considered: ", ""),
                "expected_outcome": expected,
                "source": source,
                "guard": None,
                "tools": [],
                "outcomes": [],
                "compliance": [],
            }
            continue

        if current is None:
            continue

        if log.event_type == "ACTION_VETOED":
            current["guard"] = {
                "rule": log.rule_applied,
                "detail": log.agent_reasoning,
                "substitution": log.action_taken,
            }
        elif log.event_type == "TOOL_CALL":
            current["tools"].append({"call": log.action_taken, "why": log.agent_reasoning})
        elif log.event_type in ("COMPLIANCE_PASSED", "COMPLIANCE_FAILED"):
            current["compliance"].append({
                "verdict": "PASS" if log.event_type == "COMPLIANCE_PASSED" else "FAIL",
                "reason": log.agent_reasoning,
            })
        elif log.event_type in _OUTCOME_EVENTS:
            current["outcomes"].append({
                "event": log.event_type,
                "what": log.action_taken,
                "detail": log.agent_reasoning,
                "rule": log.rule_applied,
            })

    close(current)

    return {
        "invoice_id": invoice.id,
        "client_name": invoice.client_name,
        "amount": float(invoice.amount),
        "status": invoice.status.value,
        "relationship_score": invoice.relationship_score if invoice.relationship_score is not None else 1.0,
        "decision_count": len(decisions),
        "decisions": decisions,
    }
