import json
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Optional
from src.config import settings

def get_llm(temperature=0.7):
    return ChatAnthropic(
        model_name="claude-3-5-sonnet-20241022",
        anthropic_api_key=settings.anthropic_api_key or "dummy-key",
        temperature=temperature
    )

async def draft_escalation_email(invoice, stage: str, previous_context: str = "", retrieved_context: str = "", feedback: str = "") -> str:
    """
    Uses LLM to draft an escalation email based on the current stage and context.
    """
    if not settings.anthropic_api_key or settings.anthropic_api_key == "your_anthropic_api_key_here":
        # Fallback if no API key is provided
        return f"[DRAFT EMAIL: {stage}]\nDear {invoice.client_name},\nYour invoice {invoice.id} for ₹{invoice.amount} is overdue. Please pay immediately.\nLink: {{{{payment_link}}}}"

    feedback_section = f"\nCompliance Feedback to Address:\n{feedback}\n" if feedback else ""

    prompt_template = f"""
You are drafting a follow-up email for an overdue B2B invoice.

Context:
- Invoice ID: {{invoice_id}}
- Client: {{client_name}}
- Amount: ₹{{amount}}
- Due Date: {{due_date}}
- Escalation Stage: {{stage}}
- Previous Interaction: {{previous_context}}

Additional RAG Client Context (from past history):
{{retrieved_context}}
{feedback_section}
Write a professional email appropriate for this escalation stage. Do NOT threaten legal action. Keep it under 200 words. Include a direct payment link placeholder: {{{{payment_link}}}}.
"""
    try:
        llm = get_llm(temperature=0.7)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI assistant specializing in B2B accounts receivable."),
            ("user", prompt_template)
        ])
        chain = prompt | llm
        
        response = await chain.ainvoke({
            "invoice_id": invoice.id,
            "client_name": invoice.client_name,
            "amount": invoice.amount,
            "due_date": invoice.due_date.strftime('%Y-%m-%d') if hasattr(invoice.due_date, 'strftime') else invoice.due_date,
            "stage": stage,
            "previous_context": previous_context,
            "retrieved_context": retrieved_context
        })
        return response.content.strip()
    except Exception as e:
        print(f"LLM Error drafting email: {e}")
        return f"[ERROR DRAFTING EMAIL: {e}]"

class IntentClassification(BaseModel):
    intent: str = Field(description="One of: PROMISE_TO_PAY, DISPUTE, NEED_EXTENSION, PARTIAL_PAYMENT, ACKNOWLEDGMENT, OPT_OUT, LEGAL_THREAT, UNRELATED")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    promised_date: Optional[str] = Field(description="The date the client commits to paying (ISO 8601 format), if applicable", default=None)
    reason: Optional[str] = Field(description="A brief summary of the client's stated reason, if applicable", default=None)
    summary: str = Field(description="Brief summary of the email")

async def classify_client_intent(email_text: str) -> dict:
    """
    Uses LLM to classify the client's intent from an email reply using structured output.
    """
    if not settings.anthropic_api_key or settings.anthropic_api_key == "your_anthropic_api_key_here":
        # Mock parsing logic based on keywords for demo purposes without API key
        lower_text = email_text.lower()
        if "pay" in lower_text and ("friday" in lower_text or "next week" in lower_text or "tomorrow" in lower_text):
            return {"intent": "PROMISE_TO_PAY", "confidence": 0.9, "entities": {"promised_date": "2024-11-15", "reason": "Keyword mock"}}
        elif "wrong" in lower_text or "dispute" in lower_text or "incorrect" in lower_text:
            return {"intent": "DISPUTE", "confidence": 0.95, "entities": {"reason": "Keyword mock"}}
        elif "stop" in lower_text or "lawyer" in lower_text:
            return {"intent": "OPT_OUT", "confidence": 0.9, "entities": {}}
        return {"intent": "ACKNOWLEDGMENT", "confidence": 0.8, "entities": {}}

    prompt_template = """
You are an AI assistant specializing in B2B accounts receivable. Analyze the 
following email reply from a client regarding an overdue invoice:

"{email_text}"

Classify the client's intent and extract entities.
"""
    try:
        llm = get_llm(temperature=0.0).with_structured_output(IntentClassification)
        prompt = ChatPromptTemplate.from_messages([
            ("user", prompt_template)
        ])
        chain = prompt | llm
        
        response = await chain.ainvoke({"email_text": email_text})
        
        return {
            "intent": response.intent,
            "confidence": response.confidence,
            "entities": {
                "promised_date": response.promised_date,
                "reason": response.reason
            },
            "summary": response.summary
        }
    except Exception as e:
        print(f"LLM Error classifying intent: {e}")
        return {"intent": "ERROR", "confidence": 0.0, "entities": {}, "summary": str(e)}
