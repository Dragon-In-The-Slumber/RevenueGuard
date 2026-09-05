"""
Razorpay integration.

Replaces an MCP call that could never succeed: the old code spoke SSE to
`mcp.razorpay.com` with HTTP Basic auth, but that endpoint is Streamable HTTP and
does not authenticate that way, so every invocation landed in `except` and fell
back to a mock. This uses the official SDK.

When keys are absent the mock path is used deliberately and is labelled `mode:
"mock"` in the returned dict, so a fake link is never presented as a real one.
The SDK is synchronous, so calls run in a thread to avoid blocking the event loop.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from src.config import settings

_client = None


def get_client():
    """Lazily construct the Razorpay client; None when unconfigured."""
    global _client
    if _client is not None:
        return _client
    if not settings.razorpay_configured:
        return None
    try:
        import razorpay
        _client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
        return _client
    except Exception as e:
        print(f"Razorpay client unavailable ({type(e).__name__}: {e}); using mock links")
        return None


def _mock_link(invoice_id: int, amount: float, discount_pct: Optional[float]) -> dict:
    stamp = int(datetime.utcnow().timestamp())
    return {
        "id": f"plink_mock_{invoice_id}_{stamp}",
        "short_url": f"https://rzp.io/l/{invoice_id}_{stamp}",
        "amount": amount,
        "discount_pct": discount_pct,
        "mode": "mock",
    }


async def create_payment_link(invoice_id: int, amount: float, description: str,
                              client_name: str, client_email: str,
                              discount_pct: Optional[float] = None,
                              notes: Optional[dict] = None) -> dict:
    """
    Create a Razorpay payment link. Returns id and short_url separately.

    The two were previously conflated: the full URL was stored in
    `razorpay_payment_link_id` and then rendered as a path segment, producing
    https://rzp.io/l/https://rzp.io/l/42_178860...
    """
    net = round(amount * (1 - (discount_pct or 0) / 100), 2)
    client = get_client()
    if client is None:
        return _mock_link(invoice_id, net, discount_pct)

    payload = {
        "amount": int(round(net * 100)),          # paise
        "currency": "INR",
        "description": description[:255],
        "customer": {"name": client_name, "email": client_email},
        "notify": {"email": False, "sms": False},  # the agent controls messaging
        "reminder_enable": False,
        "notes": {"invoice_id": str(invoice_id), **(notes or {})},
        "callback_url": f"{settings.public_url}/api/webhooks/razorpay",
        "callback_method": "get",
        "expire_by": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
    }

    try:
        link = await asyncio.to_thread(client.payment_link.create, payload)
        return {
            "id": link.get("id"),
            "short_url": link.get("short_url"),
            "amount": net,
            "discount_pct": discount_pct,
            "mode": "live",
        }
    except Exception as e:
        # Surface the failure, then degrade — a broken link must not stop a tick.
        print(f"Razorpay payment_link.create failed ({type(e).__name__}: {e}); using mock")
        result = _mock_link(invoice_id, net, discount_pct)
        result["error"] = f"{type(e).__name__}: {e}"
        return result


async def create_virtual_account(invoice_id: int, client_name: str, client_email: str) -> dict:
    """
    Smart Collect virtual account — a per-invoice bank account for NEFT/RTGS payers.

    Populates `razorpay_virtual_account_id`, a column the schema has always had and
    nothing ever wrote to.
    """
    client = get_client()
    if client is None:
        stamp = int(datetime.utcnow().timestamp())
        return {"id": f"va_mock_{invoice_id}_{stamp}", "mode": "mock"}

    try:
        va = await asyncio.to_thread(client.virtual_account.create, {
            "receivers": {"types": ["bank_account"]},
            "description": f"Invoice {invoice_id} collection account",
            "customer_id": None,
            "notes": {"invoice_id": str(invoice_id), "client": client_name},
        })
        receivers = va.get("receivers") or [{}]
        return {
            "id": va.get("id"),
            "account_number": receivers[0].get("account_number"),
            "ifsc": receivers[0].get("ifsc"),
            "mode": "live",
        }
    except Exception as e:
        print(f"Razorpay virtual_account.create failed ({type(e).__name__}: {e}); using mock")
        stamp = int(datetime.utcnow().timestamp())
        return {"id": f"va_mock_{invoice_id}_{stamp}", "mode": "mock", "error": str(e)}


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify X-Razorpay-Signature.

    Returns True when no secret is configured — local simulation posts unsigned
    events — but main.py refuses unsigned requests whenever a secret IS set, so a
    deployed instance cannot be spoofed.
    """
    if not settings.razorpay_webhook_secret:
        return True
    try:
        import razorpay
        razorpay.Utility.verify_webhook_signature(
            body.decode("utf-8"), signature, settings.razorpay_webhook_secret
        )
        return True
    except Exception as e:
        print(f"Webhook signature rejected: {type(e).__name__}")
        return False
