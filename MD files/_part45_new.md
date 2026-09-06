# PART 4 — Revised implementation plan (agentic)

> **This supersedes the original Part 4.** The first version sequenced the 27 defects into five
> phases of cleanup. It would have produced a correct, fast, well-tested version of the *same
> architecture* — an LLM workflow. This version reorders the same fixes as prerequisites for an
> architectural change, and inserts the change itself. Part 5 is the build spec for that change.

## The gap being closed

The problem statement asks for an agent that *"detects revenue at risk, **determines the right
intervention**, and executes a bounded recovery workflow."*

Detection works. Bounded execution works. The middle clause does not: `nodes.py:87-96` selects the
intervention with `stage_map[current_status]`, a dictionary. The four RAG client profiles change the
wording of emails and influence no decision. Acme Corp — reliable, Tier-1, delays are approval
cycles — and NovaTech Labs — twelve people, out of runway, ghosted twice — are chased on an
identical schedule.

The change is to move intervention selection from Python into the agent, and to move the compliance
layer from reviewing *prose* to vetoing *choices*. That single change also strengthens three of the
four judging pillars, which is why it comes before polish rather than after.

## Phase order and rationale

| Phase | Goal | Why here |
|---|---|---|
| 0 | Unblock | Nothing is demoable until the crashes are fixed |
| 1 | Prerequisites for agency | The decision node needs a real policy source and a real action vocabulary |
| 2 | **The agentic core** | The architectural change; everything after exists to prove it works |
| 3 | Make its actions real and fast | Agent choices must map to real Razorpay calls, and a full run must fit in a demo slot |
| 4 | Proof | A responsive environment and a reproducible A/B make the recovery number defensible |
| 5 | Polish | Cut this first if time runs short |

---

## Phase 0 — Unblock (unchanged)

Items 1-7 exactly as before: `useApi` throws on non-2xx *(D-04)*; delete the dead query in
`dashboard_api.py:200-211` *(D-03)*; rebuild `client_reply` *(D-01)*; unify the webhook payload
*(D-02)*; monotonic audit timestamps and `ORDER BY timestamp, id` *(D-05, D-06)*; `echo=False`,
funnel bar colours, payment-link URL *(D-18, D-23, D-15b)*; `docker compose down -v` *(D-20)*.

**Acceptance:** 5 invoices, 5 ticks, audit timeline in order, reply simulator classifies and
persists, `/clients` loads, backend errors visible in the UI.

---

## Phase 1 — Prerequisites for agency

The same fixes as the old Phase 1, but now they exist to feed the decision node.

8. **`src/domain/clients.py` — the policy source.** *(D-09, D-10)* Beyond name/tier/terms/contact,
   each profile now carries the fields the agent and the guard will read:
   `max_autonomous_stage`, `discount_authority_pct`, `allow_payment_plan`, `requires_split_billing`,
   `escalation_patience_days`, `relationship_value`, `guardrails: list[str]`. Seed ChromaDB,
   invoices, and `/api/clients` from this one module.
9. **RAG returns a joined string**; profile metadata returned structurally, not sniffed. *(D-08)*
10. **Complete the stopping rules.** *(D-14)* This is now load-bearing: the stop conditions define
    the boundary of the action space. Full intent→status→rule table, `LEGAL_HOLD` on
    opt-out/legal threat, `contact_attempts` column with a cap → `UNRESPONSIVE`, and a
    `notify_human` node.
11. **Fix Promise-to-Pay properly.** *(D-16)* Honour the extracted date, anchor to the virtual
    clock, gate the graph while inside the promise window.
12. **Pass the real invoice to `draft_email`** — delete `DummyInvoice`. *(D-27)*
13. **Alembic.** *(D-20)*

**Acceptance:** each of the five stopping rules demonstrably fires with the correct audit row.

---

## Phase 2 — The agentic core

Build to the spec in Part 5. Four pieces:

14. **`decide_action` node.** Replaces `stage_map`. Given invoice state, RAG profile, interaction
    history and remaining budget, the model returns a structured `AgentAction` from an explicit
    menu, with reasoning and expected outcome.
