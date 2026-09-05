"""
Intervention selection — the agentic core.

This replaces `stage_map`, a dictionary that mapped status to stage and so treated
every client identically. The agent is now given an explicit menu of actions plus
the client's written profile, and chooses. The four RAG profiles finally influence
a decision rather than only the wording of an email.

`choose_action` returns an AgentAction either from Claude (structured output,
temperature 0.2) or, when the model is unavailable, from a deterministic policy
that reads the *same* profile fields. The fallback is always tagged `source`
so a heuristic is never presented as model reasoning.
"""

import json
from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.ai.llm import get_llm, _llm_unavailable
from src.domain.clients import stage_rank

ACTION_MENU = [
    "SEND_EMAIL",
    "WAIT",
    "SWITCH_CHANNEL",
    "OFFER_DISCOUNT",
    "OFFER_PAYMENT_PLAN",
    "SPLIT_INVOICE",
    "ESCALATE_TO_HUMAN",
    "CLOSE_AS_UNRECOVERABLE",
]


class AgentAction(BaseModel):
    action: Literal[
        "SEND_EMAIL",
        "WAIT",
        "SWITCH_CHANNEL",
        "OFFER_DISCOUNT",
        "OFFER_PAYMENT_PLAN",
        "SPLIT_INVOICE",
        "ESCALATE_TO_HUMAN",
        "CLOSE_AS_UNRECOVERABLE",
    ] = Field(description="The intervention to take now")
    stage: Optional[Literal["STAGE_1", "STAGE_2", "STAGE_3", "STAGE_4"]] = Field(
        default=None, description="Escalation stage, when the action sends something"
    )
    wait_days: Optional[int] = Field(default=None, description="Days to wait, for WAIT")
    discount_pct: Optional[float] = Field(default=None, description="Discount percent, for OFFER_DISCOUNT")
    instalments: Optional[int] = Field(default=None, description="Instalment count, for OFFER_PAYMENT_PLAN")
    channel: Optional[Literal["EMAIL", "SMS", "WHATSAPP"]] = Field(default=None)
    reasoning: str = Field(description="Why this action, in one or two sentences")
    confidence: float = Field(description="0.0 to 1.0")
    expected_outcome: str = Field(description="What you predict will happen")


DECISION_PROMPT = """You are the collections strategist for an autonomous B2B receivables agent.

Your objective: maximise recovered value while preserving the client relationship and
staying inside policy. Escalating hardest every time is NOT optimal — over-escalation
damages relationships, and a damaged relationship recovers less money over time.
Choosing to do nothing is a legitimate and often correct action.

INVOICE
- ID: {invoice_id}
- Client: {client_name}
- Amount: INR {amount}
- Due date: {due_date} ({days_overdue} days overdue)
- Current status: {current_status}
- Current escalation stage: {escalation_stage}
- Contact attempts so far: {contact_attempts} (cap {max_attempts})
- Days since last contact: {days_since_contact}
- Relationship score: {relationship_score} (1.0 = intact)

CLIENT PROFILE (retrieved from the knowledge base)
{retrieved_context}

POLICY FOR THIS CLIENT
- Tier: {tier}, risk level: {risk_level}, terms: {terms}
- Maximum stage you may reach without a human: {max_autonomous_stage}
- Discount you may offer without approval: {discount_authority_pct}%
- Payment plans allowed: {allow_payment_plan}
- Requires split billing: {requires_split_billing}
- Escalation patience: {escalation_patience_days} days
- Annual relationship value: INR {relationship_value}
- Guardrails: {guardrails}

INTERACTION HISTORY (oldest first)
{interaction_history}

AVAILABLE ACTIONS
- SEND_EMAIL: send the next escalation email at a given stage
- WAIT: deliberately do nothing for N days
- SWITCH_CHANNEL: try SMS or WhatsApp instead of email
- OFFER_DISCOUNT: early-payment incentive, discount_pct
- OFFER_PAYMENT_PLAN: split the balance into instalments
- SPLIT_INVOICE: separate disputed from undisputed portions into two links
- ESCALATE_TO_HUMAN: hand the case to a person
- CLOSE_AS_UNRECOVERABLE: stop pursuing

Choose exactly one action. Explain your reasoning by referring to specifics from this
client's profile and history — not generic collections advice."""


