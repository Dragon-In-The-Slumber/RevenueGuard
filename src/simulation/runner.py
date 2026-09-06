"""
Reproducible full-simulation runs, for the agent-vs-baseline comparison.

The claim this exists to support: "same seed, same 100 invoices, two policies —
the agent recovers X%, a fixed ladder recovers Y%." That is only a controlled
comparison if the portfolio and the environment's dice are identical across both
runs, which is what `seed` guarantees.
"""

from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.agent_policy import clear_decision_cache
from src.engine.core_loop import process_simulation_tick
from src.persistence.crud import clear_all_data, generate_fake_invoices
from src.persistence.models import AuditLog, Invoice, InvoiceStatus, WebhookEvent


async def reset_world(db: AsyncSession) -> None:
    """Clear every row so a run starts from an identical blank slate."""
    # Shares one FK-safe implementation with the reset endpoint; this used to be
    # a second hand-maintained delete list that could drift out of step.
    await clear_all_data(db)


async def collect_metrics(db: AsyncSession, policy: str, seed: int,
                          start_date: datetime, days: int) -> dict:
    """Everything needed to argue the result, not just the headline number."""
    invoices = (await db.execute(select(Invoice))).scalars().all()

    total_value = sum(i.amount for i in invoices)
    recovered = [i for i in invoices if i.status == InvoiceStatus.RECOVERED]
    recovered_value = sum(i.amount for i in recovered)

    async def count_event(event_type: str) -> int:
        r = await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.event_type == event_type)
        )
        return r.scalar() or 0

    # Days-to-recovery, measured on the virtual clock.
    recovery_days = []
    if recovered:
        rows = await db.execute(
            select(AuditLog.invoice_id, func.min(AuditLog.timestamp))
            .where(AuditLog.event_type == "PAYMENT_RECEIVED")
            .group_by(AuditLog.invoice_id)
        )
        for _, ts in rows:
            if ts:
                recovery_days.append(max(0, (ts - start_date).days))

    status_counts = {}
    for inv in invoices:
        key = inv.status.value if hasattr(inv.status, "value") else str(inv.status)
        status_counts[key] = status_counts.get(key, 0) + 1

    damaged = [i for i in invoices if (i.relationship_score or 1.0) < 1.0]

    return {
        "policy": policy,
        "seed": seed,
        "days": days,
        "invoices": len(invoices),
        "portfolio_value": round(total_value, 2),
        "recovered_count": len(recovered),
        "recovered_value": round(recovered_value, 2),
        "recovery_rate_pct": round(100 * recovered_value / total_value, 2) if total_value else 0.0,
        "avg_days_to_recovery": round(sum(recovery_days) / len(recovery_days), 1) if recovery_days else None,
        "emails_sent": await count_event("EMAIL_SENT"),
        "human_escalations": await count_event("HUMAN_ESCALATED"),
        "compliance_vetoes": await count_event("ACTION_VETOED"),
        "compliance_failures": await count_event("COMPLIANCE_FAILED"),
        "escalations_self_blocked": await count_event("ESCALATION_BLOCKED"),
        "deliberate_waits": await count_event("AGENT_WAIT"),
        "relationship_damage_incidents": await count_event("RELATIONSHIP_DAMAGED"),
        "clients_with_damaged_relationship": len(damaged),
        "avg_relationship_score": (
            round(sum(i.relationship_score or 1.0 for i in invoices) / len(invoices), 3)
            if invoices else 1.0
        ),
        "status_breakdown": status_counts,
    }


async def run_simulation(db: AsyncSession, policy: str, seed: int,
                         count: int, days: int) -> dict:
    """
    Run one full simulation from a blank slate and return its metrics.

    The decision cache is cleared between runs so the second policy cannot inherit
    decisions made under the first.
    """
    clear_decision_cache()
    await reset_world(db)

    # A fixed start date, so both arms of an A/B see identical due dates and the
    # same number of days overdue on day one.
    start_date = datetime(2026, 1, 1)
    await generate_fake_invoices(db, count, seed=seed, reference_date=start_date)

    virtual_date = start_date
    for _ in range(days):
        virtual_date += timedelta(days=1)
        await process_simulation_tick(db, virtual_date, sim_seed=seed, policy=policy)

    return await collect_metrics(db, policy, seed, start_date, days)


def compare(agent: dict, ladder: dict) -> dict:
    """The headline deltas, so the comparison does not have to be eyeballed."""
    def delta(key):
        a, l = agent.get(key), ladder.get(key)
        if a is None or l is None:
            return None
        return round(a - l, 2)

    return {
        "recovery_rate_delta_pct": delta("recovery_rate_pct"),
        "recovered_value_delta": delta("recovered_value"),
        "emails_delta": delta("emails_sent"),
        "relationship_damage_delta": delta("relationship_damage_incidents"),
        "days_to_recovery_delta": delta("avg_days_to_recovery"),
        "verdict": (
            "agent outperforms the fixed ladder"
            if (delta("recovery_rate_pct") or 0) > 0
            else "fixed ladder matched or beat the agent"
        ),
    }
