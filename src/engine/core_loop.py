import random
from sqlalchemy.ext.asyncio import AsyncSession
from src.persistence.crud import get_actionable_invoices, log_audit_event, get_last_email_date, get_last_audit_event_type
from src.ai.llm import draft_escalation_email, classify_client_intent
from src.persistence.models import InvoiceStatus
from datetime import datetime, timedelta

from src.graph.builder import compiled_graph

async def process_simulation_tick(db: AsyncSession, virtual_date: datetime):
    """
    Advances the simulation by one day using LangGraph. Processes all actionable invoices.
    """
    invoices = await get_actionable_invoices(db)
    processed_count = 0
    
    for invoice in invoices:
        # Initialize graph state
        initial_state = {
            "invoice_id": invoice.id,
            "client_name": invoice.client_name,
            "client_email": invoice.client_email,
            "amount": invoice.amount,
            "due_date": invoice.due_date.isoformat(),
            "current_status": invoice.status.value if hasattr(invoice.status, "value") else invoice.status,
            "days_overdue": (virtual_date - invoice.due_date).days,
            "escalation_stage": "STAGE_1",
            "client_reply": None,
            "classified_intent": None,
            "intent_confidence": None,
            "extracted_entities": None,
            "retrieved_context": None,
            "drafted_email": None,
            "compliance_verdict": None,
            "compliance_reason": None,
            "compliance_retries": 0,
            "payment_link_url": None,
            "virtual_account_details": None,
            "action_taken": None,
            "new_status": None,
            "rule_applied": None,
            "audit_entries": [],
            "should_send_email": True
        }

        # Run the graph
        final_state = await compiled_graph.ainvoke(initial_state)

        # Apply DB changes
        if final_state.get("new_status"):
            invoice.status = InvoiceStatus(final_state["new_status"])
        
        if final_state.get("extracted_entities") and "promised_date" in final_state["extracted_entities"]:
            invoice.promised_date = datetime.fromisoformat(final_state["extracted_entities"]["promised_date"])

        # Write audit logs
        for entry in final_state.get("audit_entries", []):
            await log_audit_event(
                db, 
                invoice.id, 
                entry["event_type"], 
                entry["reasoning"], 
                entry["action"], 
                virtual_date, 
                rule_applied=entry.get("rule"), 
                content_snapshot=entry.get("content")
            )
            processed_count += 1

    await db.commit()
    return processed_count