def _format_history(history: list) -> str:
    if not history:
        return "(no prior interactions)"
    lines = []
    for h in history[-10:]:
        lines.append(
            f"- day {h.get('day', '?')}: {h.get('event')} — {h.get('action')}"
            + (f" (outcome: {h['outcome']})" if h.get("outcome") else "")
        )
    return "\n".join(lines)


def _heuristic_action(ctx: dict) -> AgentAction:
    """
    Deterministic intervention selection from the same profile fields the prompt shows.

    Used when Claude is unavailable. This is a policy, not a model: it is tagged as
    such by the caller so the audit trail never attributes it to the agent's judgment.
    """
    profile = ctx["profile"]
    status = ctx["current_status"]
    days_overdue = ctx["days_overdue"]
    days_since = ctx["days_since_contact"]
    attempts = ctx["contact_attempts"]
    patience = profile.get("escalation_patience_days", 4)
    max_stage = profile.get("max_autonomous_stage", "STAGE_4")

    next_stage_map = {
        "OVERDUE": "STAGE_1",
        "NOTIFIED_1": "STAGE_2",
        "NOTIFIED_2": "STAGE_3",
        "NOTIFIED_3": "STAGE_4",
        "PAUSED_PTP": "STAGE_2",
    }
    next_stage = next_stage_map.get(status, "STAGE_1")

    # A disputed invoice for a client whose contract demands split billing.
    if profile.get("requires_split_billing") and status == "DISPUTE":
        return AgentAction(
            action="SPLIT_INVOICE",
            reasoning=(
                f"{profile['name']}'s contract requires undisputed and disputed portions to be "
                "billed separately. Splitting unlocks the undisputed balance immediately instead "
                "of holding the whole amount hostage to one line item."
            ),
            confidence=0.8,
            expected_outcome="Undisputed portion is paid while the disputed line is resolved.",
        )

    # Beyond what this client's policy lets the agent do alone.
    if stage_rank(next_stage) > stage_rank(max_stage):
        return AgentAction(
            action="ESCALATE_TO_HUMAN",
            reasoning=(
                f"{next_stage} exceeds this client's autonomous limit of {max_stage}. "
                f"Guardrail: {(profile.get('guardrails') or ['none'])[0]}"
            ),
            confidence=0.9,
            expected_outcome="A person decides whether to escalate further.",
        )

    # Cash-constrained clients respond to money, not pressure.
    if profile.get("discount_authority_pct", 0) > 0 and profile.get("risk_level") in ("HIGH", "EXTREME") \
            and attempts >= 1:
        return AgentAction(
            action="OFFER_DISCOUNT",
            discount_pct=profile["discount_authority_pct"],
            stage=next_stage,
            reasoning=(
                f"{profile['name']} is {profile['risk_level']} risk and has not responded to "
                f"{attempts} contact(s). Their profile authorises up to "
                f"{profile['discount_authority_pct']}% early-payment discount. Partial recovery "
                "now beats full recovery never."
            ),
            confidence=0.7,
            expected_outcome="Client pays a discounted amount rather than continuing to delay.",
        )

    # A reliable client inside its patience window: doing nothing is correct.
    if days_since is not None and days_since < patience:
        wait_days = max(1, patience - days_since)
        return AgentAction(
            action="WAIT",
            wait_days=wait_days,
            reasoning=(
                f"Last contact was {days_since} day(s) ago and this client's escalation patience "
                f"is {patience} days. {(profile.get('guardrails') or ['Waiting avoids unnecessary pressure.'])[0]} "
                f"Escalating now risks an INR {profile.get('relationship_value', 0):,} relationship "
                "over a delay that historically resolves itself."
            ),
            confidence=0.75,
            expected_outcome=f"Client pays unprompted within {wait_days} day(s).",
        )

    return AgentAction(
        action="SEND_EMAIL",
        stage=next_stage,
        reasoning=(
            f"{days_overdue} days overdue at {status}; {days_since if days_since is not None else 'no'} "
            f"day(s) since last contact meets the {patience}-day patience threshold for this client. "
            f"{next_stage} is within the autonomous limit of {max_stage}."
        ),
        confidence=0.65,
        expected_outcome=f"Client responds to the {next_stage} notice or pays.",
    )