15. **`validate_action` node — the policy guard.** The Compliance Officer stops reviewing prose and
    starts vetoing choices. Nine hard rules; every veto writes an `ACTION_VETOED` audit row naming
    the proposed action, the rule, and the substitute.
16. **Rewire the graph** so `execute_action` dispatches by action type rather than always drafting
    an email. The existing draft→judge→rewrite loop becomes one branch of the dispatch, not the
    trunk.
17. **Wire the MCP tools.** *(D-26)* Action selection becomes tool selection: `send_email`,
    `create_payment_link`, `notify_slack`, `update_invoice_status`, `set_promised_date` are bound as
    real tools. "Every side effect flows through an audited tool call" becomes true rather than
    aspirational.

**Acceptance:** run 20 invoices spanning all four personas for 15 ticks. Acme and NovaTech must
produce visibly different action sequences, and the audit trail must explain why in the agent's own
words.

---

## Phase 3 — Make the actions real and fast

18. **Razorpay SDK.** *(D-15)* Now worth more than before, because the agent has actions that need
    it: `OFFER_DISCOUNT` creates a link at a reduced amount, `SPLIT_INVOICE` creates two links,
    `OFFER_PAYMENT_PLAN` creates a sequence. Plus Smart Collect virtual accounts. Store `id` and
    `short_url` separately.
19. **Webhook signature verification, idempotency, demo-token auth, env-driven CORS.** *(D-19)*
20. **Tick performance.** *(D-18)* Batched audit writes, one commit per tick, `asyncio.gather` with
    a semaphore, decision cache keyed on the equivalence class, `DEMO_FAST` mode. Target: 100
    invoices × 30 days under 60 seconds. The A/B run in Phase 4 is impossible without this.
21. **Shared WebSocket + live node trace.** *(D-07, D-13)* `visited_nodes` on the state feeds both
    the animated graph and a real per-invoice execution trace.
22. **`useVirtualDate()`**, real cooldown data on `/api/invoices`. *(D-11, D-12)*

---

## Phase 4 — Proof

23. **Responsive simulation environment.** *(D-17)* Extract to `src/simulation/client_env.py`,
    clearly labelled. Critically, the response probability must depend on **the action the agent
    chose**, not only the stage — otherwise the agent's judgment cannot affect the outcome and the
    A/B is meaningless. Include a relationship-damage penalty so over-escalation has a cost.
24. **Seeded reproducibility.** `random.Random(seed)` throughout. A judge asking "run it again"
    should get the same number.
25. **A/B: agent vs. fixed ladder.** `POST /api/simulation/run?policy=agent|ladder&seed=42`. Same
    seed, same portfolio, two policies. Report recovery rate, ₹ recovered, days-to-recovery, human
    escalations, compliance vetoes, relationship-damage incidents.
26. **Human approval queue** at `/approvals` — the HITL pillar currently has no UI at all.
27. **Decision explorer.** For any invoice, show each decision point: what the agent considered,
    what it chose, why, what the guard said, what happened. This is the screen that proves the
    system thinks.
28. **Working test suite.** *(D-24)* `pytest-asyncio`, `aiosqlite`, `FakeLLM` fixture. Tests per
    stopping rule, per guard rule, cooldown, rewrite-loop termination, and a deterministic
    golden-path e2e.

---

## Phase 5 — Polish

Old Phase 4 items 26-30: prune dependencies, fix `.env.example`, dashboard service in
docker-compose, `output: 'standalone'`, sanitise `EmailPreview`, replace `alert()` with toasts,
move inline imports, structured logging. **Cut this entirely if time is short.**

---

## If you run out of time

Priority order under pressure: **Phase 0 → Phase 2 → Phase 4 items 23-25 → everything else.**

A system that visibly reasons about each client and can prove it beats a fixed schedule, with a
handful of rough edges, scores far better than a polished workflow that walks every invoice through
the same four steps.

---

# PART 5 — Agentic architecture spec

Build spec for Phase 2. Written to be implementable directly.

## 5.1 State additions

Add to `RecoveryState` (`src/graph/state.py`):

