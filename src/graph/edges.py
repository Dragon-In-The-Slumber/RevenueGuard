from src.graph.state import RecoveryState

# Statuses that require a person to be told before the graph ends.
NOTIFY_STATUSES = {"DISPUTE", "LEGAL_HOLD", "UNRESPONSIVE", "HUMAN_ESCALATED"}


def route_after_overdue(state: RecoveryState) -> str:
    if state["days_overdue"] <= 0:
        return "__end__"
    return "check_stop_conditions"


def route_after_stop_conditions(state: RecoveryState) -> str:
    """
    A stopping rule may have halted the workflow. If a person needs to know,
    go through notify_human; otherwise end quietly or continue to the cooldown.
    """
    if state.get("stop_reason"):
        status = state.get("new_status") or state["current_status"]
        if status in NOTIFY_STATUSES:
            return "notify_human"
        return "__end__"
    return "check_cooldown"


def route_after_cooldown(state: RecoveryState) -> str:
    """
    Who enforces the contact cooldown depends on the policy.

    The fixed-ladder baseline halts here — that is what a rule-based chaser does.
    The agent does not: it is allowed to decide every tick, and guard rule 1
    substitutes WAIT when it proposes contact too soon. Halting the agent before
    decide_action made WAIT unreachable and left guard rule 1 as dead code, so
    the agent could never behave differently from the ladder and the A/B measured
    nothing.
    """
    if not state.get("should_send_email"):
        if state.get("policy") == "ladder":
            return "log_blocked"
        return "retrieve_client_context"
    return "retrieve_client_context"


def route_after_classification(state: RecoveryState) -> str:
    """
    A reply that triggers a stopping rule halts here. Cases needing a human go to
    notify_human; the rest continue to the agent's decision.
    """
    status = state.get("new_status") or state["current_status"]

    if state.get("stop_reason"):
        if status in NOTIFY_STATUSES:
            return "notify_human"
        return "__end__"

    return "decide_action"


# Which branch each action dispatches to. The email path is one entry here, not
# the trunk it used to be.
ACTION_DISPATCH = {
    "SEND_EMAIL": "draft_email",
    "OFFER_DISCOUNT": "prepare_offer",
    "OFFER_PAYMENT_PLAN": "prepare_offer",
    "SPLIT_INVOICE": "prepare_offer",
    "SWITCH_CHANNEL": "draft_sms",
    "WAIT": "act_wait",
    "ESCALATE_TO_HUMAN": "act_escalate",
    "CLOSE_AS_UNRECOVERABLE": "act_close",
}


def route_after_validation(state: RecoveryState) -> str:
    """Dispatch by action type — the agentic core's branch point."""
    action = (state.get("effective_action") or {}).get("action", "SEND_EMAIL")
    return ACTION_DISPATCH.get(action, "draft_email")


def route_after_compliance(state: RecoveryState) -> str:
    if state.get("compliance_verdict") == "PASS":
        return "call_razorpay_tools"
    if state.get("compliance_retries", 0) >= 2:
        return "execute_action"    # Give up after 2 rewrites, log failure
    return "draft_email"           # Rewrite with Judge's feedback


def route_after_draft(state: RecoveryState) -> str:
    """draft_email can bail out to a human instead of producing a draft."""
    if not state.get("should_send_email") or not state.get("drafted_email"):
        return "notify_human"
    return "evaluate_compliance"


def route_after_execute(state: RecoveryState) -> str:
    """A run that ended by handing off to a person must notify before finishing."""
    status = state.get("new_status") or state["current_status"]
    if status in NOTIFY_STATUSES and state.get("notify_payload"):
        return "notify_human"
    return "simulate_client"
