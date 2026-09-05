"""
The audited tool layer — every side effect the agent causes flows through here.

D-26: `src/mcp_server/server.py` defines seven well-written tools that nothing ever
called; the graph reached past them into CRUD and RAG directly. This module binds
those same tools for the graph so "our agent acts exclusively through audited tool
calls" is true rather than aspirational.

One deliberate difference from the MCP server: these tools do NOT write to the
database. CLAUDE.md makes `core_loop.py` the sole owner of invoice and audit writes,
and a tool committing its own session from inside a node would break that invariant
and split a tick across several transactions. So state-changing tools record their
intent onto RecoveryState, `core_loop` persists it, and every call — whatever its
kind — is appended to `state["tool_calls"]` and to the audit trail. The external
effects that are genuinely external (payment links, email, Slack) do happen here.
"""

from src.logging_config import get_logger
import httpx

from src.config import settings
from src.integrations import razorpay_client
from src.rag.vector_store import search_client_context as rag_search
from datetime import datetime, timedelta
from typing import Optional



logger = get_logger("revenueguard.tools")

def _record(state: dict, tool: str, args: dict, result: dict, reasoning: str) -> dict:
    """Append an audited tool call to the state and the audit trail."""
    call = {
        "tool": tool,
        "args": args,
        "result": result,
        "at": state.get("virtual_date"),
    }
    state.setdefault("tool_calls", []).append(call)
    state["audit_entries"].append({
        "event_type": "TOOL_CALL",
        "reasoning": reasoning,
        "action": f"{tool}({', '.join(f'{k}={v}' for k, v in args.items() if v is not None)})",
        "rule": "All side effects flow through audited tools",
        "content": None,
    })
    return result


async def create_payment_link(state: dict, amount: float, description: str,
                              discount_pct: Optional[float] = None) -> dict:
    """Create a Razorpay payment link through the official SDK (mock when unconfigured)."""

    link = await razorpay_client.create_payment_link(
        invoice_id=state["invoice_id"],
        amount=amount,
        description=description,
        client_name=state["client_name"],
        client_email=state.get("client_email") or "",
        discount_pct=discount_pct,
    )
    result = {**link, "original_amount": amount}
    return _record(
        state, "create_payment_link",
        {"amount": link["amount"], "description": description, "discount_pct": discount_pct},
        result,
        f"Created a {link['mode']} Razorpay payment link for INR {link['amount']:,.0f}"
        + (f" ({discount_pct}% discount applied)" if discount_pct else ""),
    )


async def create_virtual_account(state: dict) -> dict:
    """Smart Collect virtual account for NEFT/RTGS payers."""

    va = await razorpay_client.create_virtual_account(
        invoice_id=state["invoice_id"],
        client_name=state["client_name"],
        client_email=state.get("client_email") or "",
    )
    state["virtual_account_details"] = va
    return _record(
        state, "create_virtual_account", {},
        va,
        f"Opened a {va['mode']} Smart Collect virtual account for bank transfers",
    )


async def send_email(state: dict, to: str, subject: str, body: str, stage: str) -> dict:
    """Dispatch an escalation email (mock transport; the audit row is the record)."""
    logger.info(f"MOCK EMAIL SENT TO: {to}\nSUBJECT: {subject}\nBODY:\n{body[:400]}")
    result = {"delivered": True, "transport": "mock", "stage": stage}
    return _record(
        state, "send_email",
        {"to": to, "subject": subject, "stage": stage},
        result,
        f"Dispatched the {stage} email to {to}",
    )


async def send_sms(state: dict, to: str, body: str, channel: str) -> dict:
    """Dispatch over an alternative channel after SWITCH_CHANNEL."""
    logger.info(f"MOCK {channel} SENT TO: {to}\n{body[:200]}")
    result = {"delivered": True, "transport": "mock", "channel": channel}
    return _record(
        state, "send_sms",
        {"to": to, "channel": channel},
        result,
        f"Switched channel and sent via {channel}",
    )


async def update_invoice_status(state: dict, new_status: str, reason: str) -> dict:
    """
    Record a status change. core_loop applies it — nodes never write to the DB.
    """
    state["new_status"] = new_status
    result = {"new_status": new_status, "persisted_by": "core_loop"}
    return _record(
        state, "update_invoice_status",
        {"new_status": new_status, "reason": reason},
        result,
        reason,
    )


async def set_promised_date(state: dict, promised_date: str) -> dict:
    """Record a promised payment date for core_loop to persist."""
    state["promised_date"] = promised_date
    result = {"promised_date": promised_date, "persisted_by": "core_loop"}
    return _record(
        state, "set_promised_date",
        {"promised_date": promised_date},
        result,
        f"Recorded a payment commitment for {promised_date[:10]}",
    )


async def notify_slack(state: dict, channel: str, message: str) -> dict:
    """Notify a human channel. Falls back to console when no webhook is set."""
    delivered = "console"
    try:
        webhook = getattr(settings, "slack_webhook_url", None)
        if webhook:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(webhook, json={"text": message})
            delivered = "slack"
        else:
            logger.debug(f"SLACK NOTIFICATION TO {channel}: {message}")
    except Exception as e:
        logger.warning(f"notify_slack: delivery failed ({e}); logged to console")
        logger.debug(f"SLACK NOTIFICATION TO {channel}: {message}")
        delivered = f"console (slack failed: {type(e).__name__})"

    result = {"delivered_via": delivered, "channel": channel}
    return _record(
        state, "notify_slack",
        {"channel": channel},
        result,
        f"Escalated to a human via {delivered}",
    )


async def search_client_context(state: dict, client_name: str, query: str) -> dict:
    """RAG retrieval, recorded as a tool call so retrieval is auditable too."""
    context = await rag_search(client_name, query)
    result = {"chars": len(context), "matched": bool(context)}
    _record(
        state, "search_client_context",
        {"client_name": client_name, "query": query},
        result,
        f"Retrieved {len(context)} characters of client context",
    )
    return {**result, "context": context}


# The bound tool surface available to the graph. Mirrors the MCP server's tools.
TOOL_REGISTRY = {
    "create_payment_link": create_payment_link,
    "create_virtual_account": create_virtual_account,
    "send_email": send_email,
    "send_sms": send_sms,
    "update_invoice_status": update_invoice_status,
    "set_promised_date": set_promised_date,
    "notify_slack": notify_slack,
    "search_client_context": search_client_context,
}