```python
client_profile: Optional[dict]        # structured policy from src/domain/clients.py
interaction_history: List[dict]       # prior actions + outcomes, newest last
proposed_action: Optional[dict]       # AgentAction as dict
action_validated: Optional[bool]
veto_reason: Optional[str]
substituted_action: Optional[dict]
visited_nodes: List[str]              # each node appends its own name
contact_attempts: int
relationship_score: float             # 1.0 = intact; decreases on over-escalation
```

## 5.2 The action menu

```python
class AgentAction(BaseModel):
    action: Literal[
        "SEND_EMAIL",            # the current behaviour, now one option among many
        "WAIT",                  # deliberate patience — the option that never existed
        "SWITCH_CHANNEL",        # email → SMS / WhatsApp
        "OFFER_DISCOUNT",        # early-payment incentive
        "OFFER_PAYMENT_PLAN",    # split into instalments
        "SPLIT_INVOICE",         # separate disputed from undisputed portions
        "ESCALATE_TO_HUMAN",
        "CLOSE_AS_UNRECOVERABLE",
    ]
    stage: Optional[Literal["STAGE_1","STAGE_2","STAGE_3","STAGE_4"]] = None
    wait_days: Optional[int] = None
    discount_pct: Optional[float] = None
    instalments: Optional[int] = None
    channel: Optional[Literal["EMAIL","SMS","WHATSAPP"]] = None
    reasoning: str               # goes straight into the audit trail
    confidence: float
    expected_outcome: str        # what the agent predicts — later compared against reality
```

Three of these come directly from profiles you already wrote and currently do nothing with:

- **`SPLIT_INVOICE`** — Pinnacle's profile says *"Do NOT combine Milestone 1 and 2 in a single
  payment link. Issue separate links for undisputed and disputed portions."* An agent that reads
  that and issues two Razorpay links is a strong thirty seconds of demo.
- **`OFFER_DISCOUNT`** — NovaTech's says *"Consider offering a 10% early payment discount to
  accelerate recovery of whatever is possible."*
- **`WAIT`** — Acme's says delays are internal approval cycles, not cash flow. The correct action is
  often to do nothing, which the current system cannot express.

## 5.3 `decide_action`

Prompt inputs: invoice facts, days overdue, current status and stage, full RAG profile including
guardrails, interaction history with outcomes, contact attempts remaining, cooldown state, and the
list of actions currently permitted. Structured output, `temperature=0.2`.

The prompt must state the objective explicitly — *maximise recovered value while preserving the
client relationship and staying inside policy* — because a purely recovery-maximising agent learns
to escalate hardest every time, and the relationship penalty in 5.6 is what makes restraint
rational.

Every decision writes an `AGENT_DECISION` audit row carrying the action, the reasoning, the
confidence, and the alternatives considered.

## 5.4 `validate_action` — the policy guard

This is where "bounded autonomy" stops being a claim. The current bound is trivial because there is
only one possible action. A real menu with a real veto is a much stronger story.

| # | Rule | On violation |
|---|---|---|
| 1 | No `SEND_EMAIL` within 4 virtual days of the last one | substitute `WAIT` |
| 2 | Cannot skip more than one escalation stage | clamp to next stage |
| 3 | `discount_pct` above the profile's `discount_authority_pct` | `ESCALATE_TO_HUMAN` |
| 4 | Invoice above the value threshold and action ≠ `SEND_EMAIL` | `ESCALATE_TO_HUMAN` |
| 5 | Any contact when `LEGAL_HOLD` or opted out | hard block, no action |
| 6 | `STAGE_4` | always `ESCALATE_TO_HUMAN` |
| 7 | `WAIT` longer than 14 days | clamp to 14 |
| 8 | More than 3 instalments | clamp to 3 |
| 9 | Stage above the profile's `max_autonomous_stage` | `ESCALATE_TO_HUMAN` |

Every veto writes an `ACTION_VETOED` row naming the proposed action, the rule, and the substitute.
These rows are the demo: *"the agent proposed a 25% discount on Globex; policy caps autonomous
discounts at 10%, so it was blocked and routed to a human"* is a far better compliance story than a
gauge reading 100%.

## 5.5 Rewired graph

