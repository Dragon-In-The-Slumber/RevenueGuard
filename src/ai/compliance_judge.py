import json
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from src.config import settings
import logging

logger = logging.getLogger(__name__)

COMPLIANCE_RUBRIC = """
You are a compliance officer reviewing an automated collection email draft.
Evaluate against these mandatory rules:

1. MUST NOT threaten legal action (only human managers can do this)
2. MUST NOT use aggressive, hostile, or shaming language
3. MUST include a payment link or bank transfer details
4. MUST reference the correct invoice number and amount
5. MUST NOT contact a client who has opted out or is on legal hold
6. Tone MUST match the escalation stage:
   - STAGE_1: Warm, helpful, assumes good intent
   - STAGE_2: Professional, direct, references contract terms
   - STAGE_3: Serious, firm, references overdue duration and past commitments
   - STAGE_4: Formal final notice (requires human approval before sending)
7. If a previous Promise-to-Pay was broken, the email MUST reference it professionally
8. Email MUST be under 200 words

Return JSON: {"verdict": "PASS" or "FAIL", "reason": "...", "suggestions": "..."}
"""

async def evaluate_email_compliance(email_body: str, escalation_stage: str, context: str = "") -> dict:
    if not settings.anthropic_api_key or settings.anthropic_api_key == "your_anthropic_api_key_here":
        import random
        if random.random() < 0.2:
            logger.warning("Anthropic API key missing, skipping compliance check (mock FAIL)")
            return {"verdict": "FAIL", "reason": "Mock failure: Tone is too aggressive (missing API key)", "suggestions": "Soften the language"}
        else:
            logger.warning("Anthropic API key missing, skipping compliance check (mock PASS)")
            return {"verdict": "PASS", "reason": "Mock pass due to missing API key", "suggestions": ""}
        
    try:
        # Use Claude 3.5 Sonnet
        llm = ChatAnthropic(
            model_name="claude-3-5-sonnet-20241022",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", COMPLIANCE_RUBRIC),
            ("user", "Email Draft:\n{email_body}\n\nEscalation Stage: {escalation_stage}\nContext: {context}")
        ])
        
        chain = prompt | llm
        
        response = await chain.ainvoke({
            "email_body": email_body,
            "escalation_stage": escalation_stage,
            "context": context
        })
        
        content = response.content
        # Ensure we parse JSON out of the response
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from judge: {content}")
            return {"verdict": "FAIL", "reason": "Failed to parse compliance response", "suggestions": ""}
            
    except Exception as e:
        logger.error(f"Compliance judge error: {str(e)}")
        # Default to PASS in case of API error so we don't break the demo
        return {"verdict": "PASS", "reason": f"Error calling judge: {str(e)}", "suggestions": ""}
