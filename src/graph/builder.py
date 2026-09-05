from langgraph.graph import StateGraph, END
from src.graph.state import RecoveryState
from src.graph.nodes import (
    check_overdue, check_stop_conditions, check_cooldown, log_blocked,
    retrieve_client_context, classify_reply, decide_action, validate_action,
    draft_email, draft_sms, prepare_offer, act_wait, act_escalate, act_close,
    evaluate_compliance, call_razorpay_tools, execute_action, notify_human,
    simulate_client
)
from src.graph.edges import (
    route_after_overdue, route_after_stop_conditions, route_after_cooldown,
    route_after_classification, route_after_validation, route_after_compliance,
    route_after_draft, route_after_execute
)

workflow = StateGraph(RecoveryState)

workflow.add_node("check_overdue", check_overdue)
workflow.add_node("check_stop_conditions", check_stop_conditions)
workflow.add_node("check_cooldown", check_cooldown)
workflow.add_node("log_blocked", log_blocked)
workflow.add_node("retrieve_client_context", retrieve_client_context)
workflow.add_node("classify_reply", classify_reply)
workflow.add_node("decide_action", decide_action)
workflow.add_node("validate_action", validate_action)
workflow.add_node("draft_email", draft_email)
workflow.add_node("draft_sms", draft_sms)
workflow.add_node("prepare_offer", prepare_offer)
workflow.add_node("act_wait", act_wait)
workflow.add_node("act_escalate", act_escalate)
workflow.add_node("act_close", act_close)
workflow.add_node("evaluate_compliance", evaluate_compliance)
workflow.add_node("call_razorpay_tools", call_razorpay_tools)
workflow.add_node("execute_action", execute_action)
workflow.add_node("notify_human", notify_human)
workflow.add_node("simulate_client", simulate_client)

workflow.set_entry_point("check_overdue")

workflow.add_conditional_edges(
    "check_overdue",
    route_after_overdue,
    {
        "check_stop_conditions": "check_stop_conditions",
        "__end__": END
    }
)

# The stopping rules gate everything downstream: nothing is drafted, and no
# cooldown is even consulted, until they have had their say.
workflow.add_conditional_edges(
    "check_stop_conditions",
    route_after_stop_conditions,
    {
        "check_cooldown": "check_cooldown",
        "notify_human": "notify_human",
        "__end__": END
    }
)

workflow.add_conditional_edges(
    "check_cooldown",
    route_after_cooldown,
    {
        "retrieve_client_context": "retrieve_client_context",
        "log_blocked": "log_blocked"
    }
)

# An idle day still gives the client a chance to pay unprompted. Both the
# agent's deliberate WAIT and the ladder's cooldown block route here, so
# neither policy is scored more generously for doing nothing.
workflow.add_edge("log_blocked", "simulate_client")

workflow.add_edge("retrieve_client_context", "classify_reply")

workflow.add_conditional_edges(
    "classify_reply",
    route_after_classification,
    {
        "decide_action": "decide_action",
        "notify_human": "notify_human",
        "__end__": END
    }
)

# The agent chooses, then the guard may veto and substitute.
workflow.add_edge("decide_action", "validate_action")

# Dispatch by action type. The draft -> judge -> rewrite loop survives intact as
# one branch of this, rather than being the only path through the graph.
workflow.add_conditional_edges(
    "validate_action",
    route_after_validation,
    {
        "draft_email": "draft_email",
        "prepare_offer": "prepare_offer",
        "draft_sms": "draft_sms",
        "act_wait": "act_wait",
        "act_escalate": "act_escalate",
        "act_close": "act_close",
    }
)

# Commercial offers create their Razorpay artefacts, then are written up as email.
workflow.add_edge("prepare_offer", "draft_email")

workflow.add_conditional_edges(
    "draft_email",
    route_after_draft,
    {
        "evaluate_compliance": "evaluate_compliance",
        "notify_human": "notify_human"
    }
)

# A short-form message is still judged before it goes out.
workflow.add_edge("draft_sms", "evaluate_compliance")

workflow.add_edge("act_wait", "simulate_client")
workflow.add_edge("act_escalate", "notify_human")
workflow.add_edge("act_close", "notify_human")

workflow.add_conditional_edges(
    "evaluate_compliance",
    route_after_compliance,
    {
        "call_razorpay_tools": "call_razorpay_tools",
        "execute_action": "execute_action",
        "draft_email": "draft_email"
    }
)

workflow.add_edge("call_razorpay_tools", "execute_action")

workflow.add_conditional_edges(
    "execute_action",
    route_after_execute,
    {
        "simulate_client": "simulate_client",
        "notify_human": "notify_human"
    }
)

workflow.add_edge("notify_human", END)

workflow.add_edge("simulate_client", END)

compiled_graph = workflow.compile()


# --- Reply sub-graph -------------------------------------------------------
# An inbound client reply must not re-enter the escalation ladder: it is a
# classification event, not a tick. A compiled LangGraph has a fixed entry
# point, so the reply path is its own graph over the same nodes and state.
# `simulate_client` is deliberately excluded — a real reply is an observation,
# and rolling dice on top of it would overwrite what the client actually said.
reply_workflow = StateGraph(RecoveryState)
reply_workflow.add_node("classify_reply", classify_reply)
reply_workflow.add_node("execute_action", execute_action)
reply_workflow.add_node("notify_human", notify_human)
reply_workflow.set_entry_point("classify_reply")
reply_workflow.add_conditional_edges(
    "classify_reply",
    route_after_classification,
    {
        # A reply classifies, then either halts or hands off. It never drafts and
        # never re-decides — the next tick does that with the new status in hand.
        # This key must track route_after_classification's non-halt return value.
        "decide_action": "execute_action",
        "notify_human": "notify_human",
        "__end__": END
    }
)
reply_workflow.add_conditional_edges(
    "execute_action",
    route_after_execute,
    {
        "simulate_client": END,
        "notify_human": "notify_human"
    }
)
reply_workflow.add_edge("notify_human", END)

reply_graph = reply_workflow.compile()
