from typing import TypedDict, Optional, List
from datetime import datetime

class RecoveryState(TypedDict):
    # Invoice context
    invoice_id: int
    client_name: str
    client_email: str
    amount: float
    due_date: str
    current_status: str
    days_overdue: int
    escalation_stage: str            # STAGE_1, STAGE_2, STAGE_3, STAGE_4
    last_email_date: Optional[str]
    virtual_date: Optional[str]
    promised_date: Optional[str]     # ISO; set when a PTP is accepted, read by the PTP gate
    contact_attempts: int            # outbound contacts so far; capped by stopping rule 5
    client_replies: int              # times the client engaged; 0 through the ladder = ghosted

    # Structured policy from src/domain/clients.py — tier, limits, guardrails.
    # Phase 2's decide_action and validate_action read this.
    client_profile: Optional[dict]

    # Set by check_stop_conditions when a stopping rule halts the workflow.
    stop_reason: Optional[str]
    # Populated when a case must reach a person; consumed by notify_human.
    notify_payload: Optional[dict]

    # --- Agentic core (Phase 2) ---
    # Prior actions and their outcomes, oldest first. Feeds decide_action.
    interaction_history: List[dict]
    # The AgentAction the model chose, as a dict.
    proposed_action: Optional[dict]
    # False when the policy guard vetoed the choice.
    action_validated: Optional[bool]
    veto_reason: Optional[str]
    # What the guard substituted in place of a vetoed action.
    substituted_action: Optional[dict]
    # The action actually executed after validation.
    effective_action: Optional[dict]
    # Every node appends its own name; drives the live graph animation and trace.
    visited_nodes: List[str]
    # 1.0 = intact. Over-escalation reduces it, which costs recovery in Phase 4.
    relationship_score: float
    # Audited record of every side effect, produced by the tool layer.
    tool_calls: List[dict]

    # --- Reproducibility and A/B (Phase 4) ---
    # Seed for the simulated environment. Same seed + same portfolio = same run.
    sim_seed: int
    # "agent" uses decide_action; "ladder" is the fixed-schedule baseline.
    policy: str

    # Client reply (if any)
    client_reply: Optional[str]

    # Agent working memory
    classified_intent: Optional[str]  # PROMISE_TO_PAY, DISPUTE, OPT_OUT, etc.
    intent_confidence: Optional[float]
    extracted_entities: Optional[dict] # promised_date, disputed_amount, reason

    # RAG-retrieved context
    retrieved_context: Optional[str]  # Contract terms, past interactions, notes

    # Draft & Compliance loop
    drafted_email: Optional[str]
    compliance_verdict: Optional[str] # PASS or FAIL
    compliance_reason: Optional[str]
    compliance_retries: int           # Max 2 rewrites

    # Razorpay tool results
    payment_link_id: Optional[str]    # Razorpay plink_* identifier
    payment_link_url: Optional[str]   # Razorpay short_url; rendered directly by the UI
    virtual_account_details: Optional[dict]  # From Smart Collect

    # Execution
    action_taken: Optional[str]
    new_status: Optional[str]
    rule_applied: Optional[str]       # Which compliance rule governed the decision

    # Audit accumulator
    audit_entries: List[dict]

    # Flow control
    should_send_email: bool
