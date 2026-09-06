"""
Compliance judge behaviour, including the Phase A change that stopped an
unreachable judge from being recorded as an approved draft.
"""
import pytest

from src.ai.compliance_judge import evaluate_email_compliance

DRAFT = "Dear Acme Corp, your invoice is overdue. Pay here: https://rzp.io/l/x"


async def test_deterministic_fallback_returns_a_verdict_when_llm_is_unavailable(no_llm):
    """
    Provider-agnostic. This test used to blank ANTHROPIC_API_KEY to force the
    fallback, which stopped working the moment the client became provider-aware:
    clearing the Anthropic key does nothing when the active provider is Google.
    """
    result = await evaluate_email_compliance("test email", "STAGE_1")
    assert result["verdict"] in ("PASS", "FAIL")
    # Scaffolding must never be mistaken for a real review.
    assert result["source"] == "deterministic"


async def test_judge_outage_is_unreviewed_not_pass(monkeypatch):
    """
    The correctness fix. Returning PASS on an API error made an outage
    indistinguishable from an approved draft, and the compliance gauge read 100%
    while nothing had been reviewed.
    """
    monkeypatch.setattr("src.ai.compliance_judge._llm_unavailable", lambda client_name=None: None)

    class _Exploding:
        async def ainvoke(self, _):
            raise RuntimeError("judge is down")

    class _Chain:
        def __or__(self, other):
            return _Exploding()

    monkeypatch.setattr("src.ai.compliance_judge.get_llm", lambda **kw: _Exploding())
    monkeypatch.setattr(
        "src.ai.compliance_judge.ChatPromptTemplate.from_messages",
        classmethod(lambda cls, msgs: _Chain()),
    )

    result = await evaluate_email_compliance(DRAFT, "STAGE_1")
    assert result["verdict"] == "UNREVIEWED"
    assert result["source"] == "unavailable"
    assert "judge is down" in result["reason"]


async def test_unreviewed_does_not_enter_the_rewrite_loop():
    """
    There is no feedback to rewrite against, so looping would burn both retries
    and escalate to a human for an outage that is not the draft's fault.
    """
    from src.graph.edges import route_after_compliance
    assert route_after_compliance({"compliance_verdict": "UNREVIEWED"}) == "call_razorpay_tools"
    assert route_after_compliance({"compliance_verdict": "PASS"}) == "call_razorpay_tools"
    assert route_after_compliance({"compliance_verdict": "FAIL", "compliance_retries": 0}) == "draft_email"


async def test_no_draft_is_recorded_as_no_verdict_not_a_pass(no_llm):
    """An unsent draft is not a passed compliance check."""
    from src.graph.nodes import evaluate_compliance
    state = {"drafted_email": None, "should_send_email": False, "audit_entries": []}
    out = await evaluate_compliance(state)
    assert out["compliance_verdict"] is None
    assert out["audit_entries"] == []
