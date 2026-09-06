from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, func
from sqlalchemy import delete
from src.persistence.models import Base, Invoice, AuditLog, InvoiceStatus
from faker import Faker
import random
from datetime import datetime, timedelta
from src.domain.clients import HERO_CLIENTS

fake = Faker('en_IN') # Using Indian locale for realistic B2B company names

async def generate_fake_invoices(db: AsyncSession, count: int = 100,
                                 seed: int | None = None,
                                 reference_date: datetime | None = None):
    """
    Generate a batch of overdue invoices.

    `seed` and `reference_date` make the portfolio reproducible, which is what
    lets the A/B compare two policies over an identical set of invoices rather
    than two different random ones.
    """
    invoices = []

    rng = random.Random(seed) if seed is not None else random
    if seed is not None:
        Faker.seed(seed)
    now = reference_date or datetime.utcnow()

    # ChromaDB profiles are seeded on startup in main.py lifespan,
    # so we don't need to do it here which causes a 36-second API blocking timeout!

    # Hero clients come from src/domain/clients.py — the same roster that seeds
    # ChromaDB and serves /api/clients, so the three cannot disagree.
    num_heroes = min(count, len(HERO_CLIENTS))
    for i in range(num_heroes):
        hero = HERO_CLIENTS[i]
        due_date = now - timedelta(days=hero.seed_days_overdue)
        invoice = Invoice(
            amount=hero.seed_amount,
            client_name=hero.name,
            client_email=hero.email,
            due_date=due_date,
            status=InvoiceStatus.ISSUED
        )
        invoices.append(invoice)
        db.add(invoice)

    # Probabilities for client profiles
    profiles = ["startup", "SME", "enterprise"]
    
    for _ in range(count - num_heroes):
        profile = rng.choices(profiles, weights=[0.3, 0.5, 0.2])[0]
        
        # Randomize amount (₹10,000 to ₹50,00,000)
        if profile == "startup":
            amount = rng.randint(10000, 500000)
        elif profile == "SME":
            amount = rng.randint(100000, 2000000)
        else:
            amount = rng.randint(1000000, 5000000)
            
        client_name = fake.company()
        # Clean up company name for email domain
        domain = client_name.split()[0].lower().replace(",", "").replace(".", "") + ".com"
        client_email = f"finance@{domain}"
        
        # Randomize overdue durations (1 to 60 days)
        days_overdue = rng.randint(1, 60)
        due_date = now - timedelta(days=days_overdue)
        
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

async def clear_all_data(db: AsyncSession) -> dict:
    """
    Delete every simulation row, in foreign-key-safe order. Commits.

    The order is derived from SQLAlchemy's metadata rather than hand-written.
    Reset used to delete audit_logs then invoices explicitly, which broke the
    moment webhook_events arrived with its own foreign key to invoices — the
    endpoint returned a 500 and the Reset button silently did nothing. Sorting
    the tables by dependency means the next table to be added is handled without
    anyone remembering to update this function.

    Returns {table_name: rows_deleted} so the caller can report what it did.
    """
    deleted = {}
    # sorted_tables is parents-first; deleting children first is the reverse.
    for table in reversed(Base.metadata.sorted_tables):
        result = await db.execute(delete(table))
        deleted[table.name] = result.rowcount or 0
    await db.commit()
    return deleted


async def get_actionable_invoices(db: AsyncSession):
    """
    Invoices the agent may still act on.

    PAUSED_PTP stays actionable on purpose: the graph's stop-condition gate needs
    to see it each tick to decide whether the promise window is still open, and to
    resume once it lapses. The terminal set is where the stopping rules land —
    a case there is finished as far as automation is concerned.
    """
    terminal_states = [
        InvoiceStatus.RECOVERED,         # Stop 1: paid
        InvoiceStatus.DISPUTE,           # Stop 3: halted, with a human notified
        InvoiceStatus.LEGAL_HOLD,        # Stop 4: opt-out / legal threat
        InvoiceStatus.UNRESPONSIVE,      # Stop 5: attempt cap reached
        InvoiceStatus.HUMAN_ESCALATED,
    ]

    result = await db.execute(
        select(Invoice).where(Invoice.status.not_in(terminal_states))
    )
    return result.scalars().all()

async def get_invoices_by_client_name(db: AsyncSession, client_name: str):
    result = await db.execute(
        select(Invoice).where(Invoice.client_name == client_name)
    )
    return result.scalars().all()

def build_audit_log(invoice_id: int, event_type: str, reasoning: str, action: str,
                    timestamp: datetime = None, rule_applied: str = None,
                    content_snapshot: str = None, compliance_verdict: str = None,
                    verdict_source: str = None) -> AuditLog:
    """Construct an AuditLog without touching the session — for batched writes."""
    return AuditLog(
        invoice_id=invoice_id,
        event_type=event_type,
        agent_reasoning=reasoning,
        rule_applied=rule_applied,
        action_taken=action,
        content_snapshot=content_snapshot,
        compliance_verdict=compliance_verdict,
        verdict_source=verdict_source,
        timestamp=timestamp or datetime.utcnow()
    )


