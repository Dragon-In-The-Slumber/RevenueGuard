from src.logging_config import get_logger
import httpx
from src.config import settings
from src.graph.state import RecoveryState
from src.ai.llm import draft_escalation_email, classify_client_intent
from src.rag.vector_store import search_client_context
from src.ai.compliance_judge import evaluate_email_compliance
from src.domain.clients import get_profile, profile_as_dict, stage_rank
from src.ai.agent_policy import choose_action
from src.graph import policy_guard
from src.tools import registry as tools
from src.simulation import client_env
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode
from datetime import datetime, timedelta
import random

# --- Stopping-rule policy ---------------------------------------------------
# Stopping rule 5: outbound contacts allowed before the invoice is written off
# as UNRESPONSIVE and handed to a person.

logger = get_logger("revenueguard.graph")

MAX_CONTACT_ATTEMPTS = 5

# Stopping rule 2: a promise is honoured until its date plus this grace period.
PTP_GRACE_BUSINESS_DAYS = 2

# Statuses from which the agent must never send anything again.
HARD_STOP_STATUSES = {"LEGAL_HOLD", "UNRESPONSIVE", "RECOVERED", "HUMAN_ESCALATED"}

# The full intent -> outcome table. Every intent the classifier can emit appears
# here; previously only PROMISE_TO_PAY and DISPUTE were handled and the other six
# fell through silently, leaving LEGAL_HOLD and UNRESPONSIVE unreachable.
#   new_status  - status to move to, or None to leave unchanged
#   rule        - the governing rule, recorded in the audit row
#   notify      - whether a human must be told
#   halt        - whether the agent stops contacting this client
INTENT_OUTCOMES = {
    "PROMISE_TO_PAY": {
        "new_status": "PAUSED_PTP",
        "rule": "Stop 2: Pause escalation until promised date + grace",
        "action": "Paused workflow until promised date",
        "notify": False,
        "halt": True,
    },
    "NEED_EXTENSION": {
        "new_status": "PAUSED_PTP",
        "rule": "Stop 2: Extension request treated as a dated commitment",
        "action": "Paused workflow pending requested extension",
        "notify": False,
        "halt": True,
    },
    "DISPUTE": {
        "new_status": "DISPUTE",
        "rule": "Stop 3: Halt automated collection on dispute, route to human",
        "action": "Halted and routed to human for dispute resolution",
        "notify": True,
        "halt": True,
    },
    "OPT_OUT": {
        "new_status": "LEGAL_HOLD",
        "rule": "Stop 4: Opt-out is permanent - no further contact",
        "action": "Placed on LEGAL_HOLD, all further contact suppressed",
        "notify": True,
        "halt": True,
    },
    "LEGAL_THREAT": {
        "new_status": "LEGAL_HOLD",
        "rule": "Stop 4: Legal threat halts collection permanently",
        "action": "Placed on LEGAL_HOLD, escalated to legal/human review",
        "notify": True,
        "halt": True,
    },
    "PARTIAL_PAYMENT": {
        "new_status": None,
        "rule": "Partial payment acknowledged; balance remains collectable",
        "action": "Logged partial payment, continuing on the remaining balance",
        "notify": False,
        "halt": False,
    },
    "ACKNOWLEDGMENT": {
        "new_status": None,
        "rule": "Acknowledgement carries no commitment; escalation continues",
        "action": "Logged client acknowledgement",
        "notify": False,
        "halt": False,
    },
    "UNRELATED": {
        "new_status": None,
        "rule": "Reply unrelated to payment; escalation continues",
        "action": "Logged unrelated reply",
        "notify": False,
        "halt": False,
    },
}


