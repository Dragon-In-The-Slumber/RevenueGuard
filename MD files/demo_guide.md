# 🎬 Demo Preparation Guide & RAG Strategy

---

## 1 & 2: New Simulation Buttons

Your current `SimulationController.tsx` only has three buttons: "Generate 100", "Advance 1 Day", and "Auto-Run 30 Days". For a 5-minute demo, you need much smaller, trackable batches.

### What to Add

| Button | Action | Purpose |
|---|---|---|
| **Generate 5 Invoices** | `POST /api/invoices/simulate_batch` with `{"count": 5}` | Small enough to track each invoice by name |
| **Advance 5 Days** | Calls tick endpoint 5 times sequentially | Shows ISSUED → OVERDUE → NOTIFIED_1 for most invoices |
| **Advance 15 Days** | Calls tick endpoint 15 times sequentially | Shows the full journey: STAGE_1 through STAGE_3, PTP pauses, recoveries |

### IDE Prompt to Implement

> In `dashboard/src/components/command-center/SimulationController.tsx`, add three new buttons alongside the existing ones:
> 1. **"Generate 5"** — calls `POST /api/invoices/simulate_batch` with `{"count": 5}`. Style it as a smaller secondary `pill-btn`.
> 2. **"Advance 5 Days"** — runs the tick endpoint 5 times sequentially (await each before starting the next), showing a progress counter `(X/5)`. Use the same pattern as the existing auto-run but with 5 instead of 30.
> 3. **"Advance 15 Days"** — same as above but 15 times, showing `(X/15)`.
> Keep the existing "Generate 100", "Advance 1 Day", and "Auto-Run 30 Days" buttons. Arrange the buttons in two rows: the first row for small batches (Generate 5, Advance 5 Days, Advance 15 Days), the second row for full-scale (Generate 100, Advance 1 Day, Auto-Run 30 Days). The small batch row should have a subtle label like "Demo Mode" above it.

---

## 3: Your 4 RAG Hero Clients (Pre-seeded in ChromaDB)

These profiles are loaded into ChromaDB every time your backend starts. They are your **demo superpowers** — the AI reads these profiles before drafting every email, making each client's communication unique and context-aware.

### The 4 Hero Clients

#### 🟢 Acme Corp — "The Reliable Giant"
| Field | Value |
|---|---|
| **Type** | Fortune 500 Manufacturing |
| **Contract** | MSA, **Net-60** payment terms |
| **Contact** | Rajesh Kumar, Finance Manager |
| **History** | 12 invoices, 10 on time, 2 paid 5-8 days late |
| **Risk** | LOW |
| **RAG Guardrail** | *"Never threaten legal action — Tier 1 client worth ₹2Cr annually"* |
| **Demo Angle** | Show how the AI uses a **warm, gentle tone** even when overdue. The email will reference internal approval cycles, not cash flow. Perfect for showing RAG context influencing email tone. |

#### 🟡 Globex Solutions — "The Risky Startup"
| Field | Value |
|---|---|
| **Type** | Series B SaaS Startup, 150 employees |
| **Contract** | Net-30, **1.5% monthly late fee** clause |
| **Contact** | Priya Mehta, Head of Finance |
| **History** | 6 invoices: 2 on time, 3 late (15-25 days), **1 still outstanding (45 days!)** |
| **Risk** | HIGH |
| **RAG Guardrail** | *"Has broken TWO Promise-to-Pay commitments. Escalate to human after Stage 2."* |
| **Demo Angle** | The AI will reference the **broken promises** in its Stage 2 email. Show the compliance judge catching this context. Simulate a PTP reply → watch the AI call it out when the promise breaks again. |