async def log_audit_event(db: AsyncSession, invoice_id: int, event_type: str, reasoning: str, action: str, timestamp: datetime = None, rule_applied: str = None, content_snapshot: str = None, compliance_verdict: str = None, verdict_source: str = None):
    """
    Single audit write, committed immediately.

    Kept for the webhook and reply endpoints, which write one row per request. The
    tick loop uses build_audit_log + a single commit instead: committing per row
    inside a per-invoice loop produced hundreds of round trips per tick and left
    the database in a partial state if a tick failed halfway.
    """
    log = build_audit_log(invoice_id, event_type, reasoning, action, timestamp,
                          rule_applied, content_snapshot, compliance_verdict, verdict_source)
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_tick_context(db: AsyncSession, invoice_ids: list[int]) -> dict:
    """
    One query per fact for the whole batch, instead of three per invoice.

    Returns {invoice_id: {"last_email": dt|None, "replies": int, "history": [...]}}.
    """
    ctx = {i: {"last_email": None, "replies": 0, "history": []} for i in invoice_ids}
    if not invoice_ids:
        return ctx

    # Latest EMAIL_SENT per invoice.
    last_emails = await db.execute(
        select(AuditLog.invoice_id, func.max(AuditLog.timestamp))
        .where(AuditLog.invoice_id.in_(invoice_ids))
        .where(AuditLog.event_type == "EMAIL_SENT")
        .group_by(AuditLog.invoice_id)
    )
    for inv_id, ts in last_emails:
        ctx[inv_id]["last_email"] = ts

    # Reply counts per invoice.
    reply_counts = await db.execute(
        select(AuditLog.invoice_id, func.count(AuditLog.id))
        .where(AuditLog.invoice_id.in_(invoice_ids))
        .where(AuditLog.event_type == "INTENT_CLASSIFIED")
        .group_by(AuditLog.invoice_id)
    )
    for inv_id, count in reply_counts:
        ctx[inv_id]["replies"] = count

    # Interaction history for the whole batch in one pass.
    history_rows = await db.execute(
        select(AuditLog)
        .where(AuditLog.invoice_id.in_(invoice_ids))
        .where(AuditLog.event_type.in_([
            "EMAIL_SENT", "AGENT_DECISION", "AGENT_WAIT", "ACTION_VETOED",
            "INTENT_CLASSIFIED", "PAYMENT_RECEIVED", "PTP_HONOURED", "CHANNEL_SWITCHED",
        ]))
        .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
    )
    for log in history_rows.scalars().all():
        entries = ctx[log.invoice_id]["history"]
        if len(entries) < 20:
            entries.append({
                "day": log.timestamp.date().isoformat() if log.timestamp else None,
                "event": log.event_type,
                "action": log.action_taken,
                "outcome": log.agent_reasoning,
            })
    return ctx

async def get_last_email_date(db: AsyncSession, invoice_id: int):
    result = await db.execute(
        select(AuditLog.timestamp)
        .where(AuditLog.invoice_id == invoice_id)
        .where(AuditLog.event_type == "EMAIL_SENT")
        .order_by(AuditLog.timestamp.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()

async def count_client_replies(db: AsyncSession, invoice_id: int) -> int:
    """
    How many times this client has actually engaged.

    Distinguishes a ghost (Stop 5 -> UNRESPONSIVE) from a client who replied but
    whose case still needs a person (-> HUMAN_ESCALATED). Without this the two are
    indistinguishable and UNRESPONSIVE is unreachable.
    """
    result = await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.invoice_id == invoice_id)
        .where(AuditLog.event_type == "INTENT_CLASSIFIED")
    )
    return result.scalar() or 0


async def get_interaction_history(db: AsyncSession, invoice_id: int, limit: int = 20):
    """
    Prior actions and outcomes for this invoice, oldest first.

    Feeds `decide_action`: an agent choosing an intervention needs to know what has
    already been tried and what it produced.
    """
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.invoice_id == invoice_id)
        .where(AuditLog.event_type.in_([
            "EMAIL_SENT", "AGENT_DECISION", "AGENT_WAIT", "ACTION_VETOED",
            "INTENT_CLASSIFIED", "PAYMENT_RECEIVED", "ESCALATION_BLOCKED",
            "PTP_HONOURED", "CHANNEL_SWITCHED",
        ]))
        .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
        .limit(limit)
    )
    return [
        {
            "day": log.timestamp.date().isoformat() if log.timestamp else None,
            "event": log.event_type,
            "action": log.action_taken,
            "outcome": log.agent_reasoning,
        }
        for log in result.scalars().all()
    ]


async def get_last_audit_event_type(db: AsyncSession, invoice_id: int):
    result = await db.execute(
        select(AuditLog.event_type)
        .where(AuditLog.invoice_id == invoice_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
