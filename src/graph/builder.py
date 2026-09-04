from langgraph.graph import StateGraph, END
from src.graph.state import RecoveryState
from src.graph.nodes import (
    check_overdue, check_cooldown, log_blocked, retrieve_client_context,
    classify_reply, draft_email, evaluate_compliance, call_razorpay_tools,
    execute_action, simulate_client
)
from src.graph.edges import (
    route_after_overdue, route_after_cooldown, route_after_classification, route_after_compliance
)

workflow = StateGraph(RecoveryState)

workflow.add_node("check_overdue", check_overdue)
workflow.add_node("check_cooldown", check_cooldown)
workflow.add_node("log_blocked", log_blocked)
workflow.add_node("retrieve_client_context", retrieve_client_context)
workflow.add_node("classify_reply", classify_reply)
workflow.add_node("draft_email", draft_email)
workflow.add_node("evaluate_compliance", evaluate_compliance)
workflow.add_node("call_razorpay_tools", call_razorpay_tools)
workflow.add_node("execute_action", execute_action)
workflow.add_node("simulate_client", simulate_client)

workflow.set_entry_point("check_overdue")

workflow.add_conditional_edges(
    "check_overdue",
    route_after_overdue,
    {
        "check_cooldown": "check_cooldown",
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

workflow.add_edge("log_blocked", END)

workflow.add_edge("retrieve_client_context", "classify_reply")

workflow.add_conditional_edges(
    "classify_reply",
    route_after_classification,
    {
        "draft_email": "draft_email",
        "execute_action": "execute_action"
    }
)

workflow.add_edge("draft_email", "evaluate_compliance")

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

workflow.add_edge("execute_action", "simulate_client")

workflow.add_edge("simulate_client", END)

compiled_graph = workflow.compile()
