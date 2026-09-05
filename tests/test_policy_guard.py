"""One test per policy-guard rule (Phase 2, spec 5.4).

The guard is what makes "bounded autonomy" a fact rather than a claim, so each
rule is asserted on both the veto and the substitution it applies.
"""
import pytest

from src.domain.clients import get_profile, profile_as_dict
from src.graph import policy_guard
from src.graph.policy_guard import HIGH_VALUE_THRESHOLD, MAX_INSTALMENTS, MAX_WAIT_DAYS


def ctx(client="Globex Solutions", *, status="NOTIFIED_1", stage="STAGE_1",
        days_since=9, amount=340000.0):
    return {
        "invoice_id": 1, "client_name": client, "amount": amount,
        "current_status": status, "escalation_stage": stage,
        "days_since_contact": days_since, "contact_attempts": 1,
        "profile": profile_as_dict(get_profile(client)),
    }


def rule_numbers(verdict):
    return {v["rule_number"] for v in verdict.vetoes}


def test_rule1_cooldown_substitutes_wait():
    v = policy_guard.validate({"action": "SEND_EMAIL", "stage": "STAGE_2"}, ctx(days_since=2))
    assert 1 in rule_numbers(v)
    assert v.action["action"] == "WAIT"


def test_rule2_cannot_skip_more_than_one_stage():
    v = policy_guard.validate({"action": "SEND_EMAIL", "stage": "STAGE_3"},
                              ctx("Pinnacle Industries", stage="STAGE_1", amount=100000.0))
    assert 2 in rule_numbers(v)
    assert v.action["stage"] == "STAGE_2"


def test_rule3_discount_above_authority_goes_to_human():
    """The demo beat: 25% proposed on Globex against a 10% authority."""
    v = policy_guard.validate({"action": "OFFER_DISCOUNT", "discount_pct": 25.0, "stage": "STAGE_2"}, ctx())
    assert 3 in rule_numbers(v)
    assert v.action["action"] == "ESCALATE_TO_HUMAN"


def test_rule3_discount_within_authority_is_allowed():
    v = policy_guard.validate({"action": "OFFER_DISCOUNT", "discount_pct": 10.0, "stage": "STAGE_2"}, ctx())
    assert v.validated


def test_rule4_high_value_invoice_allows_only_a_plain_email():
    v = policy_guard.validate({"action": "OFFER_DISCOUNT", "discount_pct": 0.0, "stage": "STAGE_2"},
                              ctx("Pinnacle Industries", amount=HIGH_VALUE_THRESHOLD + 1))
    assert 4 in rule_numbers(v)
    assert v.action["action"] == "ESCALATE_TO_HUMAN"


def test_rule5_legal_hold_blocks_everything():
    v = policy_guard.validate({"action": "SEND_EMAIL", "stage": "STAGE_2"},
                              ctx("Acme Corp", status="LEGAL_HOLD"))
    assert 5 in rule_numbers(v)
    assert v.action["action"] == "WAIT"


def test_rule5_takes_precedence_over_every_other_rule():
    """A hard block must not be diluted by later substitutions."""
    v = policy_guard.validate({"action": "OFFER_DISCOUNT", "discount_pct": 99.0, "stage": "STAGE_4"},
                              ctx("Acme Corp", status="UNRESPONSIVE"))
    assert rule_numbers(v) == {5}


def test_rule6_stage4_always_requires_a_human():
    v = policy_guard.validate({"action": "SEND_EMAIL", "stage": "STAGE_4"},
                              ctx("Pinnacle Industries", stage="STAGE_3", amount=100000.0))
    assert 6 in rule_numbers(v)
    assert v.action["action"] == "ESCALATE_TO_HUMAN"


def test_rule7_wait_is_clamped():
    v = policy_guard.validate({"action": "WAIT", "wait_days": 60}, ctx("Acme Corp", days_since=12))
    assert 7 in rule_numbers(v)
    assert v.action["wait_days"] == MAX_WAIT_DAYS


def test_rule8_instalments_are_clamped():
    v = policy_guard.validate({"action": "OFFER_PAYMENT_PLAN", "instalments": 6, "stage": "STAGE_2"}, ctx())
    assert 8 in rule_numbers(v)
    assert v.action["instalments"] == MAX_INSTALMENTS


def test_rule8_payment_plan_refused_for_clients_without_authority():
    v = policy_guard.validate({"action": "OFFER_PAYMENT_PLAN", "instalments": 2, "stage": "STAGE_2"},
                              ctx("Acme Corp", days_since=12))
    assert v.action["action"] == "ESCALATE_TO_HUMAN"


def test_rule9_stage_above_client_autonomy_limit():
    """Acme caps at STAGE_2 by profile, below the global STAGE_4 gate."""
    v = policy_guard.validate({"action": "SEND_EMAIL", "stage": "STAGE_3"},
                              ctx("Acme Corp", stage="STAGE_2", days_since=12))
    assert 9 in rule_numbers(v)
    assert v.action["action"] == "ESCALATE_TO_HUMAN"


def test_a_permitted_action_passes_untouched():
    v = policy_guard.validate({"action": "SEND_EMAIL", "stage": "STAGE_2"}, ctx())
    assert v.validated
    assert v.vetoes == []
    assert v.action == v.original


def test_every_veto_names_rule_proposal_and_substitute():
    """The audit row is the deliverable; a veto missing these is not auditable."""
    v = policy_guard.validate({"action": "OFFER_DISCOUNT", "discount_pct": 25.0, "stage": "STAGE_2"}, ctx())
    veto = v.vetoes[0]
    assert veto["rule"] and veto["detail"]
    assert veto["proposed"]["action"] == "OFFER_DISCOUNT"
    assert veto["substitute"]
