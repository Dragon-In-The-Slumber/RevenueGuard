# RevenueGuard Dashboard — Complete Frontend Strategy & Features

## The Strategy: How to Decide Features When the Backend is Ready

Your instinct is correct — you shouldn't guess at features. Here's the framework:

### Step 1: Endpoint Audit → Every API endpoint gets a UI surface

If the backend exposes it, the frontend must consume it. Otherwise you built capability no one can see.

| Backend Endpoint | Was it in the original proposal? | Gap? |
|---|---|---|
| `POST /api/invoices/simulate_batch` | ✅ Yes (Simulation Controller) | |
| `POST /api/simulation/tick` | ✅ Yes (Advance Day) | |
| `POST /api/invoices/{id}/reply` | ✅ Yes (Interactive Demo Triggers) | |
| `POST /api/webhooks/razorpay` | ❌ **No UI surface** | **GAP 1** |
| `GET /api/metrics` | ✅ Yes (KPI Cards) | |
| `GET /api/funnel` | ✅ Yes (Recovery Funnel) | |
| `GET /api/invoices/{id}/audit-logs` | ✅ Yes (Audit Trail) | |
| `GET /api/audit-logs` | ✅ Yes (Activity Feed) | |
| `WebSocket /ws (state_updated)` | Partially (no virtual date display) | **GAP 2** |

### Step 2: Data Completeness → Every database field is visible somewhere

If a column exists in your DB, it should appear in the UI. Otherwise judges don't know it exists.

| DB Field | Was it exposed? | Gap? |
|---|---|---|
| `Invoice.escalation_stage` (STAGE_1→4) | ❌ **Not shown anywhere** | **GAP 3** |
| `Invoice.razorpay_payment_link_id` | ❌ **Not shown** | **GAP 4** |
| `Invoice.razorpay_virtual_account_id` | ❌ **Not shown** | **GAP 4** |
| `AuditLog.rule_applied` | ✅ Yes (AI Reasoning accordion) | |
| `AuditLog.content_snapshot` | ✅ Yes (Email display) | |
| `AuditLog.compliance_verdict` | ✅ Yes (Judge UI) | |

### Step 3: Workflow Visibility → Every LangGraph node is observable

This is what separates you from everyone else. Your competitors will show "invoice → email sent → paid". You show the *internal reasoning pipeline*.

| LangGraph Node | Was it visible? | Gap? |
|---|---|---|
| `check_overdue` | ❌ No way to see which invoices just became overdue | **GAP 5** |
| `check_cooldown` / `log_blocked` | ✅ Proposed (Cooldown Timers) | |
| `retrieve_client_context` | ✅ Proposed (RAG Panel) | |
| `classify_reply` | ✅ Proposed (Intent Display) | |
| `draft_email` → `evaluate_compliance` loop | ✅ Proposed (Draft vs Final diff) | |
| `call_razorpay_tools` | ❌ **No MCP tool call visibility** | **GAP 6** |
| `execute_action` | ✅ Implicitly in timeline | |
| `simulate_client` | ❌ **No visibility into simulated behavior** | **GAP 7** |

### Step 4: RAG Knowledge Base → Browsable, not hidden

Your 4 handcrafted client profiles (Acme, Globex, Pinnacle, NovaTech) are a key differentiator. But in the original proposal, they were only visible as a sidebar in the invoice detail. There's no way for a judge to browse the knowledge base independently.

**GAP 8:** No dedicated Client Intelligence / Knowledge Base page.

---

## The Complete Feature List (Gaps Filled)

### Page 1: Command Center (Home)

The first thing judges see. Proves "measured money recovered across a batch."

- **Simulation Controller Panel**
  - "Generate Batch" button → `POST /api/invoices/simulate_batch`
  - "Advance 1 Day" button → `POST /api/simulation/tick`
  - "Auto-Run 30 Days" button → calls tick 30 times with 1-second intervals
  - **Virtual Date Display** → shows the current simulated date from WebSocket `virtual_date` **(fixes Gap 2)**
  
- **KPI Cards** (from `GET /api/metrics`)
  - Total At-Risk Revenue (₹)
  - Total Recovered (₹) — animated counter climbing in real-time
  - Recovery Rate (%) — circular progress gauge
  - Total Invoices / Recovered Invoices

- **Recovery Funnel Chart** (from `GET /api/funnel`)
  - Visual bar/sankey showing invoice counts at each status stage
  - Color-coded: Green (RECOVERED), Amber (PAUSED_PTP), Red (DISPUTE/LEGAL_HOLD), Blue (NOTIFIED_1/2/3)

- **Live Agent Activity Ticker** (from `GET /api/audit-logs` + WebSocket refresh)
  - Scrolling feed of the 20 most recent agent actions across all invoices
  - Each entry shows: timestamp, client name, event type, action taken
  - Color-coded event type badges

---

### Page 2: Invoice Management Table

