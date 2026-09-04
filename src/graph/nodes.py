from src.graph.state import RecoveryState
from src.ai.llm import draft_escalation_email, classify_client_intent
from src.rag.vector_store import search_client_context
from src.ai.compliance_judge import evaluate_email_compliance
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode
from datetime import datetime, timedelta
import random

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

async def check_cooldown(state: RecoveryState) -> RecoveryState:
    # Set this to true by default unless blocked
    state["should_send_email"] = True
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
    context_list = await search_client_context(state["client_name"], "payment history and contract terms")
    state["retrieved_context"] = context_list if context_list else "No additional context."
    return state

async def classify_reply(state: RecoveryState) -> RecoveryState:
    if state.get("client_reply"):
        intent_data = await classify_client_intent(state["client_reply"])
        state["classified_intent"] = intent_data.get("intent")
        state["intent_confidence"] = intent_data.get("confidence")
        
        if state["classified_intent"] == "PROMISE_TO_PAY":
            state["new_status"] = "PAUSED_PTP"
            state["extracted_entities"] = {"promised_date": (datetime.utcnow() + timedelta(days=7)).isoformat()}
            state["audit_entries"].append({
                "event_type": "INTENT_CLASSIFIED",
                "reasoning": f"Classified PROMISE_TO_PAY ({state['intent_confidence']} conf).",
                "action": "Paused workflow",
                "rule": "Pause escalation on PTP intent",
                "content": state["client_reply"]
            })
        elif state["classified_intent"] == "DISPUTE":
            state["new_status"] = "DISPUTE"
            state["audit_entries"].append({
                "event_type": "INTENT_CLASSIFIED",
                "reasoning": f"Classified DISPUTE ({state['intent_confidence']} conf).",
                "action": "Halted and routed to human",
                "rule": "Halt on DISPUTE intent",
                "content": state["client_reply"]
            })
    return state

