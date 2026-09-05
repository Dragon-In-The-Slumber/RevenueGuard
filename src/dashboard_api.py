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
    
    total = len(logs)
    passed = sum(1 for l in logs if l.compliance_verdict == "PASS")
    failed = sum(1 for l in logs if l.compliance_verdict == "FAIL")
    rate = (passed / total * 100) if total > 0 else 100.0
    
    return {
        "total_checked": total,
        "passed": passed,
        "failed": failed,
        "rate": rate
    }

@router.get("/api/compliance/rejected")
async def get_compliance_rejected(db: AsyncSession = Depends(get_db)):
    # Get all logs for context
    all_logs_result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
    )
    all_logs = all_logs_result.scalars().all()

    result = await db.execute(
        select(AuditLog, Invoice.client_name)
        .join(Invoice, AuditLog.invoice_id == Invoice.id)
        .where(AuditLog.compliance_verdict == "FAIL")
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
    )

    rejected = []
    for audit, client_name in result:
        # Find the next EMAIL_SENT or COMPLIANCE_PASSED log for this invoice.
        # Compare (timestamp, id): a rejection and its approved rewrite happen in
        # the same tick, so timestamp alone never orders them.
        approved_content = None
        for log in all_logs:
            if log.invoice_id == audit.invoice_id and (log.timestamp, log.id) > (audit.timestamp, audit.id):
                if log.event_type in ["EMAIL_SENT", "COMPLIANCE_PASSED"] and log.content_snapshot:
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
            "approved_content": approved_content
        })
        
    return {"rejected": rejected}
