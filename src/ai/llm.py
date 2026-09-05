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
        temperature=temperature,
        # A tick runs on a clock. An unreachable or unauthorised API should fall
        # back quickly rather than burning the budget on retries that cannot
        # succeed — a 400 invalid_request will never pass on the second attempt.
        max_retries=1,
        timeout=20.0,
    )

def _llm_unavailable(client_name: str = None):
    """
    Returns a reason string when the LLM must not be used, else None.

    Client-aware because of DEMO_FAST: the four written personas get live Claude,
    filler invoices take the deterministic path. Gating only the decision node
    still left ~100 draft and judge calls per tick, each paying full network
    latency before failing.
    """
    if not settings.anthropic_api_key or settings.anthropic_api_key == "your_anthropic_api_key_here":
        return "no ANTHROPIC_API_KEY configured"
    if client_name and settings.demo_fast:
        from src.domain.clients import is_hero
        if not is_hero(client_name):
            return "DEMO_FAST: non-hero invoice"
    return None


def _template_draft(invoice, stage: str, reason: str) -> str:
    """
    Deterministic email used when Claude is unavailable.

    Tagged FALLBACK on the first line so it is visible in the audit trail and in
    the UI: this text is a template, not model output, and must never be shown
    or described as AI-drafted.
    """
    print("[LLM FALLBACK] draft_escalation_email -> template (" + reason + ")")
    return (
        "[FALLBACK DRAFT - template, not AI-generated | " + reason + "]\n"
        "[" + stage + "]\n"
        "Dear " + str(invoice.client_name) + ",\n"
        "Invoice " + str(invoice.id) + " for INR " + str(invoice.amount) + " is overdue. "
        "Please arrange payment.\n"
        "Link: {{payment_link}}"
    )


def _keyword_classify(email_text: str, reason: str) -> dict:
    """
    Keyword intent classification used when Claude is unavailable.

    Tagged with source="keyword_fallback" so callers and the audit trail can tell
    a heuristic apart from a real model classification.
    """
    print("[LLM FALLBACK] classify_client_intent -> keywords (" + reason + ")")
    lower_text = email_text.lower()

    if "dispute" in lower_text or "incorrect" in lower_text or "wrong" in lower_text:
        intent, confidence = "DISPUTE", 0.75
    elif "stop contacting" in lower_text or "unsubscribe" in lower_text or "opt out" in lower_text:
        intent, confidence = "OPT_OUT", 0.75
    elif "lawyer" in lower_text or "attorney" in lower_text or "legal action" in lower_text:
        intent, confidence = "LEGAL_THREAT", 0.75
    elif "extension" in lower_text or "more time" in lower_text:
        intent, confidence = "NEED_EXTENSION", 0.7
    elif "pay" in lower_text and any(
        k in lower_text for k in ("friday", "monday", "next week", "tomorrow", "by the", "end of")
    ):
        intent, confidence = "PROMISE_TO_PAY", 0.7
    elif "partial" in lower_text or "instal" in lower_text:
        intent, confidence = "PARTIAL_PAYMENT", 0.7
    else:
        intent, confidence = "ACKNOWLEDGMENT", 0.5

    return {
        "intent": intent,
        "confidence": confidence,
        # No date is invented here. Phase 1 (D-16) teaches the graph to honour a
        # real extracted date; a hardcoded constant would be worse than nothing.
        "entities": {"promised_date": None, "reason": "keyword heuristic (" + reason + ")"},
        "summary": "Keyword classification: " + intent,
        "source": "keyword_fallback",
        "fallback_reason": reason,
    }


async def draft_escalation_email(invoice, stage: str, previous_context: str = "", retrieved_context: str = "", feedback: str = "") -> str:
    """
    Uses LLM to draft an escalation email based on the current stage and context.
    """
    unavailable = _llm_unavailable(getattr(invoice, 'client_name', None))
    if unavailable:
        return _template_draft(invoice, stage, unavailable)

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
        # A configured key can still fail at request time (no credit, rate
        # limit, network). Surface it loudly, then degrade to the template
        # rather than emitting an error string into a client-facing email.
        return _template_draft(invoice, stage, "LLM call failed: " + type(e).__name__)

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
    unavailable = _llm_unavailable()
    if unavailable:
        return _keyword_classify(email_text, unavailable)

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
            "summary": response.summary,
            "source": "llm",
        }
    except Exception as e:
        print(f"LLM Error classifying intent: {e}")
        # An ERROR intent silently halts the workflow, so fall back to
        # keywords and mark the result as a heuristic.
        return _keyword_classify(email_text, "LLM call failed: " + type(e).__name__)