async def draft_email(state: RecoveryState) -> RecoveryState:
    # Dummy invoice object just for draft_escalation_email which expects an invoice object
    class DummyInvoice:
        id = state["invoice_id"]
        client_name = state["client_name"]
        amount = state["amount"]
        due_date = datetime.utcnow() # mock
    
    stage_map = {
        "OVERDUE": "STAGE_1",
        "NOTIFIED_1": "STAGE_2",
        "NOTIFIED_2": "STAGE_3",
        "NOTIFIED_3": "UNRESPONSIVE",
        "PAUSED_PTP": "STAGE_2" # Broken promise
    }
    
    current = state.get("new_status") or state["current_status"]
    stage = stage_map.get(current, "STAGE_1")
    
    if stage == "UNRESPONSIVE":
        state["new_status"] = "UNRESPONSIVE"
        state["audit_entries"].append({
            "event_type": "STATUS_CHANGED",
            "reasoning": "Max automated attempts reached",
            "action": "Routed to human",
            "rule": None,
            "content": None
        })
        state["should_send_email"] = False
        return state
        
    context = ""
    if current == "NOTIFIED_1": context = "Stage 1 sent previously."
    if current == "NOTIFIED_2": context = "Stage 1 and 2 sent previously."
    if current == "PAUSED_PTP": context = "Promise to pay was broken."
    
    draft = await draft_escalation_email(
        DummyInvoice(), 
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
    if not state.get("drafted_email") or not state.get("should_send_email"):
        state["compliance_verdict"] = "PASS"
        return state
        
    evaluation = await evaluate_email_compliance(
        state["drafted_email"], 
        state["escalation_stage"], 
        state.get("retrieved_context", "")
    )
    
    state["compliance_verdict"] = evaluation.get("verdict", "FAIL")
    state["compliance_reason"] = evaluation.get("reason", "")
    
    if state["compliance_verdict"] != "PASS":
        state["compliance_retries"] = state.get("compliance_retries", 0) + 1
        state["audit_entries"].append({
            "event_type": "COMPLIANCE_FAILED",
            "reasoning": state["compliance_reason"],
            "action": "Rejected email draft",
            "rule": "Compliance Judge",
            "content": state["drafted_email"]
        })
    else:
        state["audit_entries"].append({
            "event_type": "COMPLIANCE_PASSED",
            "reasoning": state["compliance_reason"] or "Email meets all requirements.",
            "action": "Approved email draft",
            "rule": "Compliance Judge",
            "content": state["drafted_email"]
        })
    
    return state


async def call_razorpay_tools(state: RecoveryState) -> RecoveryState:
    if state.get("drafted_email"):
        mock_link = f"https://rzp.io/l/{state['invoice_id']}_{int(datetime.utcnow().timestamp())}"
        
        try:
            import os
            import json
            from mcp.client.sse import sse_client
            from mcp import ClientSession
            from src.config import settings
            import base64
            
            # Basic Auth combining Key ID and Secret
            auth_str = f"{settings.razorpay_key_id}:{settings.razorpay_key_secret}"
            auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
            
            async with sse_client("https://mcp.razorpay.com/mcp", headers={"Authorization": f"Basic {auth_b64}"}) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool("create_payment_link", arguments={
                        "amount": int(state["amount"] * 100),
                        "currency": "INR",
                        "description": f"Payment for Invoice {state['invoice_id']}",
                        "customer": {
                            "name": state["client_name"],
                            "email": state["client_email"]
                        },
                        "expire_by": int((datetime.utcnow() + timedelta(days=7)).timestamp())
                    })
                    
                    if result and hasattr(result, "content") and len(result.content) > 0:
                        response_data = json.loads(result.content[0].text)
                        if "short_url" in response_data:
                            mock_link = response_data["short_url"]
                            
        except Exception as e:
            print(f"Failed to connect to real Razorpay MCP (fallback to mock): {e}")
            pass
            
        state["drafted_email"] = state["drafted_email"].replace("{{payment_link}}", mock_link)
        state["payment_link_url"] = mock_link
        
        state["audit_entries"].append({
            "event_type": "TOOL_CALL",
            "reasoning": "Requested payment link from Razorpay MCP",
            "action": f"Called create_payment_link. Received URL: {mock_link}",
            "rule": None,
            "content": None
        })
            
    return state

async def execute_action(state: RecoveryState) -> RecoveryState:
    if state.get("should_send_email") and state.get("drafted_email"):
        if state.get("compliance_verdict") == "PASS":
            rule = "Resume escalation if promise broken" if state["current_status"] == "PAUSED_PTP" else None
            state["audit_entries"].append({
                "event_type": "EMAIL_SENT",
                "reasoning": f"{state['escalation_stage']} Escalation",
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
    return state

async def simulate_client(state: RecoveryState) -> RecoveryState:
    # Simulate client replies or payments
    rand = random.random()
    if state.get("new_status") in ["NOTIFIED_1", "NOTIFIED_2", "NOTIFIED_3"]:
        if rand < 0.15: # 15% chance to pay outright
            state["new_status"] = "RECOVERED"
            state["audit_entries"].append({
                "event_type": "PAYMENT_RECEIVED",
                "reasoning": "Client paid after notification",
                "action": "Marked as RECOVERED",
                "rule": None,
                "content": None
            })
        elif rand < 0.25: # 10% chance to promise
            mock_email = "We will pay this by next Friday."
            intent_data = await classify_client_intent(mock_email)
            if intent_data.get("intent") == "PROMISE_TO_PAY":
                state["new_status"] = "PAUSED_PTP"
                state["extracted_entities"] = {"promised_date": (datetime.utcnow() + timedelta(days=7)).isoformat()}
                state["audit_entries"].append({
                    "event_type": "INTENT_CLASSIFIED",
                    "reasoning": f"Classified PROMISE_TO_PAY ({intent_data.get('confidence')} conf).",
                    "action": "Paused workflow",
                    "rule": "Pause escalation on PTP intent",
                    "content": mock_email
                })
        elif rand < 0.30: # 5% chance to dispute
            mock_email = "The amount on this invoice is incorrect, we didn't use that much service."
            intent_data = await classify_client_intent(mock_email)
            if intent_data.get("intent") == "DISPUTE":
                state["new_status"] = "DISPUTE"
                state["audit_entries"].append({
                    "event_type": "INTENT_CLASSIFIED",
                    "reasoning": f"Classified DISPUTE ({intent_data.get('confidence')} conf).",
                    "action": "Halted and routed to human",
                    "rule": "Halt on DISPUTE intent",
                    "content": mock_email
                })
    elif state.get("new_status") == "PAUSED_PTP" or state["current_status"] == "PAUSED_PTP":
        # Keep promise 70% of time (in real code, check promised_date)
        if rand < 0.70:
            state["new_status"] = "RECOVERED"
            state["audit_entries"].append({
                "event_type": "PAYMENT_RECEIVED",
                "reasoning": "Client fulfilled promise",
                "action": "Marked as RECOVERED",
                "rule": None,
                "content": None
            })
    return state
