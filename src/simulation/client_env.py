"""
THE SIMULATED CLIENT ENVIRONMENT — NOT AGENT LOGIC.

This module rolls dice to decide how a synthetic client responds to what the agent
did. It is the system under test's *environment*, not the system under test. Its
output must never be presented or described as agent performance.

Why it exists as its own module: `simulate_client` used to be a node inside the
production LangGraph, wired between `execute_action` and `END`, and it appeared in
the React-Flow visualiser shown to judges. That put the environment inside the
agent, with no separation between the thing being measured and the thing doing the
measuring.

Why the outcome now depends on the agent's choice: the old version drew from flat
constants (15% pay / 10% promise / 5% dispute) keyed only on status. Change the
email quality, the escalation ladder or the compliance judge and the recovery
number was identical — the headline metric was independent of the agent, which
undercuts the whole claim. Here:

    p(pay) = persona.base_pay_rate
           x stage_multiplier[stage]
           x action_multiplier[action, persona]
           x relationship_score

so knowing when *not* to act is worth measurable money, which is exactly what the
A/B in `runner.py` is built to demonstrate.
"""

import hashlib
import random
from datetime import datetime, timedelta
from typing import Optional

from src.domain.clients import get_profile, stage_rank

# Later stages carry more weight, with diminishing returns.
STAGE_MULTIPLIER = {
    "STAGE_1": 1.0,
    "STAGE_2": 1.25,
    "STAGE_3": 1.45,
    "STAGE_4": 1.5,
}

# Over-escalation costs this much relationship score per incident.
RELATIONSHIP_PENALTY = 0.15


def invoice_identity(state: dict) -> str:
    """
    A stable identity for an invoice, reproducible across runs.

    Deliberately NOT the primary key: `id` is a database autoincrement that keeps
    climbing after a reset, so run 2 of the same seed would draw entirely
    different dice from run 1 and the "run it again" claim would be false.
    Client, amount and due date are all reproducible from the seed.
    """
    return f"{state.get('client_name')}|{state.get('amount')}|{(state.get('due_date') or '')[:10]}"


def derive_rng(seed: int, identity: str, virtual_date: str, salt: str = "") -> random.Random:
    """
    A deterministic RNG for one (invoice, day) pair.

    A single shared Random() would make results depend on the order asyncio
    happened to interleave concurrent invoices — so the same seed would give a
    different number every run, defeating the whole point. Deriving per
    (seed, identity, day) makes the outcome independent of execution order.
    """
    key = f"{seed}:{identity}:{virtual_date}:{salt}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    return random.Random(int(digest[:16], 16))


def action_multiplier(action: Optional[str], profile, discount_pct: float = 0.0,
                      instalments: int = 0) -> tuple[float, str]:
    """
    How much the agent's chosen intervention moves this particular client.

    Returns (multiplier, explanation). The explanation goes into the audit trail so
    the environment's behaviour is inspectable rather than a black box.
    """
    if action == "OFFER_DISCOUNT":
        # Scales with the size of the discount, capped so it cannot dominate.
        strength = 1.0 + (profile.discount_sensitivity - 1.0) * min(discount_pct / 10.0, 1.5)
        return strength, f"{discount_pct:.0f}% discount, sensitivity {profile.discount_sensitivity}"

    if action == "OFFER_PAYMENT_PLAN":
        return profile.plan_sensitivity, (
            f"{instalments or 3}-instalment plan, sensitivity {profile.plan_sensitivity}"
        )

    if action == "SPLIT_INVOICE":
        # Unlocks the undisputed portion for a client whose contract demands it.
        if profile.requires_split_billing:
            return 2.2, "split billing matches this client's contract terms"
        return 1.1, "split billing offered but not required by contract"

    if action == "SWITCH_CHANNEL":
        return 1.3, "alternative channel reaches a client ignoring email"

    if action == "WAIT":
        # Patience works on reliable payers and does nothing for a ghost.
        if profile.base_pay_rate >= 0.25:
            return 1.4, "reliable payer left to their own approval cycle"
        return 0.35, "waiting on an unreliable payer rarely produces payment"

    if action == "SEND_EMAIL":
        return 1.0, "standard escalation email"

    return 0.0, "no outreach"