```
check_overdue
  → check_stop_conditions          (payment, PTP window, legal hold, max attempts)
  → check_cooldown
  → retrieve_client_context
  → classify_reply
  → decide_action                  ← NEW: the agent chooses
  → validate_action                ← NEW: the guard can veto and substitute
  → execute_action                 (dispatch by action type)
        ├ SEND_EMAIL       → draft_email → evaluate_compliance → [rewrite loop] → send_via_tool
        ├ OFFER_DISCOUNT   → razorpay.create_payment_link(discounted) → draft_email → …
        ├ SPLIT_INVOICE    → razorpay ×2 → draft_email → …
        ├ OFFER_PAYMENT_PLAN → razorpay plan → draft_email → …
        ├ SWITCH_CHANNEL   → draft_sms → send_via_tool
        ├ WAIT             → schedule next review → END
        ├ ESCALATE_TO_HUMAN → notify_human → END
        └ CLOSE_AS_UNRECOVERABLE → notify_human → END
  → END
```

The existing draft→judge→rewrite loop survives intact as one branch. Nothing good is thrown away;
it stops being the only path.

## 5.6 Environment that responds to choices

`src/simulation/client_env.py`, explicitly labelled in the UI as the simulated environment.

```
p(pay) = persona.base_rate
       × stage_multiplier[stage]
       × action_multiplier[action]
       × relationship_score
```

Illustrative `action_multiplier` — tune during Phase 4:

| Action | Effect |
|---|---|
| `OFFER_DISCOUNT` | ×2.0 for cash-constrained personas (Globex, NovaTech), ×1.1 for Acme |
| `OFFER_PAYMENT_PLAN` | ×2.5 for NovaTech-type; converts some ghosts into partial payers |
| `SPLIT_INVOICE` | unlocks Pinnacle's undisputed portion → guaranteed partial recovery |
| `WAIT` on a reliable persona | high chance of unprompted payment |
| `SEND_EMAIL` at a stage above `max_autonomous_stage` | `relationship_score −= 0.15` |

The relationship penalty is what makes the agent's judgment matter. Without it the optimal policy is
"escalate maximally, always," and a fixed ladder ties the agent. With it, knowing when *not* to act
is worth measurable money — which is exactly the thing you want the A/B to demonstrate.

Seed everything: `random.Random(seed)`, seed surfaced in the UI.

## 5.7 What this buys you against the rubric

| Pillar | Before | After |
|---|---|---|
| Measured money recovered | `random.random()`, independent of the agent | Outcome depends on choices; reproducible; A/B against a baseline |
| Compliant escalation | Cooldown + prose review — real but narrow | Nine-rule guard vetoing *choices*; every veto audited |
| Stopping rules | 2 of 5 | 5 of 5, plus `WAIT` and `CLOSE_AS_UNRECOVERABLE` as first-class decisions |
| Audit trail | What happened | What was considered, what was chosen, why, what the guard said, what followed |

## 5.8 The demo this makes possible

Ninety seconds, three beats:

1. **Two invoices side by side.** Acme, ₹12.5L, 22 days overdue. NovaTech, ₹80k, 35 days overdue.
   Same tick. The agent sends Acme a warm Stage-1 note and then *waits eleven days* — reasoning
   shown on screen: *"Tier-1 client, 10 of 12 invoices paid on time, delays historically caused by
   internal approval cycles. Escalating now risks a ₹2Cr relationship for a delay that resolves
   itself."* For NovaTech it skips straight to a 10% early-payment discount with a real Razorpay
   link, reasoning: *"Seed-stage, two prior invoices ghosted, likely runway-constrained. Partial
   recovery now beats full recovery never."*

2. **The guard fires.** The agent proposes a 25% discount on Globex. Blocked — policy caps
   autonomous discounts at 10%. Routed to the approval queue with the agent's case attached.

3. **The number.** Same seed, same 100 invoices, two policies. *"Fixed ladder: 31.2%. Our agent:
   47.3%. Zero compliance violations, 47 self-blocked escalations, 12 drafts rewritten, 18 invoices
   routed to humans."*

Beat 1 is the one that wins. No other team's demo will show an agent deciding to do nothing and
being right.
