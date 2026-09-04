from src.graph.state import RecoveryState

def route_after_overdue(state: RecoveryState) -> str:
    if state["days_overdue"] <= 0:
        return "__end__"
    return "check_cooldown"

def route_after_cooldown(state: RecoveryState) -> str:
    if not state.get("should_send_email"):
        return "log_blocked"
    return "retrieve_client_context"

def route_after_classification(state: RecoveryState) -> str:
    intent = state.get("classified_intent")
    if intent in ("PROMISE_TO_PAY", "DISPUTE", "OPT_OUT", "LEGAL_THREAT"):
        return "execute_action"    # Halt - no email needed
    return "draft_email"           # Continue escalation

def route_after_compliance(state: RecoveryState) -> str:
    if state.get("compliance_verdict") == "PASS":
        return "call_razorpay_tools"
    if state.get("compliance_retries", 0) >= 2:
        return "execute_action"    # Give up after 2 rewrites, log failure
    return "draft_email"           # Rewrite with Judge's feedback
