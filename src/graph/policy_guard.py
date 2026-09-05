"""
The policy guard — bounded autonomy, enforced.

The Compliance Officer used to review prose after the fact. It now vetoes *choices*
before they happen. Nine hard rules; each veto names the proposed action, the rule
that blocked it, and what was substituted, so "the agent proposed a 25% discount on
Globex, policy caps autonomous discounts at 10%, so it was blocked and routed to a
human" becomes a provable statement rather than a gauge reading 100%.

Pure functions: no I/O, no database. Returns a verdict for the node to record.
"""

from typing import Optional

from src.domain.clients import stage_rank

# Rule 1: outreach cooldown, in virtual days.
CONTACT_COOLDOWN_DAYS = 4
# Rule 4: above this value, anything cleverer than a plain email needs a person.
HIGH_VALUE_THRESHOLD = 5_000_000
# Rule 7 / rule 8 clamps.
MAX_WAIT_DAYS = 14
MAX_INSTALMENTS = 3

SENDING_ACTIONS = {"SEND_EMAIL", "OFFER_DISCOUNT", "OFFER_PAYMENT_PLAN", "SPLIT_INVOICE", "SWITCH_CHANNEL"}


class GuardVerdict:
    def __init__(self, action: dict):
        self.action = dict(action)
        self.original = dict(action)
        self.vetoes: list[dict] = []

    @property
    def validated(self) -> bool:
        return not self.vetoes

    def veto(self, rule_number: int, rule: str, substitute: dict, detail: str) -> None:
        """Record a veto and apply the substitute."""
        self.vetoes.append({
            "rule_number": rule_number,
            "rule": rule,
            "proposed": {
                "action": self.action.get("action"),
                "stage": self.action.get("stage"),
                "discount_pct": self.action.get("discount_pct"),
                "instalments": self.action.get("instalments"),
                "wait_days": self.action.get("wait_days"),
            },
            "substitute": substitute,
            "detail": detail,
        })
        self.action.update(substitute)


def validate(action: dict, ctx: dict) -> GuardVerdict:
    """Apply the nine rules in order. Later rules see earlier substitutions."""
    v = GuardVerdict(action)
    profile = ctx.get("profile") or {}
    status = ctx.get("current_status")
    days_since = ctx.get("days_since_contact")
    amount = ctx.get("amount") or 0

    # --- Rule 5 first: a hard block overrides everything else ---
    if status in ("LEGAL_HOLD", "UNRESPONSIVE") or ctx.get("opted_out"):
        if v.action.get("action") != "WAIT":
            v.veto(
                5,
                "No contact permitted on LEGAL_HOLD or after opt-out",
                {"action": "WAIT", "wait_days": MAX_WAIT_DAYS, "stage": None,
                 "discount_pct": None, "instalments": None},
                f"Invoice is {status}; all outreach is suppressed permanently.",
            )
        return v

    # --- Rule 6: STAGE_4 always needs a person ---
    if v.action.get("stage") == "STAGE_4":
        v.veto(
            6,
            "STAGE_4 always requires human approval",
            {"action": "ESCALATE_TO_HUMAN", "stage": "STAGE_4"},
            "A formal final notice may not be sent autonomously.",
        )

    # --- Rule 9: stage above the client's autonomous limit ---
    max_stage = profile.get("max_autonomous_stage", "STAGE_4")
    proposed_stage = v.action.get("stage")
    if proposed_stage and stage_rank(proposed_stage) > stage_rank(max_stage):
        v.veto(
            9,
            f"Stage exceeds this client's autonomous limit of {max_stage}",
            {"action": "ESCALATE_TO_HUMAN"},
            f"{proposed_stage} is beyond {max_stage} for {profile.get('name', 'this client')}.",
        )

    # --- Rule 2: cannot skip more than one escalation stage ---
    current_rank = stage_rank(ctx.get("escalation_stage") or "STAGE_1")
    if v.action.get("stage") and v.action.get("action") in SENDING_ACTIONS:
        proposed_rank = stage_rank(v.action["stage"])
        if proposed_rank > current_rank + 1:
            clamped = ["STAGE_1", "STAGE_2", "STAGE_3", "STAGE_4"][min(current_rank + 1, 3)]
            v.veto(
                2,
                "Cannot skip more than one escalation stage",
                {"stage": clamped},
                f"Proposed {v.action['stage']} from {ctx.get('escalation_stage')}; clamped to {clamped}.",
            )

    # --- Rule 1: outreach cooldown ---
    if v.action.get("action") in SENDING_ACTIONS and days_since is not None \
            and days_since < CONTACT_COOLDOWN_DAYS:
        v.veto(
            1,
            f"Max 1 contact per {CONTACT_COOLDOWN_DAYS} days",
            {"action": "WAIT", "wait_days": CONTACT_COOLDOWN_DAYS - days_since,
             "stage": None, "discount_pct": None, "instalments": None},
            f"Last contact was {days_since} day(s) ago.",
        )

    # --- Rule 3: discount above the client's authority ---
    authority = profile.get("discount_authority_pct", 0.0)
    proposed_discount = v.action.get("discount_pct")
    if proposed_discount is not None and proposed_discount > authority:
        v.veto(
            3,
            f"Discount exceeds autonomous authority of {authority}%",
            {"action": "ESCALATE_TO_HUMAN", "discount_pct": proposed_discount},
            f"Proposed {proposed_discount}% against an authority of {authority}%.",
        )

    # --- Rule 4: high-value invoices allow only a plain email ---
    if amount > HIGH_VALUE_THRESHOLD and v.action.get("action") in SENDING_ACTIONS \
            and v.action.get("action") != "SEND_EMAIL":
        v.veto(
            4,
            f"Invoices above INR {HIGH_VALUE_THRESHOLD:,} allow only a standard email autonomously",
            {"action": "ESCALATE_TO_HUMAN"},
            f"INR {amount:,.0f} exceeds the high-value threshold.",
        )

    # --- Rule 8: instalment cap ---
    instalments = v.action.get("instalments")
    if instalments is not None and instalments > MAX_INSTALMENTS:
        v.veto(
            8,
            f"No more than {MAX_INSTALMENTS} instalments",
            {"instalments": MAX_INSTALMENTS},
            f"Proposed {instalments} instalments.",
        )

    # Payment plans are not open to every client.
    if v.action.get("action") == "OFFER_PAYMENT_PLAN" and not profile.get("allow_payment_plan"):
        v.veto(
            8,
            "Payment plans are not permitted for this client",
            {"action": "ESCALATE_TO_HUMAN"},
            f"{profile.get('name', 'This client')} is not approved for instalments.",
        )

    # --- Rule 7: wait cap ---
    wait_days = v.action.get("wait_days")
    if wait_days is not None and wait_days > MAX_WAIT_DAYS:
        v.veto(
            7,
            f"WAIT may not exceed {MAX_WAIT_DAYS} days",
            {"wait_days": MAX_WAIT_DAYS},
            f"Proposed a {wait_days}-day wait.",
        )

    return v