def _parse_dt(value):
    """Parse an ISO string from the state; returns None for missing/invalid values."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _add_business_days(start: datetime, days: int) -> datetime:
    """Advance past `days` business days, skipping weekends."""
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current

async def check_overdue(state: RecoveryState) -> RecoveryState:
    if state["current_status"] == "ISSUED" and state["days_overdue"] > 0:
        state["new_status"] = "OVERDUE"
        state["audit_entries"].append({
            "event_type": "STATUS_CHANGED",
            "reasoning": "Due date passed",
            "action": "Marked as OVERDUE",
            "rule": None,
            "content": None
        })
    return state

async def check_stop_conditions(state: RecoveryState) -> RecoveryState:
    """
    Enforces the stopping rules before any outreach is considered.

    Runs after check_overdue and before the cooldown. Sets `stop_reason` when the
    workflow must halt; routing reads that and ends the graph (via notify_human
    where a person needs to be told).
    """
    state["stop_reason"] = None
    status = state.get("new_status") or state["current_status"]
    virtual_now = _parse_dt(state.get("virtual_date")) or datetime.utcnow()

    # Stopping rule 4 (and terminal states generally): never contact again.
    if status in HARD_STOP_STATUSES:
        state["stop_reason"] = f"Invoice is {status}; no further automated contact permitted."
        state["audit_entries"].append({
            "event_type": "STOP_CONDITION",
            "reasoning": state["stop_reason"],
            "action": "Suppressed outreach",
            "rule": "Stop 4: Terminal status halts all contact",
            "content": None,
        })
        return state

    # Stopping rule 2: a promise is honoured until promised_date + grace.
    promised = _parse_dt(state.get("promised_date"))
    if status == "PAUSED_PTP" and promised:
        deadline = _add_business_days(promised, PTP_GRACE_BUSINESS_DAYS)
        if virtual_now <= deadline:
            days_left = (deadline - virtual_now).days
            state["stop_reason"] = (
                f"Promise to pay is still open until {deadline.date().isoformat()}."
            )
            state["audit_entries"].append({
                "event_type": "PTP_HONOURED",
                "reasoning": (
                    f"Client promised payment by {promised.date().isoformat()}; "
                    f"{PTP_GRACE_BUSINESS_DAYS} business days grace runs to "
                    f"{deadline.date().isoformat()} ({days_left} day(s) remaining). "
                    "Chasing now would break our own commitment."
                ),
                "action": "Held escalation inside the promise window",
                "rule": "Stop 2: Honour Promise-to-Pay until promised date + grace",
                "content": None,
            })
            return state

    # Stopping rule 5: too many unanswered contacts.
    if state.get("contact_attempts", 0) >= MAX_CONTACT_ATTEMPTS:
        state["new_status"] = "UNRESPONSIVE"
        state["stop_reason"] = (
            f"{state.get('contact_attempts')} contact attempts with no resolution."
        )
        state["notify_payload"] = {
            "reason": "UNRESPONSIVE",
            "detail": state["stop_reason"],
            "invoice_id": state["invoice_id"],
            "client_name": state["client_name"],
            "amount": state["amount"],
        }
        state["audit_entries"].append({
            "event_type": "STATUS_CHANGED",
            "reasoning": (
                f"Contacted {state.get('contact_attempts')} times "
                f"(cap {MAX_CONTACT_ATTEMPTS}) without resolution."
            ),
            "action": "Marked UNRESPONSIVE and routed to human review",
            "rule": "Stop 5: Max contact attempts reached",
            "content": None,
        })
        return state

    return state


async def notify_human(state: RecoveryState) -> RecoveryState:
    """
    Hands a case to a person.

    Posts to a Slack webhook when one is configured, and always writes the audit
    row so the handoff is provable even without Slack. Fires on DISPUTE,
    LEGAL_HOLD, UNRESPONSIVE and HUMAN_ESCALATED.
    """
    payload = state.get("notify_payload") or {
        "reason": state.get("new_status") or state["current_status"],
        "detail": state.get("stop_reason") or "Case requires human review.",
        "invoice_id": state["invoice_id"],
        "client_name": state["client_name"],
        "amount": state["amount"],
    }

    message = (
        f"[RevenueGuard] Human review needed - {payload['reason']}\n"
        f"Invoice #{payload['invoice_id']} | {payload['client_name']} | "
        f"INR {payload['amount']}\n{payload['detail']}"
    )

    delivered = "console"
    try:
        webhook = getattr(settings, "slack_webhook_url", None)
        if webhook:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(webhook, json={"text": message})
            delivered = "slack"
        else:
            logger.debug(message)
    except Exception as e:
        # A failed notification must not lose the handoff: the audit row below is
        # the durable record, and the failure is named rather than hidden.
        logger.warning(f"notify_human: Slack delivery failed ({e}); logged to console instead")
        logger.debug(message)
        delivered = f"console (slack failed: {type(e).__name__})"

    state["audit_entries"].append({
        "event_type": "HUMAN_ESCALATED",
        "reasoning": payload["detail"],
        "action": f"Notified human via {delivered}",
        "rule": f"Human handoff: {payload['reason']}",
        "content": message,
    })
    return state


async def check_cooldown(state: RecoveryState) -> RecoveryState:
    state["should_send_email"] = True
    
    if state.get("last_email_date"):
        last_dt = datetime.fromisoformat(state["last_email_date"])
        # Use virtual_date if available, otherwise fallback to utcnow
        current_dt = datetime.fromisoformat(state["virtual_date"]) if state.get("virtual_date") else datetime.utcnow()
        if (current_dt - last_dt).days < 4:
            state["should_send_email"] = False
            
    return state

async def log_blocked(state: RecoveryState) -> RecoveryState:
    state["audit_entries"].append({
        "event_type": "ESCALATION_BLOCKED",
        "reasoning": "Cooldown active (4 days).",
        "action": "Blocked escalation",
        "rule": "Max 1 contact per 4 days",
        "content": None
    })
    return state


async def retrieve_client_context(state: RecoveryState) -> RecoveryState:
    # search_client_context returns a joined string, so this interpolates cleanly
    # into prompts instead of leaking a Python list repr.
    context = await search_client_context(state["client_name"], "payment history and contract terms")
    state["retrieved_context"] = context if context else "No additional context."
    # Structured policy travels with the state for the guard and, in Phase 2, the
    # decision node.
    state["client_profile"] = profile_as_dict(get_profile(state["client_name"]))
    return state


def _resolve_promised_date(state: RecoveryState, intent_data: dict) -> str:
    """
    Determine when the client actually said they would pay.

    Honours the date the classifier extracted from natural language — that
    extraction is the entire point of the feature. Falls back to +7 days only when
    the model returned nothing, and anchors to the *virtual* clock so the promise
    lands inside the simulation rather than at a wall-clock date.
    """
    virtual_now = _parse_dt(state.get("virtual_date")) or datetime.utcnow()
    extracted = (intent_data.get("entities") or {}).get("promised_date")

    parsed = _parse_dt(extracted)
    if parsed:
        # A model may return a bare date; treat anything already past as next week.
        if parsed > virtual_now:
            return parsed.isoformat()

    return (virtual_now + timedelta(days=7)).isoformat()


async def classify_reply(state: RecoveryState) -> RecoveryState:
    if not state.get("client_reply"):
        return state

    intent_data = await classify_client_intent(state["client_reply"])
    intent = intent_data.get("intent")
    state["classified_intent"] = intent
    state["intent_confidence"] = intent_data.get("confidence")

    outcome = INTENT_OUTCOMES.get(intent)
    if not outcome:
        # An unrecognised intent must not silently continue the escalation.
        state["audit_entries"].append({
            "event_type": "INTENT_CLASSIFIED",
            "reasoning": f"Unrecognised intent '{intent}'; no automated action taken.",
            "action": "Logged reply without acting",
            "rule": "Unknown intent requires human interpretation",
            "content": state["client_reply"],
        })
        return state

    if outcome["new_status"]:
        state["new_status"] = outcome["new_status"]

    reasoning = f"Classified {intent} ({state['intent_confidence']} confidence)."

    if outcome["new_status"] == "PAUSED_PTP":
        promised = _resolve_promised_date(state, intent_data)
        state["promised_date"] = promised
        state["extracted_entities"] = {"promised_date": promised}
        reasoning += f" Payment promised by {promised[:10]}."

    if outcome["halt"]:
        state["should_send_email"] = False
        state["stop_reason"] = outcome["rule"]

    if outcome["notify"]:
        state["notify_payload"] = {
            "reason": intent,
            "detail": reasoning,
            "invoice_id": state["invoice_id"],
            "client_name": state["client_name"],
            "amount": state["amount"],
        }

    state["audit_entries"].append({
        "event_type": "INTENT_CLASSIFIED",
        "reasoning": reasoning,
        "action": outcome["action"],
        "rule": outcome["rule"],
        "content": state["client_reply"],
    })
    return state

def _days_since_contact(state: RecoveryState):
    """Virtual days since the last outbound contact, or None if never contacted."""
    last = _parse_dt(state.get("last_email_date"))
    if not last:
        return None
    now = _parse_dt(state.get("virtual_date")) or datetime.utcnow()
    return (now - last).days


def _decision_context(state: RecoveryState) -> dict:
    return {
        "invoice_id": state["invoice_id"],
        "client_name": state["client_name"],
        "amount": state["amount"],
        "due_date": state.get("due_date"),
        "days_overdue": state.get("days_overdue"),
        "current_status": state.get("new_status") or state["current_status"],
        "escalation_stage": state.get("escalation_stage"),
        "contact_attempts": state.get("contact_attempts", 0),
        "max_attempts": MAX_CONTACT_ATTEMPTS,
        "days_since_contact": _days_since_contact(state),
        "relationship_score": state.get("relationship_score", 1.0),
        "retrieved_context": state.get("retrieved_context") or "(none)",
        "profile": state.get("client_profile") or {},
        "interaction_history": state.get("interaction_history") or [],
    }


LADDER_STAGE_MAP = {
    "OVERDUE": "STAGE_1",
    "NOTIFIED_1": "STAGE_2",
    "NOTIFIED_2": "STAGE_3",
    "NOTIFIED_3": "STAGE_4",
    "PAUSED_PTP": "STAGE_2",
}


def _ladder_action(state: RecoveryState) -> dict:
    """
    The baseline the A/B measures against: a fixed-schedule chaser.

    This is what the system did before Phase 2 — `stage_map[current_status]`, the
    same treatment for every client regardless of profile. Kept as an explicit
    policy so "our agent recovers X% vs Y% for a rule-based chaser, same seed,
    same portfolio" is a controlled comparison rather than a claim.
    """
    current = state.get("new_status") or state["current_status"]
    stage = LADDER_STAGE_MAP.get(current, "STAGE_1")
    return {
        "action": "SEND_EMAIL",
        "stage": stage,
        "wait_days": None,
        "discount_pct": None,
        "instalments": None,
        "channel": None,
        "reasoning": (
            f"Fixed ladder: {current} always advances to {stage}, "
            "regardless of client profile or history."
        ),
        "confidence": 1.0,
        "expected_outcome": "Client receives the next scheduled notice.",
        "source": "fixed_ladder",
    }


async def decide_action(state: RecoveryState) -> RecoveryState:
    """
    The agent chooses an intervention.

    Replaces `stage_map[current_status]` — a dictionary that gave Acme Corp and
    NovaTech Labs identical treatment. The choice now reads the client's written
    profile, their history, and the remaining budget.
    """
    state.setdefault("visited_nodes", []).append("decide_action")

    ctx = _decision_context(state)
    if state.get("policy") == "ladder":
        action = _ladder_action(state)
    else:
        action = await choose_action(ctx)
    state["proposed_action"] = action

    considered = ", ".join(
        a for a in ["SEND_EMAIL", "WAIT", "OFFER_DISCOUNT", "SPLIT_INVOICE", "ESCALATE_TO_HUMAN"]
        if a != action["action"]
    )
    source_note = "" if action.get("source") == "llm" else \
        f" [selected by deterministic policy - {action.get('fallback_reason')}]"

    state["audit_entries"].append({
        "event_type": "AGENT_DECISION",
        "reasoning": action["reasoning"] + source_note,
        "action": (
            f"Chose {action['action']}"
            + (f" at {action['stage']}" if action.get("stage") else "")
            + (f" ({action['discount_pct']}%)" if action.get("discount_pct") else "")
            + (f" for {action['wait_days']}d" if action.get("wait_days") else "")
            + f" | confidence {action['confidence']:.2f}"
        ),
        "rule": f"Alternatives considered: {considered}",
        "content": (
            f"Expected outcome: {action['expected_outcome']}\n"
            f"Decision source: {action.get('source')}"
        ),
    })
    return state


async def validate_action(state: RecoveryState) -> RecoveryState:
    """
    The policy guard. Vetoes choices, substitutes a permitted one, audits every veto.
    """
    state.setdefault("visited_nodes", []).append("validate_action")

    proposed = state.get("proposed_action") or {}
    verdict = policy_guard.validate(proposed, _decision_context(state))

    state["action_validated"] = verdict.validated
    state["effective_action"] = verdict.action

    if verdict.validated:
        state["veto_reason"] = None
        state["substituted_action"] = None
        return state

    state["substituted_action"] = verdict.action
    state["veto_reason"] = "; ".join(v["rule"] for v in verdict.vetoes)

    for veto in verdict.vetoes:
        state["audit_entries"].append({
            "event_type": "ACTION_VETOED",
            "reasoning": veto["detail"],
            "action": (
                f"Blocked {veto['proposed']['action']}"
                + (f" at {veto['proposed']['stage']}" if veto["proposed"].get("stage") else "")
                + (f" ({veto['proposed']['discount_pct']}%)" if veto["proposed"].get("discount_pct") else "")
                + f" -> substituted {veto['substitute'].get('action', verdict.action['action'])}"
            ),
            "rule": f"Guard rule {veto['rule_number']}: {veto['rule']}",
            "content": None,
        })
    return state


class _InvoiceView:
    """
    The invoice fields draft_escalation_email needs, carried from RecoveryState.

    Replaces a DummyInvoice shim whose due_date was datetime.utcnow(), which made
    every drafted email state today as the due date regardless of the real one.
    """

    def __init__(self, state: RecoveryState):
        self.id = state["invoice_id"]
        self.client_name = state["client_name"]
        self.client_email = state.get("client_email")
        self.amount = state["amount"]
        self.due_date = _parse_dt(state.get("due_date")) or state.get("due_date")


async def draft_email(state: RecoveryState) -> RecoveryState:
    state.setdefault("visited_nodes", []).append("draft_email")

    # The stage now comes from the agent's validated decision. stage_map survives
    # only as the fallback for paths that reach drafting without a decision
    # (the reply sub-graph, chiefly).
    stage_map = {
        "OVERDUE": "STAGE_1",
        "NOTIFIED_1": "STAGE_2",
        "NOTIFIED_2": "STAGE_3",
        "NOTIFIED_3": "STAGE_4",
        "PAUSED_PTP": "STAGE_2" # Broken promise
    }

    current = state.get("new_status") or state["current_status"]
    action = state.get("effective_action") or {}
    stage = action.get("stage") or stage_map.get(current, "STAGE_1")

    # A client's profile can cap autonomy below STAGE_4 (Acme and NovaTech stop at
    # STAGE_2). Past that cap the case belongs to a person, not the agent.
    profile = state.get("client_profile") or {}
    max_stage = profile.get("max_autonomous_stage", "STAGE_4")
    if stage_rank(stage) > stage_rank(max_stage):
        state["escalation_stage"] = stage
        state["new_status"] = "HUMAN_ESCALATED"
        state["should_send_email"] = False
        state["notify_payload"] = {
            "reason": "STAGE_ABOVE_AUTONOMY",
            "detail": (
                f"{stage} exceeds this client's autonomous limit of {max_stage}. "
                f"{'; '.join(profile.get('guardrails', [])[:1])}"
            ),
            "invoice_id": state["invoice_id"],
            "client_name": state["client_name"],
            "amount": state["amount"],
        }
        state["audit_entries"].append({
            "event_type": "STATUS_CHANGED",
            "reasoning": state["notify_payload"]["detail"],
            "action": "Routed to human instead of escalating",
            "rule": f"Client policy caps autonomous escalation at {max_stage}",
            "content": None,
        })
        return state
    
    if stage == "STAGE_4" or stage == "UNRESPONSIVE":
        state["escalation_stage"] = stage
        state["should_send_email"] = False

        # A client who never once replied across the whole ladder is a ghost:
        # that is stopping rule 5, not a draft awaiting approval. One who did
        # engage gets the STAGE_4 human-approval gate instead.
        if state.get("client_replies", 0) == 0:
            state["new_status"] = "UNRESPONSIVE"
            detail = (
                f"No reply to any of {state.get('contact_attempts', 0)} contacts "
                f"across the full escalation ladder."
            )
            state["notify_payload"] = {
                "reason": "UNRESPONSIVE",
                "detail": detail,
                "invoice_id": state["invoice_id"],
                "client_name": state["client_name"],
                "amount": state["amount"],
            }
            state["audit_entries"].append({
                "event_type": "STATUS_CHANGED",
                "reasoning": detail,
                "action": "Marked UNRESPONSIVE and routed to human review",
                "rule": "Stop 5: Ladder exhausted with no client engagement",
                "content": None,
            })
            return state

        state["new_status"] = "HUMAN_ESCALATED"
        state["notify_payload"] = {
            "reason": "STAGE_4_GATE",
            "detail": "Formal final notice requires human approval before sending.",
            "invoice_id": state["invoice_id"],
            "client_name": state["client_name"],
            "amount": state["amount"],
        }
        state["audit_entries"].append({
            "event_type": "STATUS_CHANGED",
            "reasoning": "Requires human approval before sending STAGE_4",
            "action": "Routed to human",
            "rule": "Formal final notice requires human approval",
            "content": None
        })
        return state

    context = ""
    # An offer prepared upstream (discount, plan, split) becomes part of the brief.
    if state.get("offer_context"):
        context = state["offer_context"] + " "
    if current == "NOTIFIED_1": context += "Stage 1 sent previously."
    if current == "NOTIFIED_2": context += "Stage 1 and 2 sent previously."
    if current == "PAUSED_PTP":
        # The promise window has already been cleared by check_stop_conditions, so
        # reaching here means the date passed. Name the date in the draft.
        promised = _parse_dt(state.get("promised_date"))
        context += (
            f"Promise to pay was broken. Client committed to pay by "
            f"{promised.date().isoformat()} and that date has passed."
            if promised else "Promise to pay was broken."
        )

    draft = await draft_escalation_email(
        _InvoiceView(state),
        stage,
        context,
        retrieved_context=state.get("retrieved_context", ""),
        feedback=state.get("compliance_reason", "")
    )
    state["drafted_email"] = draft
    state["escalation_stage"] = stage
    
    if current == "OVERDUE": state["new_status"] = "NOTIFIED_1"
    elif current == "NOTIFIED_1": state["new_status"] = "NOTIFIED_2"
    elif current == "NOTIFIED_2": state["new_status"] = "NOTIFIED_3"
    elif current == "PAUSED_PTP": state["new_status"] = "NOTIFIED_2"
    
    return state

async def evaluate_compliance(state: RecoveryState) -> RecoveryState:
    state.setdefault("visited_nodes", []).append("evaluate_compliance")

    if not state.get("drafted_email") or not state.get("should_send_email"):
        # Nothing was drafted, so nothing was reviewed. This used to record PASS,
        # which inflated the compliance rate with checks that never happened.
        # No audit row is written either — there is no draft to attach one to.
        state["compliance_verdict"] = None
        return state
        
    evaluation = await evaluate_email_compliance(
        state["drafted_email"],
        state["escalation_stage"],
        state.get("retrieved_context", ""),
        client_name=state.get("client_name"),
    )
    
    state["compliance_verdict"] = evaluation.get("verdict", "FAIL")
    state["compliance_reason"] = evaluation.get("reason", "")
    verdict_source = evaluation.get("source", "unknown")
    
    if state["compliance_verdict"] == "UNREVIEWED":
        # Distinct from both PASS and FAIL: the draft goes out, but no judge saw
        # it. Not counted as a check, and not retried — there is no feedback to
        # rewrite against.
        state["audit_entries"].append({
            "event_type": "COMPLIANCE_UNREVIEWED",
            "reasoning": state["compliance_reason"] or "Compliance judge was unavailable.",
            "action": "Sent without compliance review",
            "rule": "Compliance Judge unavailable",
            "content": state["drafted_email"],
            "compliance_verdict": "UNREVIEWED",
            "verdict_source": verdict_source,
        })
    elif state["compliance_verdict"] != "PASS":
        state["compliance_retries"] = state.get("compliance_retries", 0) + 1
        state["audit_entries"].append({
            "event_type": "COMPLIANCE_FAILED",
            "reasoning": state["compliance_reason"],
            "action": "Rejected email draft",
            "rule": "Compliance Judge",
            "content": state["drafted_email"],
            "compliance_verdict": state["compliance_verdict"],
            "verdict_source": verdict_source,
        })
    else:
        state["audit_entries"].append({
            "event_type": "COMPLIANCE_PASSED",
            "reasoning": state["compliance_reason"] or "Email meets all requirements.",
            "action": "Approved email draft",
            "rule": "Compliance Judge",
            "content": state["drafted_email"],
            "compliance_verdict": state["compliance_verdict"],
            "verdict_source": verdict_source,
        })

    return state


async def call_razorpay_tools(state: RecoveryState) -> RecoveryState:
    """
    Attach payment rails to the drafted message.

    `prepare_offer` may already have created a link for a commercial action; this
    only creates one when the branch has not. Goes through the audited tool layer,
    which uses the Razorpay SDK.
    """
    state.setdefault("visited_nodes", []).append("call_razorpay_tools")
    if not state.get("drafted_email"):
        return state

    if not state.get("payment_link_url"):
        link = await tools.create_payment_link(
            state, state["amount"], f"Payment for Invoice {state['invoice_id']}"
        )
        state["payment_link_id"] = link.get("id")
        state["payment_link_url"] = link.get("short_url")

    state["drafted_email"] = state["drafted_email"].replace(
        "{{payment_link}}", state["payment_link_url"] or ""
    )
    return state

async def act_wait(state: RecoveryState) -> RecoveryState:
    """
    Deliberate patience — the option the old system could not express.

    Nothing is sent. The audit row records that doing nothing was a decision, with
    the agent's reasoning, so a judge can see restraint being chosen on purpose.
    """
    state.setdefault("visited_nodes", []).append("act_wait")
    action = state.get("effective_action") or {}
    wait_days = action.get("wait_days") or 1
    virtual_now = _parse_dt(state.get("virtual_date")) or datetime.utcnow()
    next_review = virtual_now + timedelta(days=wait_days)

    state["should_send_email"] = False
    state["audit_entries"].append({
        "event_type": "AGENT_WAIT",
        "reasoning": action.get("reasoning", "Deliberate pause."),
        "action": f"Took no action; next review {next_review.date().isoformat()} ({wait_days}d)",
        "rule": "WAIT is a first-class action, not an absence of one",
        "content": f"Expected outcome: {action.get('expected_outcome', 'n/a')}",
    })
    return state


async def prepare_offer(state: RecoveryState) -> RecoveryState:
    """
    Turn a commercial action into real payment artefacts before drafting.

    OFFER_DISCOUNT creates a discounted link, SPLIT_INVOICE creates two, and
    OFFER_PAYMENT_PLAN creates one per instalment. Each goes through the audited
    tool layer.
    """
    state.setdefault("visited_nodes", []).append("prepare_offer")
    action = state.get("effective_action") or {}
    kind = action.get("action")
    amount = state["amount"]

    if kind == "OFFER_DISCOUNT":
        pct = action.get("discount_pct") or 0
        link = await tools.create_payment_link(
            state, amount, f"Invoice {state['invoice_id']} - {pct}% early payment discount",
            discount_pct=pct,
        )
        state["payment_link_id"] = link.get("id")
        state["payment_link_url"] = link["short_url"]
        state["offer_context"] = (
            f"Offer a {pct}% early-payment discount, reducing the amount due to "
            f"INR {link['amount']:,.0f} if paid promptly."
        )

    elif kind == "SPLIT_INVOICE":
        # Pinnacle's contract: undisputed and disputed portions billed separately.
        undisputed = round(amount * 0.6, 2)
        disputed = round(amount - undisputed, 2)
        first = await tools.create_payment_link(
            state, undisputed, f"Invoice {state['invoice_id']} - undisputed portion")
        await tools.create_payment_link(
            state, disputed, f"Invoice {state['invoice_id']} - disputed portion (on hold)")
        state["payment_link_id"] = first.get("id")
        state["payment_link_url"] = first["short_url"]
        state["offer_context"] = (
            f"Split the invoice: INR {undisputed:,.0f} undisputed is payable now on a separate "
            f"link, while INR {disputed:,.0f} remains under review. Do not combine them."
        )

    elif kind == "OFFER_PAYMENT_PLAN":
        n = action.get("instalments") or 3
        per = round(amount / n, 2)
        first = await tools.create_payment_link(
            state, per, f"Invoice {state['invoice_id']} - instalment 1 of {n}")
        state["payment_link_id"] = first.get("id")
        state["payment_link_url"] = first["short_url"]
        state["offer_context"] = (
            f"Offer a {n}-instalment payment plan of INR {per:,.0f} each; the first "
            "instalment link is attached."
        )

    return state


async def draft_sms(state: RecoveryState) -> RecoveryState:
    """Short-form message for SWITCH_CHANNEL. Compliance still applies."""
    state.setdefault("visited_nodes", []).append("draft_sms")
    action = state.get("effective_action") or {}
    channel = action.get("channel") or "SMS"
    state["drafted_email"] = (
        f"[{channel}] {state['client_name']}: Invoice {state['invoice_id']} for "
        f"INR {state['amount']:,.0f} is {state.get('days_overdue')} days overdue. "
        f"Pay here: {{{{payment_link}}}}"
    )
    state["escalation_stage"] = action.get("stage") or state.get("escalation_stage") or "STAGE_1"
    state["audit_entries"].append({
        "event_type": "CHANNEL_SWITCHED",
        "reasoning": action.get("reasoning", "Email has not produced a response."),
        "action": f"Drafted a {channel} message instead of email",
        "rule": "SWITCH_CHANNEL",
        "content": state["drafted_email"],
    })
    return state


async def act_close(state: RecoveryState) -> RecoveryState:
    """CLOSE_AS_UNRECOVERABLE — stop pursuing, and tell a person."""
    state.setdefault("visited_nodes", []).append("act_close")
    action = state.get("effective_action") or {}
    await tools.update_invoice_status(
        state, "UNRESPONSIVE",
        action.get("reasoning", "Recovery is no longer economic."),
    )
    state["should_send_email"] = False
    state["notify_payload"] = {
        "reason": "CLOSED_AS_UNRECOVERABLE",
        "detail": action.get("reasoning", "Agent judged this unrecoverable."),
        "invoice_id": state["invoice_id"],
        "client_name": state["client_name"],
        "amount": state["amount"],
    }
    return state


async def act_escalate(state: RecoveryState) -> RecoveryState:
    """ESCALATE_TO_HUMAN, whether chosen by the agent or substituted by the guard."""
    state.setdefault("visited_nodes", []).append("act_escalate")
    action = state.get("effective_action") or {}
    detail = state.get("veto_reason") or action.get("reasoning") or "Case requires human judgment."

    await tools.update_invoice_status(state, "HUMAN_ESCALATED", detail)
    state["should_send_email"] = False
    state["notify_payload"] = {
        "reason": "AGENT_ESCALATION" if state.get("action_validated") else "GUARD_VETO",
        "detail": detail,
        "invoice_id": state["invoice_id"],
        "client_name": state["client_name"],
        "amount": state["amount"],
    }
    return state


async def execute_action(state: RecoveryState) -> RecoveryState:
    state.setdefault("visited_nodes", []).append("execute_action")
    if state.get("should_send_email") and state.get("drafted_email"):
        if state.get("compliance_verdict") == "PASS":
            rule = "Resume escalation if promise broken" if state["current_status"] == "PAUSED_PTP" else None
            # Count the contact so stopping rule 5 can cap it.
            state["contact_attempts"] = state.get("contact_attempts", 0) + 1

            action = state.get("effective_action") or {}
            if action.get("action") == "SWITCH_CHANNEL":
                await tools.send_sms(
                    state, state.get("client_email") or "", state["drafted_email"],
                    action.get("channel") or "SMS",
                )
            else:
                await tools.send_email(
                    state,
                    state.get("client_email") or "",
                    f"Invoice {state['invoice_id']} - payment reminder",
                    state["drafted_email"],
                    state.get("escalation_stage") or "STAGE_1",
                )

            # Pushing past a client's autonomous limit has a cost. Phase 4's
            # environment reads this, which is what makes restraint rational.
            profile = state.get("client_profile") or {}
            max_stage = profile.get("max_autonomous_stage", "STAGE_4")
            if stage_rank(state.get("escalation_stage")) > stage_rank(max_stage):
                state["relationship_score"] = round(
                    max(0.0, state.get("relationship_score", 1.0) - 0.15), 3
                )

            state["audit_entries"].append({
                "event_type": "EMAIL_SENT",
                "reasoning": (
                    f"{state['escalation_stage']} Escalation "
                    f"(contact {state['contact_attempts']} of {MAX_CONTACT_ATTEMPTS})"
                ),
                "action": f"Drafted and sent {state['escalation_stage']} email",
                "rule": rule,
                "content": state["drafted_email"]
            })
        else:
            state["audit_entries"].append({
                "event_type": "STATUS_CHANGED",
                "reasoning": "Max compliance retries reached",
                "action": "Routed to human",
                "rule": None,
                "content": None
            })
            state["new_status"] = "HUMAN_ESCALATED"
            state["notify_payload"] = {
                "reason": "COMPLIANCE_EXHAUSTED",
                "detail": "Compliance judge rejected every rewrite attempt.",
                "invoice_id": state["invoice_id"],
                "client_name": state["client_name"],
                "amount": state["amount"],
            }
    return state

async def simulate_client(state: RecoveryState) -> RecoveryState:
    """
    SIMULATED ENVIRONMENT — not agent logic.

    Delegates to src/simulation/client_env.py, which is explicitly labelled as the
    test harness. The response now depends on the action the agent chose, not only
    the stage, so agent judgment can actually affect the outcome. Seeded, so the
    same seed reproduces the same run.
    """
    state.setdefault("visited_nodes", []).append("simulate_client")
    seed = state.get("sim_seed", 42)
    status = state.get("new_status") or state["current_status"]

    # A promise whose date has arrived is resolved rather than re-rolled.
    promised = _parse_dt(state.get("promised_date"))
    virtual_now = _parse_dt(state.get("virtual_date")) or datetime.utcnow()
    if status == "PAUSED_PTP" and promised and virtual_now >= promised:
        if client_env.resolve_promise(state, seed):
            state["new_status"] = "RECOVERED"
            state["audit_entries"].append({
                "event_type": "PAYMENT_RECEIVED",
                "reasoning": "[SIMULATED ENVIRONMENT] Client honoured their promise.",
                "action": "Marked as RECOVERED",
                "rule": None,
                "content": None,
            })
        else:
            state["audit_entries"].append({
                "event_type": "PTP_BROKEN",
                "reasoning": (
                    "[SIMULATED ENVIRONMENT] Promise date passed without payment "
                    f"(this persona breaks {int(get_profile(state['client_name']).ptp_break_rate * 100)}% "
                    "of commitments)."
                ),
                "action": "Promise broken; escalation may resume",
                "rule": "Stop 2 expired",
                "content": None,
            })
        return state

    # An idle tick — the ladder blocked by cooldown, or the agent choosing WAIT —
    # is modelled identically: the client may still pay unprompted, weighted by
    # how reliable this persona is. Scoring the two differently would hand the
    # agent an advantage it did not earn.
    if not state.get("effective_action"):
        state["effective_action"] = {"action": "WAIT", "_idle": True}

    result = client_env.simulate_response(state, seed)

    # Over-escalation costs relationship score, which lowers future p(pay).
    damage, damage_note = client_env.relationship_damage(state)
    if damage:
        state["relationship_score"] = round(max(0.0, state.get("relationship_score", 1.0) - damage), 3)
        state["audit_entries"].append({
            "event_type": "RELATIONSHIP_DAMAGED",
            "reasoning": f"[SIMULATED ENVIRONMENT] {damage_note}",
            "action": f"Relationship score reduced to {state['relationship_score']}",
            "rule": "Over-escalation has a cost",
            "content": None,
        })

    if result["outcome"] in ("PAID", "PARTIAL_PAID"):
        state["new_status"] = "RECOVERED"
        state["audit_entries"].append({
            "event_type": "PAYMENT_RECEIVED",
            "reasoning": f"[SIMULATED ENVIRONMENT] {result['explanation']}",
            "action": "Marked as RECOVERED"
                      + (" (undisputed portion)" if result["outcome"] == "PARTIAL_PAID" else ""),
            "rule": None,
            "content": result.get("reply_text"),
        })
    elif result["outcome"] == "PROMISED":
        state["new_status"] = "PAUSED_PTP"
        state["promised_date"] = result["promised_date"]
        state["extracted_entities"] = {"promised_date": result["promised_date"]}
        state["audit_entries"].append({
            "event_type": "INTENT_CLASSIFIED",
            "reasoning": f"[SIMULATED ENVIRONMENT] Client promised payment. {result['explanation']}",
            "action": f"Paused until {result['promised_date'][:10]}",
            "rule": "Stop 2: Pause escalation until promised date + grace",
            "content": result.get("reply_text"),
        })
    elif result["outcome"] == "DISPUTED":
        state["new_status"] = "DISPUTE"
        state["audit_entries"].append({
            "event_type": "INTENT_CLASSIFIED",
            "reasoning": f"[SIMULATED ENVIRONMENT] Client disputed. {result['explanation']}",
            "action": "Halted and routed to human for dispute resolution",
            "rule": "Stop 3: Halt automated collection on dispute",
            "content": result.get("reply_text"),
        })
    else:
        state["audit_entries"].append({
            "event_type": "NO_RESPONSE",
            "reasoning": f"[SIMULATED ENVIRONMENT] No response. {result['explanation']}",
            "action": "Client did not respond",
            "rule": None,
            "content": None,
        })

    return state