#### 🔴 Pinnacle Industries — "The Serial Disputer"
| Field | Value |
|---|---|
| **Type** | Listed Conglomerate, 5000+ employees |
| **Contract** | Annual Retainer, **Net-45**, auto-renewal |
| **Contact** | VP Singh (responds only to Stage 2+ emails) |
| **History** | 8 invoices: 5 on time, **3 disputed** (pattern: always disputes consulting hours) |
| **Risk** | MEDIUM-HIGH |
| **RAG Guardrail** | *"Do NOT combine Milestone 1 and 2 in a single payment link. Issue separate links."* |
| **Demo Angle** | Simulate a dispute reply → show how the AI immediately halts and escalates. Point out the RAG context telling the AI to issue *separate* payment links. This is your **"AI reads the contract"** wow moment. |

#### ⚫ NovaTech Labs — "The Ghost"
| Field | Value |
|---|---|
| **Type** | Seed-stage AI startup, **12 employees** |
| **Contract** | Project-based SOW, **Net-15**, no late fee |
| **Contact** | Arjun Patel, CEO (only contact, no finance team) |
| **History** | 3 invoices: 1 on time, **2 ghosted (30+ days no response)** |
| **Risk** | **EXTREME** |
| **RAG Guardrail** | *"Company may be running out of runway. After Stage 2, escalate to human immediately. Consider 10% early payment discount."* |
| **Demo Angle** | Show how the AI **stops wasting resources** after Stage 2 and immediately escalates to a human. This demonstrates the system's intelligence — it knows when to quit. |

### How to Use Them in Your Demo

> [!IMPORTANT]
> The RAG profiles only activate when the `client_name` of a generated invoice **exactly matches** one of these 4 names. But `generate_fake_invoices()` uses `faker` to generate **random Indian company names** — so these hero clients will almost never appear in a random batch!

**The fix:** You need to modify the invoice generation to **always include these 4 hero clients** in every batch. Add this to the IDE prompt (in the bug fix):

> In `src/persistence/crud.py`, modify `generate_fake_invoices` so that the first 4 invoices of every batch are always the hero clients: Acme Corp, Globex Solutions, Pinnacle Industries, and NovaTech Labs. Use their exact names and appropriate amounts/overdue days. Only generate random faker invoices for the remaining `count - 4` slots (if count > 4).

This guarantees that when you click "Generate 5", you get exactly the 4 hero clients + 1 random one.

---

## 4: How to Effectively Use the Webhook & Event Simulator

