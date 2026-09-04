from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
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
        .order_by(AuditLog.timestamp.asc())
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
        .order_by(AuditLog.timestamp.desc())
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

@router.get("/api/invoices")
async def get_all_invoices(status: str = None, db: AsyncSession = Depends(get_db)):
    query = select(Invoice)
    if status:
        query = query.where(Invoice.status == InvoiceStatus(status))
    query = query.order_by(Invoice.due_date.desc())
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    return {"invoices": [{
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
    } for inv in invoices]}

from fastapi import HTTPException
from src.rag.vector_store import search_client_context

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
    # Call the actual ChromaDB RAG function
    context = await search_client_context(name, "contract terms payment history risk")
    
    # Infer some mock profile data from the raw context string
    risk = "LOW"
    if "EXACT MATCH" not in context:
        risk = "HIGH"
        
    return {
        "context": context,
        "profile": {
            "tier": "Enterprise",
            "contact": "Finance Team",
            "risk_level": risk,
            "terms": "Net-30",
            "history_summary": "Usually pays on time"
        }
    }

@router.get("/api/clients")
async def get_clients(db: AsyncSession = Depends(get_db)):
    # Group invoices by client
    result = await db.execute(
        select(
            Invoice.client_name,
            func.count(Invoice.id),
            func.sum(Invoice.amount),
            func.sum(
                func.cast(Invoice.status == InvoiceStatus.RECOVERED, db.bind.dialect.type_compiler.process(func.cast(1, db.bind.dialect.type_compiler.process(db.bind.dialect.type_compiler.process(db.bind.dialect.type_compiler.process))))).cast(db.bind.dialect.type_compiler.process) 
                # Actually, in SQLite, sum(case when status='RECOVERED' then amount else 0 end) is better
            )
        ).group_by(Invoice.client_name)
    )
    
    # Better query for SQLite/Postgres compatibility
    clients = []
    
    # Let's just fetch all and aggregate in Python for safety/simplicity in this demo
    all_invs = await db.execute(select(Invoice))
    invs = all_invs.scalars().all()
    
    c_map = {}
    for inv in invs:
        c = inv.client_name
        if c not in c_map:
            c_map[c] = {
                "name": c, 
                "invoice_count": 0, 
                "total_amount": 0, 
                "recovered_amount": 0, 
                "risk_level": "LOW",
                "tier": "Standard",
                "terms": "Net-30",
                "contact": "billing@company.com"
            }
        
        c_map[c]["invoice_count"] += 1
        c_map[c]["total_amount"] += float(inv.amount)
        if inv.status == InvoiceStatus.RECOVERED:
            c_map[c]["recovered_amount"] += float(inv.amount)
            
    # Hardcode some risk levels and details based on hero clients for demo realism
    for c, data in c_map.items():
        if c == "Acme Corp": 
            data.update({"risk_level": "LOW", "tier": "Enterprise", "terms": "Net-30", "contact": "finance@acmecorp.com"})
        elif c == "Globex Solutions": 
            data.update({"risk_level": "MEDIUM", "tier": "Mid-Market", "terms": "Net-45", "contact": "ap@globex.com"})
        elif c == "Initech": 
            data.update({"risk_level": "HIGH", "tier": "Enterprise", "terms": "Net-60", "contact": "lumbergh@initech.com"})
        elif c == "Soylent Corp": 
            data.update({"risk_level": "EXTREME", "tier": "SMB", "terms": "Net-15", "contact": "admin@soylent.com"})

    return {"clients": list(c_map.values())}

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
    all_logs_result = await db.execute(select(AuditLog).order_by(AuditLog.timestamp))
    all_logs = all_logs_result.scalars().all()
    
    result = await db.execute(
        select(AuditLog, Invoice.client_name)
        .join(Invoice, AuditLog.invoice_id == Invoice.id)
        .where(AuditLog.compliance_verdict == "FAIL")
        .order_by(AuditLog.timestamp.desc())
    )
    
    rejected = []
    for audit, client_name in result:
        # Find the next EMAIL_SENT or COMPLIANCE_PASSED log for this invoice
        approved_content = None
        for log in all_logs:
            if log.invoice_id == audit.invoice_id and log.timestamp > audit.timestamp:
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
