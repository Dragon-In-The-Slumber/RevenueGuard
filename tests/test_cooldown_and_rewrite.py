"""Cooldown enforcement, rewrite-loop termination, and reproducibility."""
from datetime import datetime

from src.engine.core_loop import build_recovery_state
from src.graph.edges import route_after_compliance
from src.graph.nodes import check_cooldown, evaluate_compliance
from src.simulation.client_env import derive_rng, invoice_identity, simulate_response
from tests.conftest import make_invoice

VDATE = datetime(2026, 2, 10)


def state_for(invoice, last_email=None):
    return build_recovery_state(invoice, VDATE, last_email)


async def test_cooldown_blocks_a_second_email_in_the_same_window(no_llm):
    s = await check_cooldown(state_for(make_invoice(), last_email=datetime(2026, 2, 8)))
    assert s["should_send_email"] is False


async def test_cooldown_allows_contact_once_four_days_have_passed(no_llm):
    s = await check_cooldown(state_for(make_invoice(), last_email=datetime(2026, 2, 5)))
    assert s["should_send_email"] is True


async def test_never_contacted_invoice_is_not_blocked(no_llm):
    s = await check_cooldown(state_for(make_invoice(), last_email=None))
    assert s["should_send_email"] is True


def test_rewrite_loop_terminates_after_two_retries():
    """A failing judge must not loop forever; retries >= 2 hands off to a human."""
    assert route_after_compliance({"compliance_verdict": "FAIL", "compliance_retries": 0}) == "draft_email"
    assert route_after_compliance({"compliance_verdict": "FAIL", "compliance_retries": 1}) == "draft_email"
    assert route_after_compliance({"compliance_verdict": "FAIL", "compliance_retries": 2}) == "execute_action"
    assert route_after_compliance({"compliance_verdict": "PASS"}) == "call_razorpay_tools"


async def test_compliance_verdict_is_deterministic_for_the_same_draft(no_llm):
    """
    The mock judge used an unseeded 20% coin flip, which made the same seed
    produce a different recovery number on every run.
    """
    body = "Dear Acme Corp, invoice 7 for INR 100000 is overdue. Pay: https://rzp.io/l/x"
    first = await evaluate_compliance_verdict(body)
    for _ in range(5):
        assert await evaluate_compliance_verdict(body) == first


async def evaluate_compliance_verdict(body):
    from src.ai.compliance_judge import evaluate_email_compliance
    result = await evaluate_email_compliance(body, "STAGE_1", "", client_name="Nobody Ltd")
    return result["verdict"]


async def test_compliance_verdict_ignores_the_invoice_id(no_llm):
    """
    Ids are a database autoincrement that climbs on every reset, so a verdict
    keyed on them would differ between two runs of the same seed.
    """
    from src.ai.compliance_judge import evaluate_email_compliance
    a = await evaluate_email_compliance("Invoice 7 for INR 100000 is overdue.", "STAGE_1",
                                        client_name="Nobody Ltd")
    b = await evaluate_email_compliance("Invoice 9917 for INR 100000 is overdue.", "STAGE_1",
                                        client_name="Nobody Ltd")
    assert a["verdict"] == b["verdict"]


def test_environment_rng_is_stable_across_runs():
    """Keyed on identity, not the primary key, so a reset does not change dice."""
    s = {"client_name": "Acme Corp", "amount": 1250000.0, "due_date": "2026-01-01T00:00:00"}
    ident = invoice_identity(s)
    assert derive_rng(42, ident, "2026-02-01").random() == derive_rng(42, ident, "2026-02-01").random()
    assert derive_rng(42, ident, "2026-02-01").random() != derive_rng(7, ident, "2026-02-01").random()


def test_the_action_the_agent_chose_changes_the_outcome_probability():
    """
    If p(pay) did not depend on the action, the agent's judgment could not affect
    the result and the A/B would be meaningless.
    """
    base = {
        "invoice_id": 1, "client_name": "NovaTech Labs", "amount": 80000.0,
        "due_date": "2026-01-01T00:00:00", "virtual_date": "2026-02-01T00:00:00",
        "escalation_stage": "STAGE_2", "relationship_score": 1.0,
    }
    email = simulate_response({**base, "effective_action": {"action": "SEND_EMAIL"}}, 42)
    discount = simulate_response(
        {**base, "effective_action": {"action": "OFFER_DISCOUNT", "discount_pct": 10.0}}, 42)
    assert discount["p_pay"] > email["p_pay"]


async def test_reset_clears_every_table_including_foreign_key_children(db):
    """
    Reset deleted audit_logs and invoices from a hand-written list, so it began
    returning 500 the moment webhook_events arrived with its own foreign key to
    invoices — the Reset button silently did nothing. The order now comes from
    SQLAlchemy metadata, so a new table is handled without editing this code.
    """
    from sqlalchemy import func, select

    from src.persistence.crud import clear_all_data
    from src.persistence.models import AuditLog, Invoice, WebhookEvent
    from tests.conftest import make_invoice

    invoice = make_invoice()
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)

    db.add(AuditLog(invoice_id=invoice.id, event_type="EMAIL_SENT", action_taken="sent"))
    db.add(WebhookEvent(event_id="evt_test_1", event_type="invoice.paid", invoice_id=invoice.id))
    await db.commit()

    deleted = await clear_all_data(db)

    assert deleted["webhook_events"] == 1
    assert deleted["invoices"] == 1
    for model in (WebhookEvent, AuditLog, Invoice):
        remaining = (await db.execute(select(func.count()).select_from(model))).scalar()
        assert remaining == 0, f"{model.__tablename__} still has rows"


async def test_reset_is_idempotent_on_an_empty_database(db):
    """Resetting twice must not raise; the second call simply deletes nothing."""
    from src.persistence.crud import clear_all_data

    assert sum((await clear_all_data(db)).values()) == 0
    assert sum((await clear_all_data(db)).values()) == 0
