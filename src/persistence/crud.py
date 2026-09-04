from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from src.persistence.models import Invoice, AuditLog, InvoiceStatus
from faker import Faker
import random
from datetime import datetime, timedelta
from src.rag.seed_data import seed_database

fake = Faker('en_IN') # Using Indian locale for realistic B2B company names

async def generate_fake_invoices(db: AsyncSession, count: int = 100):
    invoices = []
    
    # Seed ChromaDB profiles
    seed_database()
    
    # Probabilities for client profiles
    profiles = ["startup", "SME", "enterprise"]
    
    for _ in range(count):
        profile = random.choices(profiles, weights=[0.3, 0.5, 0.2])[0]
        
        # Randomize amount (₹10,000 to ₹50,00,000)
        if profile == "startup":
            amount = random.randint(10000, 500000)
        elif profile == "SME":
            amount = random.randint(100000, 2000000)
        else:
            amount = random.randint(1000000, 5000000)
            
        client_name = fake.company()
        # Clean up company name for email domain
        domain = client_name.split()[0].lower().replace(",", "").replace(".", "") + ".com"
        client_email = f"finance@{domain}"
        
        # Randomize overdue durations (1 to 60 days)
        days_overdue = random.randint(1, 60)
        due_date = datetime.utcnow() - timedelta(days=days_overdue)
        
        invoice = Invoice(
            amount=amount,
            client_name=client_name,
            client_email=client_email,
            due_date=due_date,
            status=InvoiceStatus.ISSUED # Initial state, core loop will detect it's overdue
        )
        invoices.append(invoice)
        db.add(invoice)
        
    await db.commit()
    
    # We don't return the list of 100 objects fully to avoid memory bloat if count is huge,
    # but for 100 it's fine. We'll just return the count.
    return count

async def get_actionable_invoices(db: AsyncSession):
    # Fetch invoices that are ISSUED (and overdue), OVERDUE, NOTIFIED_1, NOTIFIED_2, NOTIFIED_3, or PAUSED_PTP (if grace period passed)
    # For now, let's fetch anything that is NOT in a terminal state
    terminal_states = [InvoiceStatus.RECOVERED, InvoiceStatus.HUMAN_ESCALATED, InvoiceStatus.LEGAL_HOLD, InvoiceStatus.UNRESPONSIVE, InvoiceStatus.DISPUTE]
    

    
    result = await db.execute(
        select(Invoice).where(Invoice.status.not_in(terminal_states))
    )
    return result.scalars().all()

async def get_invoices_by_client_name(db: AsyncSession, client_name: str):
    result = await db.execute(
        select(Invoice).where(Invoice.client_name == client_name)
    )
    return result.scalars().all()

async def log_audit_event(db: AsyncSession, invoice_id: int, event_type: str, reasoning: str, action: str, timestamp: datetime = None, rule_applied: str = None, content_snapshot: str = None):
    log = AuditLog(
        invoice_id=invoice_id,
        event_type=event_type,
        agent_reasoning=reasoning,
        rule_applied=rule_applied,
        action_taken=action,
        content_snapshot=content_snapshot,
        timestamp=timestamp or datetime.utcnow()
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log

async def get_last_email_date(db: AsyncSession, invoice_id: int):
    result = await db.execute(
        select(AuditLog.timestamp)
        .where(AuditLog.invoice_id == invoice_id)
        .where(AuditLog.event_type == "EMAIL_SENT")
        .order_by(AuditLog.timestamp.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()

async def get_last_audit_event_type(db: AsyncSession, invoice_id: int):
    result = await db.execute(
        select(AuditLog.event_type)
        .where(AuditLog.invoice_id == invoice_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