def simulate_response(state: dict, seed: int) -> dict:
    """
    Roll the client's response to what the agent just did.

    Returns a dict describing the outcome; the caller records it. Pure apart from
    the seeded RNG, so it can run inside the concurrent tick.
    """
    profile = get_profile(state["client_name"])
    action_obj = state.get("effective_action") or {}
    action = action_obj.get("action")
    stage = state.get("escalation_stage") or "STAGE_1"
    relationship = state.get("relationship_score", 1.0)

    rng = derive_rng(seed, invoice_identity(state), state.get("virtual_date") or "", "response")

    stage_mult = STAGE_MULTIPLIER.get(stage, 1.0)
    act_mult, act_note = action_multiplier(
        action, profile,
        discount_pct=action_obj.get("discount_pct") or 0.0,
        instalments=action_obj.get("instalments") or 0,
    )

    p_pay = min(0.95, profile.base_pay_rate * stage_mult * act_mult * relationship)

    outcome = {
        "outcome": "NO_RESPONSE",
        "p_pay": round(p_pay, 4),
        "explanation": (
            f"base {profile.base_pay_rate} x stage {stage_mult} x action {act_mult:.2f} "
            f"({act_note}) x relationship {relationship} = {p_pay:.3f}"
        ),
        "new_status": None,
        "promised_date": None,
        "reply_text": None,
    }

    roll = rng.random()
    if roll < p_pay:
        outcome.update(outcome_paid(action_obj, profile))
        return outcome

    # Not paying. Distribute the remainder across promise / dispute / silence.
    remaining = max(0.0, 1.0 - p_pay)
    p_ptp = remaining * profile.ptp_rate
    p_dispute = remaining * profile.dispute_rate

    if roll < p_pay + p_ptp:
        virtual_now = datetime.fromisoformat(state["virtual_date"])
        days = rng.randint(3, 10)
        outcome.update({
            "outcome": "PROMISED",
            "new_status": "PAUSED_PTP",
            "promised_date": (virtual_now + timedelta(days=days)).isoformat(),
            "reply_text": f"We will settle this invoice within {days} days.",
        })
        return outcome

    if roll < p_pay + p_ptp + p_dispute:
        outcome.update({
            "outcome": "DISPUTED",
            "new_status": "DISPUTE",
            "reply_text": "The amount billed does not match our records; we are disputing this.",
        })
        return outcome

    return outcome


def outcome_paid(action_obj: dict, profile) -> dict:
    """Full or partial payment, depending on what was offered."""
    action = action_obj.get("action")
    if action == "SPLIT_INVOICE" and profile.requires_split_billing:
        return {
            "outcome": "PARTIAL_PAID",
            "new_status": "RECOVERED",
            "reply_text": "Paying the undisputed portion now; the remainder is under review.",
        }
    return {"outcome": "PAID", "new_status": "RECOVERED", "reply_text": None}


def resolve_promise(state: dict, seed: int) -> bool:
    """
    Does the client honour a promise whose date has arrived?

    Globex breaks 55% of theirs, NovaTech 60% — both taken from their written
    profiles, which is what makes a broken promise a persona trait rather than a
    coin flip.
    """
    profile = get_profile(state["client_name"])
    rng = derive_rng(seed, invoice_identity(state), state.get("virtual_date") or "", "promise")
    return rng.random() >= profile.ptp_break_rate


def relationship_damage(state: dict) -> tuple[float, Optional[str]]:
    """
    The cost of over-escalation.

    Without this the optimal policy is "escalate maximally, always" and a fixed
    ladder ties the agent. With it, restraint is worth money — which is the whole
    point of the A/B.
    """
    profile = get_profile(state["client_name"])
    stage = state.get("escalation_stage")
    if stage_rank(stage) > stage_rank(profile.max_autonomous_stage):
        return (
            RELATIONSHIP_PENALTY,
            f"{stage} exceeds {profile.name}'s tolerance of "
            f"{profile.max_autonomous_stage}; relationship damaged",
        )
    return 0.0, None