> [!IMPORTANT]
> This was completely missing from the original proposal. You need a way to browse, filter, and click into individual invoices.

- **Full Invoice Table** (needs new endpoint: `GET /api/invoices`)
  - Columns: ID, Client Name, Amount (₹), Due Date, Days Overdue, Status, Escalation Stage, Actions
  - **Status Badges** — color-coded pills for every `InvoiceStatus` enum value
  - **Escalation Stage Indicator** — visual progress bar showing STAGE_1 → STAGE_4 **(fixes Gap 3)**
  - **Razorpay Links Column** — clickable payment link URL and virtual account ID when present **(fixes Gap 4)**
  
- **Filters & Sorting**
  - Filter by status (dropdown with all 11 `InvoiceStatus` values)
  - Filter by escalation stage (STAGE_1 through STAGE_4)
  - Sort by amount, days overdue, or status
  - Search by client name

- **Bulk Actions**
  - "Process Selected" — manually trigger the LangGraph on selected invoices
  - "Export CSV" — download the current view

- **Quick Actions per Row**
  - "View Audit Trail" → navigates to invoice detail
  - "Simulate Reply" → opens the reply modal **(interactive demo)**
  - "Simulate Payment" → calls webhook endpoint with `invoice.paid` **(fixes Gap 1)**

---

### Page 3: Invoice Detail & Audit Trail

Click any invoice from the table to enter this view. This is the centrepiece of the demo.

- **Invoice Header Card**
  - Client name, email, amount, due date, days overdue
  - Current status (large badge)
  - Escalation stage progress bar (STAGE_1 → 2 → 3 → 4)
  - Promise-to-pay date (if set)
  - Razorpay Payment Link (clickable) **(fixes Gap 4)**
  - Virtual Account details (if assigned)

- **Chronological Audit Timeline** (from `GET /api/invoices/{id}/audit-logs`)
  - Every event as a card in a vertical timeline
  - Event type icon + color (📧 EMAIL_SENT green, 🤖 INTENT_CLASSIFIED blue, ⚖️ COMPLIANCE_PASSED/FAILED, 🛑 ESCALATION_BLOCKED red, etc.)
  - **Expandable "AI Reasoning" Accordion** — shows:
    - `agent_reasoning`: The LLM's analysis text
    - `rule_applied`: Which compliance rule governed the decision
    - `compliance_verdict`: PASS ✅ or FAIL ❌
  - **Email Content Panel** — when `content_snapshot` exists, show the full email text in a styled card
  - **Draft vs. Final Diff View** — when the Compliance Judge rejected a draft and it was rewritten, show a side-by-side or inline diff highlighting what changed **(key differentiator)**

- **RAG Context Sidebar**
  - Shows exactly what the agent retrieved from ChromaDB for this client
  - Contract terms, payment history, behavioral notes, strategic guardrails
  - Highlighted warning badges (e.g., "⚠️ HIGH RISK", "🚫 NEVER threaten legal action")

- **Interactive Demo Panel** (right sidebar or bottom panel)
  - **"Simulate Client Reply"** text input + send button → `POST /api/invoices/{id}/reply`
    - Pre-built quick-reply buttons:
      - 💬 "We will pay by Friday"
      - ⚠️ "The amount is incorrect, we're disputing this"
      - 🚫 "Stop contacting us"
      - 🤝 "Can we get a 2-week extension?"
  - **"Simulate Razorpay Webhook"** buttons → `POST /api/webhooks/razorpay` **(fixes Gap 1)**
    - 💰 "Payment Received" (sends `invoice.paid`)
    - ⚔️ "Dispute Filed" (sends `payment.dispute.created`)
    - ❌ "Payment Failed" (sends `payment.failed`)

---

### Page 4: LangGraph Execution Visualizer **(NEW — Key Differentiator)**

> [!TIP]
> This is what NO other team will have. A visual representation of the AI's decision-making graph.

- **Interactive Graph Diagram**
  - Render the LangGraph topology as a visual flowchart (using a library like React Flow or D3)
  - Nodes: `check_overdue` → `check_cooldown` → `retrieve_client_context` → `classify_reply` / `draft_email` → `evaluate_compliance` → `call_razorpay_tools` → `execute_action` → `simulate_client`
  - Show conditional edges with labels ("DISPUTE → halt", "PASS → tools", "FAIL → rewrite")

- **Live Execution Trace**
  - When a tick runs or a reply is processed, animate the path the agent took through the graph
  - Highlight active nodes in green, skipped nodes in gray, failed/blocked nodes in red
  - Show the state values at each node (e.g., at `classify_reply`: `intent=PROMISE_TO_PAY, confidence=0.94`)

- **Node Detail Panels**
  - Click any node to see:
    - What state fields it reads/writes
    - The last N executions of this node across all invoices
    - Average execution time **(fixes Gap 5, 6, 7)**

---

