"""One test per mandated stopping rule (D-14).

Each asserts both the resulting status and the audit row that proves why, since
the rule being *recorded* is what the compliance story rests on.
"""
from datetime import datetime

import pytest

from src.engine.core_loop import build_recovery_state
from src.graph.nodes import (
    MAX_CONTACT_ATTEMPTS, check_stop_conditions, classify_reply, draft_email,
)
from tests.conftest import make_invoice

VDATE = datetime(2026, 2, 1)


def state_for(invoice, **extra):
    s = build_recovery_state(invoice, VDATE, None, **extra)
    s.setdefault("client_profile", {"max_autonomous_stage": "STAGE_4", "guardrails": []})
    return s


def rules(state):
    return [e.get("rule") for e in state["audit_entries"]]


async def test_stop1_payment_marks_recovered_and_halts(no_llm):
    """Stop 1 — a paid invoice is terminal and must never be contacted again."""
    s = state_for(make_invoice(status="RECOVERED"))
    s = await check_stop_conditions(s)
    assert s["stop_reason"]
    assert any("Terminal status halts all contact" in (r or "") for r in rules(s))


async def test_stop2_promise_is_honoured_inside_the_window(no_llm):
    """Stop 2 — inside promised_date + grace the agent must hold off."""
    s = state_for(make_invoice(status="PAUSED_PTP", promised_date=datetime(2026, 2, 10)))
    s = await check_stop_conditions(s)
    assert s["stop_reason"]
    entry = next(e for e in s["audit_entries"] if e["event_type"] == "PTP_HONOURED")
    assert "Honour Promise-to-Pay" in entry["rule"]


async def test_stop2_releases_once_the_promise_lapses(no_llm):
    """...and resumes once the date has passed, otherwise it would never chase."""
    s = state_for(make_invoice(status="PAUSED_PTP", promised_date=datetime(2026, 1, 5)))
    s = await check_stop_conditions(s)
    assert s["stop_reason"] is None
    assert s["audit_entries"] == []


async def test_stop3_dispute_halts_and_routes_to_human(no_llm):
    """Stop 3 — a dispute stops automated collection and notifies a person."""
    s = state_for(make_invoice(status="NOTIFIED_1"))
    s["client_reply"] = "This amount is incorrect, we are disputing this invoice."
    s = await classify_reply(s)
    assert s["new_status"] == "DISPUTE"
    assert s["notify_payload"]["reason"] == "DISPUTE"
    assert any("Stop 3" in (r or "") for r in rules(s))


@pytest.mark.parametrize("reply,expected", [
    ("Please stop contacting us about this matter", "OPT_OUT"),
    ("Our attorney will be in touch regarding this", "LEGAL_THREAT"),
])
async def test_stop4_optout_and_legal_threat_set_legal_hold(no_llm, reply, expected):
    """Stop 4 — LEGAL_HOLD was unreachable before; both routes must now reach it."""
    s = state_for(make_invoice(status="NOTIFIED_2"))
    s["client_reply"] = reply
    s = await classify_reply(s)
    assert s["classified_intent"] == expected
    assert s["new_status"] == "LEGAL_HOLD"
    assert any("Stop 4" in (r or "") for r in rules(s))


async def test_stop5_attempt_cap_marks_unresponsive(no_llm):
    """Stop 5 — the hard cap, enforced before anything is drafted."""
    s = state_for(make_invoice(status="NOTIFIED_2", contact_attempts=MAX_CONTACT_ATTEMPTS))
    s = await check_stop_conditions(s)
    assert s["new_status"] == "UNRESPONSIVE"
    assert any("Stop 5" in (r or "") for r in rules(s))


async def test_stop5_ghost_through_the_ladder_is_unresponsive(no_llm):
    """A client who never replied is a ghost, not a draft awaiting approval."""
    s = state_for(make_invoice(status="NOTIFIED_3", contact_attempts=3), client_replies=0)
    s["client_profile"] = {"max_autonomous_stage": "STAGE_4", "guardrails": []}
    s = await draft_email(s)
    assert s["new_status"] == "UNRESPONSIVE"


async def test_engaged_client_at_stage4_goes_to_human_not_unresponsive(no_llm):
    """The counterpart: a client who did reply gets the STAGE_4 approval gate."""
    s = state_for(make_invoice(status="NOTIFIED_3", contact_attempts=3), client_replies=2)
    s["client_profile"] = {"max_autonomous_stage": "STAGE_4", "guardrails": []}
    s = await draft_email(s)
    assert s["new_status"] == "HUMAN_ESCALATED"
