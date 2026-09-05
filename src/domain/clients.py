"""
The single source of truth for who our clients are and what the agent may do to them.

Before this module the roster existed in four places that disagreed: `rag/seed_data.py`,
`crud.generate_fake_invoices`, the hardcoded overrides in `dashboard_api.get_clients`
(which invented "Initech" and "Soylent Corp"), and a query router in the frontend. ChromaDB,
the invoice generator, and `/api/clients` are all seeded from here now.

The policy fields are not decoration: Phase 2's `decide_action` reads them to choose an
intervention, and `validate_action` reads them to veto one. Each value is derived from the
prose in `narrative` — that prose is what the RAG retrieval returns, so the numbers the
guard enforces and the story the model reads cannot drift apart.
"""

from dataclasses import dataclass, field
from typing import List, Literal, Optional

Tier = Literal["Enterprise", "Mid-Market", "SMB", "Standard"]
Risk = Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
Stage = Literal["STAGE_1", "STAGE_2", "STAGE_3", "STAGE_4"]


@dataclass(frozen=True)
class ClientProfile:
    # --- identity ---
    name: str
    email: str
    tier: Tier
    contact: str
    terms: str
    risk_level: Risk
    is_hero: bool = True

    # --- policy the agent and the guard read ---
    # Highest stage the agent may reach without a human. Above this -> ESCALATE_TO_HUMAN.
    max_autonomous_stage: Stage = "STAGE_3"
    # Largest early-payment discount the agent may offer unilaterally, in percent.
    discount_authority_pct: float = 0.0
    allow_payment_plan: bool = False
    # True when undisputed and disputed portions must be billed on separate links.
    requires_split_billing: bool = False
    # How long to let a silence run before escalating, in virtual days.
    escalation_patience_days: int = 4
    # Annual relationship value in rupees; scales the cost of damaging the relationship.
    relationship_value: int = 0
    guardrails: List[str] = field(default_factory=list)

    # --- demo seeding ---
    seed_amount: int = 0
    seed_days_overdue: int = 0

    # --- RAG document ---
    narrative: str = ""


HERO_CLIENTS: List[ClientProfile] = [
    ClientProfile(
        name="Acme Corp",
        email="finance@acmecorp.com",
        tier="Enterprise",
        contact="Rajesh Kumar, Finance Manager (rajesh.kumar@acme.com)",
        terms="Net-60",
        risk_level="LOW",
        # "Never threaten legal action - Tier 1 client worth Rs 2Cr annually."
        max_autonomous_stage="STAGE_2",
        discount_authority_pct=0.0,
        allow_payment_plan=False,
        requires_split_billing=False,
        # "Delays usually due to internal approval cycles, not cash flow" - patience pays.
        escalation_patience_days=11,
        relationship_value=20_000_000,
        guardrails=[
            "Never threaten legal action - Tier 1 client worth Rs 2Cr annually.",
            "Delays are internal approval cycles, not cash flow. Waiting is usually correct.",
            "CC accounts@acme.com for invoices over Rs 5,00,000.",
        ],
        seed_amount=1_250_000,
        seed_days_overdue=22,
        narrative="""
- Company: Acme Corp (Fortune 500 Manufacturing)
- Contract: Master Service Agreement dated Jan 2024. Net-60 payment terms.
- Key Contact: Rajesh Kumar, Finance Manager (rajesh.kumar@acme.com)
- Payment History: 12 invoices in last 12 months. 10 paid on time. 2 paid 5-8 days late.
- Notes: Very reliable. Delays usually due to internal approval cycles, not cash flow.
  Never threaten legal action - they are a Tier 1 client worth Rs 2Cr annually.
- Preferred Channel: Email. CC to accounts@acme.com for invoices > Rs 5,00,000.
""",
    ),
    ClientProfile(
        name="Globex Solutions",
        email="accounts@globexsolutions.com",
        tier="Mid-Market",
        contact="Priya Mehta, Head of Finance (priya@globex.io)",
        terms="Net-30",
        risk_level="HIGH",
        # "Escalate to human after Stage 2."
        max_autonomous_stage="STAGE_2",
        discount_authority_pct=10.0,
        allow_payment_plan=True,
        requires_split_billing=False,
        escalation_patience_days=4,
        relationship_value=3_400_000,
        guardrails=[
            "Escalate to a human after Stage 2.",
            "Has broken two Promise-to-Pay commitments in 2024. Treat new promises with scepticism.",
            "Firm but professional tone. 1.5% monthly late fee clause may be cited.",
        ],
        seed_amount=340_000,
        seed_days_overdue=12,
        narrative="""
- Company: Globex Solutions (Series B SaaS Startup, 150 employees)
- Contract: Service Agreement dated Mar 2024. Net-30 payment terms. 1.5% monthly late fee clause.
- Key Contact: Priya Mehta, Head of Finance (priya@globex.io)
- Payment History: 6 invoices in last 8 months. 2 paid on time. 3 paid 15-25 days late.
  1 still outstanding (INV-2024-0612, Rs 3,40,000, 45 days overdue).
- Past Disputes: Disputed INV-2024-0489 ("Wrong quantity billed for API calls"). Resolved
  in 8 days after credit note of Rs 12,000.
- Notes: HIGH RISK. Has broken two Promise-to-Pay commitments in 2024 (promised Oct 15,
  paid Nov 3; promised Jul 20, paid Aug 8). Cash flow constrained - "budget cycle" is
  frequently cited. Requires firm but professional tone. Escalate to human after Stage 2.
""",
    ),
    ClientProfile(
        name="Pinnacle Industries",
        email="ap@pinnacleindustries.com",
        tier="Enterprise",
        contact="Vikram Singh, VP Finance (v.singh@pinnacle.co.in)",
        terms="Net-45",
        risk_level="MEDIUM",
        max_autonomous_stage="STAGE_3",
        discount_authority_pct=0.0,
        allow_payment_plan=False,
        # "Do NOT combine Milestone 1 and 2 in a single payment link."
        requires_split_billing=True,
        escalation_patience_days=6,
        relationship_value=15_000_000,
        guardrails=[
            "Do NOT combine Milestone 1 and 2 in a single payment link. Issue separate "
            "links for undisputed and disputed portions.",
            "VP Singh responds only to Stage 2+ emails.",
            "Prefers formal language with contract clause references.",
        ],
        seed_amount=7_500_000,
        seed_days_overdue=45,
        narrative="""
- Company: Pinnacle Industries (Listed Conglomerate, 5000+ employees)
- Contract: Annual Retainer Agreement. Net-45 terms. Auto-renewal clause.
- Key Contact: Vikram Singh, VP Finance (v.singh@pinnacle.co.in)
- Payment History: 8 invoices. 5 paid on time. 3 disputed (2 resolved, 1 pending).
- Past Disputes: Pattern of disputing consulting hours (Milestone 2 charges).
  Always accepts Milestone 1 (deliverables). Average dispute resolution: 12 days.
- Notes: Do NOT combine Milestone 1 and 2 in a single payment link. Issue separate
  links for undisputed and disputed portions. VP Singh responds only to Stage 2+ emails.
  Prefers formal language with contract clause references.
""",
    ),
    ClientProfile(
        name="NovaTech Labs",
        email="arjun@novatechlabs.com",
        tier="SMB",
        contact="Arjun Patel, CEO (arjun@novatech.ai)",
        terms="Net-15",
        risk_level="EXTREME",
        # "After Stage 2, escalate to human immediately."
        max_autonomous_stage="STAGE_2",
        # "Consider offering a 10% early payment discount."
        discount_authority_pct=10.0,
        allow_payment_plan=True,
        requires_split_billing=False,
        escalation_patience_days=3,
        relationship_value=240_000,
        guardrails=[
            "After Stage 2, escalate to a human immediately - do not waste further "
            "automated outreach.",
            "Consider a 10% early payment discount to accelerate recovery of whatever is possible.",
            "CEO is the only contact. No finance team.",
        ],
        seed_amount=80_000,
        seed_days_overdue=35,
        narrative="""
- Company: NovaTech Labs (Seed-stage AI startup, 12 employees)
- Contract: Project-based SOW. Net-15 payment terms. No late fee clause.
- Key Contact: Arjun Patel, CEO (arjun@novatech.ai)
- Payment History: 3 invoices. 1 paid on time. 2 ghosted (no response to any
  communication for 30+ days).
- Notes: EXTREME HIGH RISK. Company may be running out of runway. CEO is the only
  contact. No finance team. After Stage 2, escalate to human immediately - do not
  waste further automated outreach. Consider offering a 10% early payment discount
  to accelerate recovery of whatever is possible.
""",
    ),
]

