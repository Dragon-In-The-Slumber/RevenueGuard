from mcp.server.fastmcp import FastMCP
from sqlalchemy.ext.asyncio import AsyncSession
from src.persistence.database import get_db, async_session
from src.persistence.models import Invoice, InvoiceStatus, AuditLog
from sqlalchemy.future import select
from datetime import datetime

from contextlib import asynccontextmanager

mcp = FastMCP("RevenueGuard Internal Tools")

@asynccontextmanager
async def get_session():
    async with async_session() as session:
        yield session

@mcp.tool()
async def get_invoice_details(invoice_id: int) -> dict:
    """Fetch full invoice data by ID."""
    async with get_session() as db:
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            return {"error": "Invoice not found"}
        return {
            "id": invoice.id,
            "amount": invoice.amount,
            "client_name": invoice.client_name,
            "client_email": invoice.client_email,
            "status": invoice.status.value if hasattr(invoice.status, "value") else invoice.status,
            "due_date": invoice.due_date.isoformat(),
            "promised_date": invoice.promised_date.isoformat() if invoice.promised_date else None
        }

@mcp.tool()
async def update_invoice_status(invoice_id: int, new_status: str, reason: str) -> str:
    """Change invoice status and log it."""
    async with get_session() as db:
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            return "Error: Invoice not found"
        
        invoice.status = InvoiceStatus(new_status)
        
        log = AuditLog(
            invoice_id=invoice_id,
            event_type="STATUS_CHANGED",
            agent_reasoning=reason,
            action_taken=f"Status updated to {new_status} via MCP",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        await db.commit()
        return f"Successfully updated invoice {invoice_id} to {new_status}"

@mcp.tool()
async def set_promised_date(invoice_id: int, promised_date: str) -> str:
    """Set the promised payment date for an invoice."""
    async with get_session() as db:
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            return "Error: Invoice not found"
            
        invoice.promised_date = datetime.fromisoformat(promised_date)
        await db.commit()
        return f"Set promised date to {promised_date}"

@mcp.tool()
async def log_audit_event(invoice_id: int, event_type: str, reasoning: str, action: str, rule: str = None) -> str:
    """Write a custom entry to the audit trail."""
    async with get_session() as db:
        log = AuditLog(
            invoice_id=invoice_id,
            event_type=event_type,
            agent_reasoning=reasoning,
            action_taken=action,
            rule_applied=rule,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        await db.commit()
        return "Audit event logged"

@mcp.tool()
async def search_client_context(client_name: str, query: str) -> str:
    """Perform a RAG search in ChromaDB for client context."""
    from src.rag.vector_store import search_client_context as rag_search
    results = await rag_search(client_name, query)
    return str(results)

@mcp.tool()
async def send_email_mock(to: str, subject: str, body: str) -> str:
    """Mock email send for testing."""
    # In a real app, this would use an SMTP server or SendGrid/AWS SES
    print(f"MOCK EMAIL SENT TO: {to}\nSUBJECT: {subject}\nBODY:\n{body}")
    return "Mock email successfully dispatched"

@mcp.tool()
async def notify_slack(channel: str, message: str) -> str:
    """Send a Slack webhook for human escalation."""
    print(f"SLACK NOTIFICATION TO {channel}: {message}")
    return "Slack notification sent"

if __name__ == "__main__":
    mcp.run()