### Page 5: Client Intelligence Hub **(NEW — fixes Gap 8)**

> [!TIP]
> This showcases your RAG system as a first-class feature, not a hidden implementation detail.

- **Client Profile Cards**
  - 4 hero clients displayed as rich cards: Acme Corp, Globex Solutions, Pinnacle Industries, NovaTech Labs
  - Each card shows:
    - Company tier (Enterprise / SME / Startup) with icon
    - Contract terms (Net-60, Net-30, etc.)
    - Key contact name & email
    - Risk level badge (LOW / HIGH / EXTREME HIGH)
    - Payment history summary (pie chart: on-time vs. late vs. ghosted)
    - Strategic guardrails (the "never do X" rules)

- **RAG Search Demo**
  - A search bar where judges can type a query like "What do we know about Globex's payment history?"
  - Shows the raw ChromaDB vector search results — proving the RAG system works
  - This is an interactive "wow" moment during the pitch

- **All Invoices for This Client**
  - Click a client card → see all their invoices, current statuses, and audit trails
  - Shows the client's lifetime recovery stats

---

### Page 6: Compliance Dashboard **(NEW — Proves Pillar 2)**

- **Compliance Score** — "100% compliance rate: 0 violations out of N emails"
- **Rejected Drafts Gallery** — a feed of every email that was rejected by the Compliance Judge, showing:
  - The original draft (with violations highlighted in red)
  - The Judge's feedback
  - The rewritten, approved version
  - The specific rule that was violated (Rule 1-8)
- **Cooldown Status Board** — for every active invoice, show:
  - Last contact date
  - Cooldown expiry countdown
  - Whether the next action is blocked or permitted
- **Rule Violation Heatmap** — which rules are most frequently violated (shows the AI is learning/improving)

---

### Page 7: Webhook & Event Simulator **(NEW — fixes Gap 1)**

> [!IMPORTANT]
> During the live demo, you need a dedicated panel to fire simulated Razorpay events and watch the system react in real-time.

- **Event Fire Panel**
  - Dropdown: Select invoice
  - Dropdown: Select event type (`invoice.paid`, `invoice.partially_paid`, `payment_link.paid`, `payment.dispute.created`, `virtual_account.credited`, `payment.failed`)
  - "Fire Event" button → `POST /api/webhooks/razorpay`
  - Live response display

- **Event Log**
  - Chronological log of all webhook events fired and their system impact
  - Shows: "Fired `invoice.paid` for INV-42 → Status changed NOTIFIED_2 → RECOVERED → All pending emails cancelled"

---

## Navigation Structure

```
┌─────────────────────────────────────────────┐
│  RevenueGuard                    [Virtual Date: Nov 15, 2024]  │
├─────────────┬───────────────────────────────┤
│ 📊 Command  │                               │
│    Center   │    (Active Page Content)       │
│ 📋 Invoices │                               │
│ 🧠 AI Graph │                               │
│ 👥 Clients  │                               │
│ ⚖️ Compliance│                              │
│ 🔔 Events   │                               │
│             │                               │
│ ─────────── │                               │
│ ⚙️ Settings │                               │
└─────────────┴───────────────────────────────┘
```

7 pages total. Sidebar navigation. The virtual date is always visible in the header.

---

## Priority Order for Implementation

| Priority | Page | Why | Effort |
|---|---|---|---|
| 🔴 P0 | **Command Center** | First thing judges see. Proves Pillar 1. | Medium |
| 🔴 P0 | **Invoice Table** | Core CRUD — judges need to browse data | Medium |
| 🔴 P0 | **Invoice Detail + Audit Trail** | Centrepiece of the demo. Proves Pillar 4. | High |
| 🟡 P1 | **LangGraph Visualizer** | Biggest differentiator. No other team will have this. | High |
| 🟡 P1 | **Client Intelligence Hub** | Showcases RAG as a visible feature | Medium |
| 🟢 P2 | **Compliance Dashboard** | Proves Pillar 2 with hard numbers | Low |
| 🟢 P2 | **Webhook Simulator** | Essential for live demo, but can be a modal instead of a full page | Low |

---

## Backend Endpoints You Still Need

The current backend is missing a few endpoints that the frontend needs. These should be added:

| Endpoint | Purpose | Needed By |
|---|---|---|
| `GET /api/invoices` | List all invoices with optional status/stage filters | Invoice Table page |
| `GET /api/invoices/{id}` | Get single invoice detail | Invoice Detail page |
| `GET /api/clients` | List unique clients with aggregated stats | Client Intelligence Hub |
| `GET /api/clients/{name}/context` | Fetch RAG context for a specific client | Client Intelligence Hub |
| `GET /api/compliance/stats` | Aggregate compliance pass/fail rates | Compliance Dashboard |
| `GET /api/graph/last-execution/{invoice_id}` | Return the node-by-node execution trace | LangGraph Visualizer |