# Applied to Faker-generated filler invoices, which have no written profile.
DEFAULT_PROFILE = ClientProfile(
    name="",
    email="",
    tier="Standard",
    contact="billing@company.com",
    terms="Net-30",
    risk_level="MEDIUM",
    is_hero=False,
    max_autonomous_stage="STAGE_3",
    discount_authority_pct=5.0,
    allow_payment_plan=False,
    requires_split_billing=False,
    escalation_patience_days=4,
    relationship_value=0,
    guardrails=["No written profile on file. Apply standard collections policy."],
)

_BY_NAME = {p.name: p for p in HERO_CLIENTS}

# The order the escalation ladder climbs, used to compare against max_autonomous_stage.
STAGE_ORDER: List[str] = ["STAGE_1", "STAGE_2", "STAGE_3", "STAGE_4"]


def get_profile(client_name: str) -> ClientProfile:
    """Profile for a client, falling back to the standard policy for filler invoices."""
    hero = _BY_NAME.get(client_name)
    if hero:
        return hero
    return ClientProfile(
        **{
            **DEFAULT_PROFILE.__dict__,
            "name": client_name,
            "email": DEFAULT_PROFILE.contact,
        }
    )


def is_hero(client_name: str) -> bool:
    return client_name in _BY_NAME


def stage_rank(stage: Optional[str]) -> int:
    """Position of a stage in the ladder; -1 for anything unrecognised."""
    if not stage:
        return -1
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return -1


def profile_as_dict(profile: ClientProfile) -> dict:
    """Serialisable view for API responses and for the RecoveryState."""
    return {
        "name": profile.name,
        "email": profile.email,
        "tier": profile.tier,
        "contact": profile.contact,
        "terms": profile.terms,
        "risk_level": profile.risk_level,
        "is_hero": profile.is_hero,
        "max_autonomous_stage": profile.max_autonomous_stage,
        "discount_authority_pct": profile.discount_authority_pct,
        "allow_payment_plan": profile.allow_payment_plan,
        "requires_split_billing": profile.requires_split_billing,
        "escalation_patience_days": profile.escalation_patience_days,
        "relationship_value": profile.relationship_value,
        "guardrails": list(profile.guardrails),
    }