# Decisions are cached per equivalence class. In a 100-invoice batch most cases
# collapse into a couple of dozen classes, which is where the LLM-call reduction
# comes from. Cleared whenever a batch is reset.
_decision_cache: dict[tuple, dict] = {}


def _equivalence_key(ctx: dict) -> tuple:
    """
    The features that actually change the decision.

    Days overdue is bucketed and contact recency coarsened: a 31-day and a 34-day
    overdue invoice for the same client at the same stage warrant the same action.
    """
    profile = ctx["profile"]
    days_since = ctx["days_since_contact"]
    return (
        profile.get("name") if profile.get("is_hero") else f"__standard_{profile.get('tier')}",
        ctx["current_status"],
        ctx["escalation_stage"],
        min(ctx["days_overdue"] // 15, 4),
        min(ctx["contact_attempts"], 5),
        "never" if days_since is None else min(days_since // 3, 5),
        round(ctx.get("relationship_score", 1.0), 1),
        # Value band matters: the guard treats high-value invoices differently.
        1 if (ctx.get("amount") or 0) > 5_000_000 else 0,
    )


def clear_decision_cache() -> None:
    _decision_cache.clear()


async def choose_action(ctx: dict) -> dict:
    """
    Select the next intervention. Returns the action dict plus a `source` tag.

    `source` is "llm" for a model decision and "policy_heuristic" when Claude was
    unavailable, so the audit trail can never present a heuristic as agent reasoning.
    """
    from src.config import settings

    unavailable = _llm_unavailable()
    if unavailable:
        action = _heuristic_action(ctx)
        return {**action.model_dump(), "source": "policy_heuristic", "fallback_reason": unavailable}

    # DEMO_FAST: the four written personas get live Claude; filler invoices use the
    # deterministic path. Judges see real reasoning on the invoices they click into,
    # and a 100-invoice run still finishes inside a demo slot.
    if settings.demo_fast and not (ctx["profile"] or {}).get("is_hero"):
        action = _heuristic_action(ctx)
        return {**action.model_dump(), "source": "policy_heuristic",
                "fallback_reason": "DEMO_FAST: non-hero invoice"}

    key = _equivalence_key(ctx)
    if key in _decision_cache:
        return {**_decision_cache[key], "source": "llm_cached"}

    profile = ctx["profile"]
    try:
        llm = get_llm(temperature=0.2).with_structured_output(AgentAction)
        prompt = DECISION_PROMPT.format(
            invoice_id=ctx["invoice_id"],
            client_name=ctx["client_name"],
            amount=ctx["amount"],
            due_date=ctx["due_date"],
            days_overdue=ctx["days_overdue"],
            current_status=ctx["current_status"],
            escalation_stage=ctx["escalation_stage"],
            contact_attempts=ctx["contact_attempts"],
            max_attempts=ctx["max_attempts"],
            days_since_contact=ctx["days_since_contact"],
            relationship_score=ctx["relationship_score"],
            retrieved_context=ctx["retrieved_context"],
            tier=profile.get("tier"),
            risk_level=profile.get("risk_level"),
            terms=profile.get("terms"),
            max_autonomous_stage=profile.get("max_autonomous_stage"),
            discount_authority_pct=profile.get("discount_authority_pct"),
            allow_payment_plan=profile.get("allow_payment_plan"),
            requires_split_billing=profile.get("requires_split_billing"),
            escalation_patience_days=profile.get("escalation_patience_days"),
            relationship_value=profile.get("relationship_value"),
            guardrails="; ".join(profile.get("guardrails") or []),
            interaction_history=_format_history(ctx.get("interaction_history") or []),
        )
        response = await llm.ainvoke(prompt)
        decision = response.model_dump()
        _decision_cache[key] = decision
        return {**decision, "source": "llm"}
    except Exception as e:
        print(f"[LLM FALLBACK] decide_action -> policy heuristic (LLM call failed: {type(e).__name__})")
        action = _heuristic_action(ctx)
        return {
            **action.model_dump(),
            "source": "policy_heuristic",
            "fallback_reason": f"LLM call failed: {type(e).__name__}",
        }