### Current Problem
Your webhook endpoint (`POST /api/webhooks/razorpay`) is a **stub** — it just prints the event and broadcasts `state_updated`, but never actually changes any invoice status. This was flagged in the [bug diagnosis](file:///C:/Users/abhin/.gemini/antigravity/brain/44ca47e4-6098-4598-b6ea-caf110cc4993/bug_diagnosis.md) as Bug 4.

Once the bug fix is implemented, here is exactly how each event type should work:

### Event Type → What It Should Do

| Event | What It Does | Invoice Status Change | Demo Use Case |
|---|---|---|---|
| `invoice.paid` | Full payment received | → `RECOVERED` ✅ | Select an overdue invoice → fire this → watch it turn green instantly |
| `invoice.partially_paid` | Partial amount received | No status change, logs audit entry | Show that the system acknowledges partial payments but keeps chasing |
| `payment_link.paid` | Client clicked the Razorpay link and paid | → `RECOVERED` ✅ | Show the payment link journey end-to-end |
| `payment.dispute.created` | Client formally disputes | → `DISPUTE` ⚔️ | Select a NOTIFIED invoice → fire this → watch it halt and escalate to human |
| `payment.failed` | Payment attempt bounced | No status change, logs failure | Show resilience — system doesn't crash on failed payments |
| `virtual_account.credited` | Bank transfer (NEFT/RTGS) received | → `RECOVERED` ✅ | Show Smart Collect / virtual account flow |

### Demo Script for Webhook Simulator

1. **Go to Events page**
2. **Select Invoice #1 (Acme Corp)** from the dropdown — it should be at NOTIFIED_1 or NOTIFIED_2 stage
3. **Select `invoice.paid`** → Click **Fire Event**
4. **Switch to Invoices page** → Show that Acme Corp is now ✅ RECOVERED
5. **Go back to Events** → **Select Invoice #3 (Pinnacle Industries)**
6. **Select `payment.dispute.created`** → Click **Fire Event**
7. **Switch to Invoices** → Show that Pinnacle is now ⚔️ DISPUTED and escalated to human
8. **Open Pinnacle's audit trail** → Show the complete chain: overdue → emails → dispute → human escalation

---

## 🎬 Complete 5-Minute Demo Script

### Minute 0:00 – 0:30 | "The Problem"
- Show the empty Command Center dashboard
- *"B2B companies lose ₹X crore annually to overdue invoices. Manual chasing is slow, inconsistent, and lacks compliance guardrails."*

### Minute 0:30 – 1:00 | "Generate & Observe"
- Click **"Generate 5 Invoices"**
- Show the Invoice Table — 5 invoices, all ISSUED
- Point out: *"4 of these are real client profiles loaded from our RAG knowledge base"*

### Minute 1:00 – 2:00 | "Watch the AI Work"
- Click **"Advance 5 Days"**
- Watch invoices transition: ISSUED → OVERDUE → NOTIFIED_1
- Open **Acme Corp's audit trail** → Show:
  - AI reasoning: *"Client is Tier 1, use warm tone"*
  - Email preview with Razorpay payment link
  - Compliance Judge: PASS ✅
- *"The AI read Acme's contract (Net-60), their payment history (10/12 on time), and crafted a gentle reminder"*

### Minute 2:00 – 3:00 | "Client Interactions"
- Open **Globex Solutions** invoice detail
- Click the **Reply Simulator** → Send *"We will pay by next Friday"*
- Show intent classification: **PROMISE_TO_PAY (94% confidence)**
- Status changes to 🤝 PAUSED_PTP
- *"The AI paused all escalation — but it remembers. Globex has broken promises before."*
- Click **"Advance 5 Days"** → If Globex doesn't pay, watch the AI resume escalation with a **firmer tone referencing the broken promise**

### Minute 3:00 – 4:00 | "Compliance & Disputes"
- Go to **Events page** → Fire `payment.dispute.created` on **Pinnacle Industries**
- Show status flip to ⚔️ DISPUTE → human escalation logged
- Go to **Compliance Dashboard** → Show pass/fail stats
- Open a rejected draft → Show the **side-by-side diff** (original vs. rewritten email)
- *"Every email is reviewed by our AI Compliance Judge against 8 mandatory rules"*

### Minute 4:00 – 4:30 | "The Graph"
- Go to **AI Graph page**
- Show the LangGraph execution visualizer
- Highlight the compliance loop: `draft_email → evaluate_compliance → FAIL → rewrite → PASS`
- *"This isn't a black box. Every decision node is visible and auditable."*

### Minute 4:30 – 5:00 | "Results"
- Go back to **Command Center**
- Show KPIs: Recovery Rate, Total Recovered
- Show the funnel: distribution across all states
- Fire `invoice.paid` on **NovaTech** via webhook → Watch recovery amount jump
- *"RevenueGuard recovered ₹X in 15 simulated days, with zero human intervention and 100% compliance."*

---

## Combined IDE Prompt (New Buttons + Hero Clients)

> In `dashboard/src/components/command-center/SimulationController.tsx`, add three new buttons alongside the existing ones: "Generate 5" (calls simulate_batch with count 5), "Advance 5 Days" (runs tick 5 times sequentially with progress counter), and "Advance 15 Days" (runs tick 15 times sequentially with progress counter). Arrange in two rows — first row labeled "Demo Mode" with the small buttons, second row with the existing full-scale buttons.
> 
> Also, in `src/persistence/crud.py`, modify `generate_fake_invoices` so that the first 4 invoices always use the hero client names exactly matching the RAG seed data: "Acme Corp", "Globex Solutions", "Pinnacle Industries", and "NovaTech Labs" — with appropriate amounts and emails. Only generate random faker invoices for the remaining `count - 4` slots. If count <= 4, just generate that many hero clients in order.
