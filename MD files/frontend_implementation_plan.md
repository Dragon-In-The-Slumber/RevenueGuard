# RevenueGuard Dashboard — Frontend Implementation Plan

> **Status:** FINAL — Awaiting user approval  
> **Framework:** Next.js 16 (App Router) + React 19 + TailwindCSS v4 + SWR  
> **Backend:** FastAPI at `http://localhost:8000` (Docker) with WebSocket at `ws://localhost:8000/ws`  
> **Reference:** [frontend_features.md](file:///C:/Users/abhin/.gemini/antigravity/brain/44ca47e4-6098-4598-b6ea-caf110cc4993/frontend_features.md) · [project_core_context.md](file:///C:/Users/abhin/.gemini/antigravity/brain/44ca47e4-6098-4598-b6ea-caf110cc4993/project_core_context.md)

---

## Current State Assessment

### What We KEEP (The design system is excellent)
- [globals.css](file:///c:/PROGRAMER's%20FOLDER/Projects/RazorPay/RevenueGuard/v2_b2b/dashboard/src/app/globals.css) — Dark glassmorphism theme, CSS variables, animations, utility classes (`glass-panel`, `pill-btn`, `nav-item`, `mono-label`, `text-gradient`). This is production-quality.
- [layout.tsx](file:///c:/PROGRAMER's%20FOLDER/Projects/RazorPay/RevenueGuard/v2_b2b/dashboard/src/app/layout.tsx) — Root layout with Outfit font, Sidebar, ToastProvider.
- [ToastProvider.tsx](file:///c:/PROGRAMER's%20FOLDER/Projects/RazorPay/RevenueGuard/v2_b2b/dashboard/src/components/ToastProvider.tsx) — Notification system.
- `package.json` dependencies (Next.js 16, React 19, SWR, TailwindCSS v4).

### What We REWRITE (All v1 content)
- Every page (`page.tsx`, `audit/page.tsx`, `pipeline/page.tsx`, `settings/page.tsx`, `tx/[id]/page.tsx`)
- Every component (MetricsPanel, RecoveryPipeline, LiveEventFeed, etc.)
- Every API route (all proxy to wrong backend or use mock stores)
- Sidebar navigation links

### What We DELETE
- `src/lib/mockStore.ts` — v1 in-memory mock (we use the real FastAPI backend)
- `src/lib/mockPipeline.ts` — v1 pipeline simulation (replaced by LangGraph)
- `src/hooks/useSimulationStream.ts` — v1 SSE stream (we use WebSocket now)
- `src/app/api/*` — All Next.js API proxy routes (we call FastAPI directly)
- `src/app/pipeline/page.tsx` — v1 pipeline graph (replaced by LangGraph Visualizer)
- `src/app/tx/[id]/page.tsx` — v1 transaction detail (replaced by Invoice Detail)
- `src/app/settings/page.tsx` — v1 settings (replaced by Compliance Dashboard)
- `src/app/audit/page.tsx` — v1 audit page (replaced by full Audit Trail in Invoice Detail)

---

## New File Structure

```
src/
├── app/
│   ├── globals.css                      # KEEP (design system)
│   ├── layout.tsx                       # MODIFY (update metadata)
│   ├── page.tsx                         # REWRITE → Command Center
│   ├── invoices/
│   │   └── page.tsx                     # NEW → Invoice Management Table
│   ├── invoices/[id]/
│   │   └── page.tsx                     # NEW → Invoice Detail + Audit Trail
│   ├── graph/
│   │   └── page.tsx                     # NEW → LangGraph Execution Visualizer
│   ├── clients/
│   │   └── page.tsx                     # NEW → Client Intelligence Hub
│   ├── compliance/
│   │   └── page.tsx                     # NEW → Compliance Dashboard
│   └── events/
│       └── page.tsx                     # NEW → Webhook & Event Simulator
│
├── components/
│   ├── Sidebar.tsx                      # REWRITE (new nav links, virtual date)
│   ├── ToastProvider.tsx                # KEEP
│   │
│   ├── command-center/                  # NEW DIRECTORY
│   │   ├── KpiCards.tsx                 # Recovery metrics cards
│   │   ├── RecoveryFunnel.tsx           # Status distribution chart
│   │   ├── SimulationController.tsx     # Batch generate + tick + auto-run
│   │   └── ActivityTicker.tsx           # Live scrolling agent feed
│   │
│   ├── invoices/                        # NEW DIRECTORY
│   │   ├── InvoiceTable.tsx             # Sortable/filterable data table
│   │   ├── StatusBadge.tsx              # Color-coded status pill
│   │   ├── EscalationProgress.tsx       # STAGE_1→4 progress bar
│   │   └── QuickActions.tsx             # Reply/Webhook simulation buttons
│   │
│   ├── invoice-detail/                  # NEW DIRECTORY
│   │   ├── InvoiceHeader.tsx            # Invoice summary card
│   │   ├── AuditTimeline.tsx            # Chronological event timeline
│   │   ├── AuditTimelineEntry.tsx       # Single timeline event card
│   │   ├── EmailPreview.tsx             # Styled email content display
│   │   ├── ComplianceDiff.tsx           # Draft vs. Final side-by-side
│   │   ├── RagContextPanel.tsx          # RAG sidebar with retrieved docs
│   │   └── ReplySimulator.tsx           # Interactive demo panel
│   │
│   ├── graph/                           # NEW DIRECTORY
│   │   ├── LangGraphFlow.tsx            # Visual node-edge graph
│   │   ├── GraphNode.tsx                # Single node component
│   │   └── ExecutionTrace.tsx           # Animated path highlight
│   │
│   ├── clients/                         # NEW DIRECTORY
│   │   ├── ClientCard.tsx               # Rich client profile card
│   │   ├── RagSearchBar.tsx             # Interactive RAG query demo
│   │   └── ClientInvoiceList.tsx        # Invoices for a specific client
│   │
│   ├── compliance/                      # NEW DIRECTORY
│   │   ├── ComplianceScore.tsx          # Big pass/fail score display
│   │   ├── RejectedDraftsGallery.tsx    # Feed of Judge-rejected emails
│   │   └── CooldownBoard.tsx            # Active cooldown timers
│   │
│   └── events/                          # NEW DIRECTORY
│       ├── WebhookFirePanel.tsx          # Event type selector + fire button
│       └── EventLog.tsx                 # Chronological webhook event log
│
├── hooks/
│   ├── useWebSocket.ts                  # NEW — WebSocket connection to FastAPI
│   ├── useApi.ts                        # NEW — SWR wrapper with base URL config
│   └── useVirtualDate.ts                # NEW — Global virtual date state
│
├── lib/
│   ├── api.ts                           # NEW — API client (fetch wrapper with base URL)
│   ├── types.ts                         # NEW — TypeScript interfaces for all API responses
│   └── constants.ts                     # NEW — Status colors, stage labels, event icons
│
└── favicon.ico                          # KEEP
```

---

## Phase 0: Foundation (Clean Up + Infrastructure)

> Delete all v1 code and set up the shared infrastructure every page depends on.

### [DELETE] Files to Remove
```
src/lib/mockStore.ts
src/lib/mockPipeline.ts
src/hooks/useSimulationStream.ts
src/app/api/                          # Entire directory (all proxy routes)
src/app/audit/page.tsx
src/app/pipeline/page.tsx
src/app/settings/page.tsx
src/app/tx/                           # Entire directory
src/components/AuditTrailViewer.tsx
src/components/BackendStatus.tsx
src/components/BatchSimulatorButton.tsx
src/components/InlineSimulator.tsx
src/components/LiveEventFeed.tsx
src/components/MetricsPanel.tsx
src/components/RecoveryPipeline.tsx
src/components/TransactionModal.tsx
```

### [NEW] `src/lib/api.ts` — API Client

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API Error: ${res.status}`);
  return res.json();
}

export const apiPost = <T>(path: string, body: unknown) =>
  apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) });
```

### [NEW] `src/lib/types.ts` — Shared TypeScript Interfaces

```typescript
// Must match the backend's InvoiceStatus enum and API responses exactly
export type InvoiceStatus =
  | "ISSUED" | "OVERDUE" | "NOTIFIED_1" | "NOTIFIED_2" | "NOTIFIED_3"
  | "PAUSED_PTP" | "DISPUTE" | "LEGAL_HOLD" | "UNRESPONSIVE"
  | "RECOVERED" | "HUMAN_ESCALATED";

export interface Invoice {
  id: number;
  amount: number;
  client_name: string;
  client_email: string;
  due_date: string;
  status: InvoiceStatus;
  promised_date: string | null;
  escalation_stage: string;
  razorpay_payment_link_id: string | null;
  razorpay_virtual_account_id: string | null;
}

export interface AuditLogEntry {
  id: number;
  invoice_id: number;
  client_name?: string;
  timestamp: string;
  event_type: string;
  agent_reasoning: string | null;
  action_taken: string;
  rule_applied: string | null;
  content_snapshot: string | null;
  compliance_verdict: string | null;
}

export interface Metrics {
  totalAtRisk: number;
  totalRecovered: number;
  recoveryRate: number;
  totalInvoices: number;
  recoveredInvoices: number;
}

export interface FunnelEntry {
  status: InvoiceStatus;
  count: number;
  amount: number;
}
```

### [NEW] `src/lib/constants.ts` — Status Colors, Icons, Labels

Maps every `InvoiceStatus` to a color, icon, and label for consistent rendering across all components.

```typescript
export const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string; icon: string }> = {
  ISSUED:           { color: "text-blue-400",    bg: "bg-blue-500/10",    label: "Issued",           icon: "📄" },
  OVERDUE:          { color: "text-amber-400",   bg: "bg-amber-500/10",   label: "Overdue",          icon: "⏰" },
  NOTIFIED_1:       { color: "text-cyan-400",    bg: "bg-cyan-500/10",    label: "Stage 1 Sent",     icon: "📧" },
  NOTIFIED_2:       { color: "text-purple-400",  bg: "bg-purple-500/10",  label: "Stage 2 Sent",     icon: "📧" },
  NOTIFIED_3:       { color: "text-orange-400",  bg: "bg-orange-500/10",  label: "Stage 3 Sent",     icon: "📱" },
  PAUSED_PTP:       { color: "text-yellow-400",  bg: "bg-yellow-500/10",  label: "Promise to Pay",   icon: "🤝" },
  DISPUTE:          { color: "text-red-400",     bg: "bg-red-500/10",     label: "Disputed",         icon: "⚔️" },
  LEGAL_HOLD:       { color: "text-red-500",     bg: "bg-red-600/10",     label: "Legal Hold",       icon: "🚫" },
  UNRESPONSIVE:     { color: "text-gray-400",    bg: "bg-gray-500/10",    label: "Unresponsive",     icon: "👻" },
  RECOVERED:        { color: "text-emerald-400", bg: "bg-emerald-500/10", label: "Recovered",        icon: "✅" },
  HUMAN_ESCALATED:  { color: "text-pink-400",    bg: "bg-pink-500/10",    label: "Human Escalated",  icon: "👤" },
};

export const EVENT_TYPE_CONFIG: Record<string, { color: string; icon: string }> = {
  EMAIL_SENT:          { color: "text-emerald-400", icon: "📧" },
  INTENT_CLASSIFIED:   { color: "text-cyan-400",    icon: "🤖" },
  STATUS_CHANGED:      { color: "text-amber-400",   icon: "🔄" },
  ESCALATION_BLOCKED:  { color: "text-red-400",     icon: "🛑" },
  COMPLIANCE_PASSED:   { color: "text-emerald-400", icon: "✅" },
  COMPLIANCE_FAILED:   { color: "text-red-400",     icon: "❌" },
  TOOL_CALL:           { color: "text-purple-400",  icon: "🔧" },
  HUMAN_ESCALATED:     { color: "text-pink-400",    icon: "👤" },
  PAYMENT_RECEIVED:    { color: "text-emerald-400", icon: "💰" },
};
```

### [NEW] `src/hooks/useWebSocket.ts` — Real-time Updates

```typescript
"use client";
import { useEffect, useCallback } from "react";
import { mutate } from "swr";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export function useWebSocket() {
  const refresh = useCallback(() => {
    // Revalidate all SWR caches when the backend broadcasts a state update
    mutate(() => true); // Revalidates ALL SWR keys
  }, []);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      ws = new WebSocket(WS_URL);
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.event === "state_updated") {
          refresh();
        }
      };
      ws.onclose = () => {
        reconnectTimeout = setTimeout(connect, 3000);
      };
    };
    connect();

    return () => {
      ws?.close();
      clearTimeout(reconnectTimeout);
    };
  }, [refresh]);
}
```

### [NEW] `src/hooks/useApi.ts` — SWR Fetcher with Base URL

```typescript
"use client";
import useSWR, { SWRConfiguration } from "swr";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const fetcher = (path: string) => fetch(`${API_BASE}${path}`).then(r => r.json());

export function useApi<T>(path: string | null, config?: SWRConfiguration) {
  return useSWR<T>(path, fetcher, { refreshInterval: 5000, ...config });
}
```

### [MODIFY] `src/components/Sidebar.tsx` — New Navigation

Rewrite with new nav links matching the 7-page structure:

| Icon | Label | Path |
|---|---|---|
| 📊 | Command Center | `/` |
| 📋 | Invoices | `/invoices` |
| 🧠 | AI Graph | `/graph` |
| 👥 | Client Intel | `/clients` |
| ⚖️ | Compliance | `/compliance` |
| 🔔 | Events | `/events` |

Add a **Virtual Date Display** at the top of the sidebar showing the current simulation date.
Add a **Backend Status Indicator** (green dot = connected, amber = demo mode) at the bottom.

### [MODIFY] `src/app/layout.tsx`

Update metadata title/description. No structural changes needed.

---

## Phase 1: Command Center (Home Page)

> The first page judges see. Proves Pillar 1: "Measured money recovered across a batch."

### [REWRITE] `src/app/page.tsx`

Layout:
```
┌──────────────────────────────────────────────────┐
│ AI Command Center        [Simulation Controller] │
├──────────────────────────────────────────────────┤
│ ┌─KPI──┐ ┌─KPI──┐ ┌─KPI──┐ ┌─KPI──┐ ┌─KPI──┐  │
│ │₹ Risk│ │₹ Recv│ │ Rate │ │Total │ │Recvd │  │
│ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘  │
│                                                  │
│ ┌──── Recovery Funnel ────┐ ┌── Activity Feed ──┐│
│ │ [====] OVERDUE     23   │ │ 📧 Acme Corp...  ││
│ │ [===]  NOTIFIED    18   │ │ 🤖 Globex Sol... ││
│ │ [==]   PAUSED_PTP   5   │ │ ✅ NovaTech...   ││
│ │ [==]   RECOVERED   12   │ │ 🛑 Pinnacle...   ││
│ │ [=]    DISPUTED     3   │ │                   ││
│ └─────────────────────────┘ └───────────────────┘│
└──────────────────────────────────────────────────┘
```

### [NEW] Components

#### `src/components/command-center/SimulationController.tsx`
- "Generate 100 Invoices" button → `POST /api/invoices/simulate_batch` with `{"count": 100}`
- "Advance 1 Day" button → `POST /api/simulation/tick`
- "Auto-Run 30 Days" button → calls tick endpoint 30 times with 1-second intervals using `setInterval`, with a progress bar showing day X/30
- Shows the current Virtual Date from the tick response
- All buttons use the existing `pill-btn` / `pill-btn primary` classes
- Disable buttons during processing with loading spinners

#### `src/components/command-center/KpiCards.tsx`
- Fetches `GET /api/metrics`
- 5 cards in a row using `glass-panel`:
  1. **Total At Risk** — `₹{totalAtRisk.toLocaleString('en-IN')}` — amber icon
  2. **Total Recovered** — `₹{totalRecovered.toLocaleString('en-IN')}` — green icon, animated counter
  3. **Recovery Rate** — `{recoveryRate}%` — circular SVG progress gauge
  4. **Total Invoices** — count — blue icon
  5. **Recovered Invoices** — count — emerald icon
- Use `animate-fade-in` with stagger classes for entrance animation
- Numbers should use `font-mono` for alignment

#### `src/components/command-center/RecoveryFunnel.tsx`
- Fetches `GET /api/funnel`
- Horizontal bar chart showing each status with:
  - Status badge (using `StatusBadge` component)
  - Count label
  - Amount label (₹)
  - Proportional bar width (percentage of total)
  - Bar color from `STATUS_CONFIG`
- Sorted by count descending
- Animate bars on data change (CSS transition on `width`)

#### `src/components/command-center/ActivityTicker.tsx`
- Fetches `GET /api/audit-logs` (returns 20 most recent across all invoices)
- Scrolling list inside a `glass-panel` with `max-h-[500px] overflow-y-auto no-scrollbar`
- Each entry shows:
  - Colored dot (from `EVENT_TYPE_CONFIG`)
  - Timestamp (relative: "2m ago")
  - Client name (bold)
  - Action taken (truncated to 1 line)
- Click an entry → navigate to `/invoices/{invoice_id}`

---

## Before proceeding with the Phase 2: Invoice Management Table as described in [frontend_implementation_plan.md](file;file:///c%3A/PROGRAMER%27s%20FOLDER/Projects/RazorPay/RevenueGuard/v2_b2b/MD%20files/frontend_implementation_plan.md)   just do a thorough check to ensure each and every step mentioned in the phase 1 is completed and the goal set for phase 1 is achieved or not.

> Core CRUD view. Judges need to browse, filter, and click into invoices.

> [!IMPORTANT]
> **Backend requirement:** You need a new endpoint `GET /api/invoices` that returns all invoices. The current backend does not expose this. Add it to `dashboard_api.py`:
> ```python
> @router.get("/api/invoices")
> async def get_all_invoices(status: str = None, db: AsyncSession = Depends(get_db)):
>     query = select(Invoice)
>     if status:
>         query = query.where(Invoice.status == InvoiceStatus(status))
>     query = query.order_by(Invoice.due_date.desc())
>     result = await db.execute(query)
>     invoices = result.scalars().all()
>     return {"invoices": [{ ...invoice fields... } for inv in invoices]}
> ```

### [NEW] `src/app/invoices/page.tsx`

Layout:
```
┌──────────────────────────────────────────────────┐
│ Invoice Management            [Filter ▾] [Search]│
├──────────────────────────────────────────────────┤
│ ID  │ Client        │ Amount    │ Due    │ Stage │
│─────┼───────────────┼───────────┼────────┼───────│
│ 42  │ Acme Corp     │ ₹12,50,000│ Oct 1  │ ██░░ │
│ 87  │ Globex Sol.   │  ₹3,40,000│ Sep 15 │ ███░ │
│ 103 │ NovaTech Labs │    ₹80,000│ Aug 20 │ █░░░ │
│                                                  │
│ [Simulate Reply] [Simulate Payment] [View Trail] │
└──────────────────────────────────────────────────┘
```

### [NEW] Components

#### `src/components/invoices/InvoiceTable.tsx`
- Fetches `GET /api/invoices` via `useApi`
- Columns: ID, Client Name, Amount (₹ formatted), Due Date, Days Overdue, Status (`StatusBadge`), Escalation Stage (`EscalationProgress`), Actions
- **Sorting:** Click column headers to sort (client-side)
- **Filtering:** Status dropdown (all 11 values), search input for client name
- **Row click:** Navigate to `/invoices/{id}`
- Alternating row backgrounds with subtle hover effect

#### `src/components/invoices/StatusBadge.tsx`
- Takes `status: InvoiceStatus` prop
- Renders a rounded pill with icon + label + color from `STATUS_CONFIG`
- Example: `🤝 Promise to Pay` with yellow background

#### `src/components/invoices/EscalationProgress.tsx`
- Takes `stage: string` prop (STAGE_1 through STAGE_4)
- Renders 4 small dots/segments, filled based on stage
- Tooltip showing stage label on hover

#### `src/components/invoices/QuickActions.tsx`
- Three icon buttons per invoice row:
  1. 💬 **Reply** — Opens a modal with text input → `POST /api/invoices/{id}/reply`
  2. 💰 **Pay** — Fires `POST /api/webhooks/razorpay` with `{"event": "invoice.paid", "payload": {"invoice_id": id}}`
  3. 📋 **Trail** — Links to `/invoices/{id}`

---

## Phase 3: Invoice Detail & Audit Trail

> The centrepiece of the demo. Where you prove Pillar 4: Audit Trail.

### [NEW] `src/app/invoices/[id]/page.tsx`

Layout:
```
┌──────────────────────────────────────────────────┐
│ ← Back   Invoice #42                            │
├────────────────────────────┬─────────────────────┤
│ ┌─ Invoice Header ───────┐ │ ┌─ RAG Context ──┐ │
│ │ Acme Corp              │ │ │ Contract: Net60 │ │
│ │ ₹12,50,000  22d overdue│ │ │ Risk: LOW      │ │
│ │ Stage: ██░░ (STAGE_2)  │ │ │ Contact: Rajesh│ │
│ │ PTP: None              │ │ │ History: 10/12 │ │
│ │ Link: rzp.io/l/abc123  │ │ │  on-time       │ │
│ └────────────────────────┘ │ └────────────────┘ │
│                            │                     │
│ ┌─ Audit Timeline ──────┐ │ ┌─ Demo Panel ───┐ │
│ │ ● Nov 1  STATUS_CHANGED│ │ │ [Will pay Fri] │ │
│ │   → OVERDUE            │ │ │ [Dispute]      │ │
│ │                        │ │ │ [Stop contact] │ │
│ │ ● Nov 2  EMAIL_SENT   │ │ │ [Extension]    │ │
│ │   🤖 AI Reasoning ▼   │ │ │                │ │
│ │   📧 Email Preview ▼  │ │ │ [💰 Sim. Pay]  │ │
│ │   ⚖️ Judge: PASS ✅   │ │ │ [⚔️ Sim. Disp] │ │
│ │                        │ │ │ [❌ Sim. Fail] │ │
│ │ ● Nov 3  INTENT_CLASS. │ │ │                │ │
│ │   → PROMISE_TO_PAY 94%│ │ │ ┌─ Text Input ┐│ │
│ └────────────────────────┘ │ │ │ Type reply...││ │
│                            │ │ └──────────────┘│ │
│                            │ └────────────────┘ │
└────────────────────────────┴─────────────────────┘
```

### [NEW] Components

#### `src/components/invoice-detail/InvoiceHeader.tsx`
- Props: `invoice: Invoice`
- Large card showing: client name, email, amount, due date, days overdue (calculated), status (large `StatusBadge`), escalation stage (`EscalationProgress`), promised date (if set), Razorpay Payment Link (clickable `<a>` tag), Virtual Account ID

#### `src/components/invoice-detail/AuditTimeline.tsx`
- Fetches `GET /api/invoices/{id}/audit-logs`
- Renders a vertical timeline with a thin line connecting entries
- Each entry is an `AuditTimelineEntry` component

#### `src/components/invoice-detail/AuditTimelineEntry.tsx`
- Props: `entry: AuditLogEntry`
- Colored dot on the timeline (from `EVENT_TYPE_CONFIG`)
- Timestamp (formatted: "Nov 2, 2024 · 14:32")
- Event type badge
- Action taken text
- **Expandable accordion sections** (click to toggle):
  1. **🤖 AI Reasoning** — Shows `agent_reasoning` in a monospaced code block
  2. **📜 Rule Applied** — Shows `rule_applied` in a highlighted box
  3. **⚖️ Compliance** — Shows `compliance_verdict` as PASS ✅ or FAIL ❌
  4. **📧 Email Content** — Shows `content_snapshot` in a styled email preview card (`EmailPreview` component)

#### `src/components/invoice-detail/EmailPreview.tsx`
- Props: `emailBody: string`
- Renders the email content in a card styled like an actual email:
  - Light header bar with "To:", "Subject:", timestamp
  - White/light content area with the email body (respecting line breaks)
  - `{{payment_link}}` placeholders rendered as clickable blue links

#### `src/components/invoice-detail/ComplianceDiff.tsx`
- Shows when a draft was rejected and rewritten
- **Two adjacent** `EmailPreview` cards:
  - Left: Original draft (with violations highlighted in red using text markers like ~~strikethrough~~ or red background)
  - Right: Approved rewrite
- Judge's feedback displayed between them
- Needs 2+ consecutive audit entries (COMPLIANCE_FAILED then COMPLIANCE_PASSED) to render

#### `src/components/invoice-detail/RagContextPanel.tsx`
- Fetches RAG context for the client (needs new endpoint: `GET /api/clients/{name}/context`)
- Displays in a sidebar card:
  - Company tier badge (Enterprise/SME/Startup)
  - Contract terms
  - Key contact
  - Risk level (color-coded: green LOW, amber HIGH, red EXTREME)
  - Payment history summary
  - Strategic guardrails (displayed as warning boxes)

#### `src/components/invoice-detail/ReplySimulator.tsx`
- **Quick Reply Buttons:**
  - 💬 "We will pay by Friday" → sends `{"message": "We will pay by this Friday"}`
  - ⚠️ "Wrong amount, we dispute" → sends `{"message": "The amount billed is incorrect, we are disputing this invoice"}`
  - 🚫 "Stop contacting us" → sends `{"message": "Please stop contacting us regarding this matter"}`
  - 🤝 "Need 2-week extension" → sends `{"message": "Can we get a two week extension on this payment?"}`
- **Custom Text Input:** Textarea + Send button for free-form replies
- All call `POST /api/invoices/{id}/reply` with `{"message": text}`
- Show the classified intent result in a toast notification after submission
- **Webhook Simulation Buttons:**
  - 💰 "Simulate Payment" → `POST /api/webhooks/razorpay` with `{"event": "invoice.paid", ...}`
  - ⚔️ "Simulate Dispute" → `{"event": "payment.dispute.created", ...}`
  - ❌ "Simulate Failed Payment" → `{"event": "payment.failed", ...}`

---

## Phase 4: LangGraph Visualizer

> The biggest differentiator. No other team will have a visual of their AI's decision graph.

### [NEW] `src/app/graph/page.tsx`

> [!IMPORTANT]
> **Install dependency:** `npm install @xyflow/react` (React Flow v12 — the library for interactive node graphs)

Layout:
```
┌──────────────────────────────────────────────────┐
│ LangGraph Execution Visualizer                   │
├──────────────────────────────────────────────────┤
│                                                  │
│     [check_overdue] ──→ [check_cooldown]         │
│                              │                   │
│                    ┌─────────┴─────────┐         │
│                    ▼                   ▼         │
│           [log_blocked]    [retrieve_context]     │
│                                  │               │
│                           [classify_reply]        │
│                     ┌────────────┴──────┐        │
│                     ▼                   ▼        │
│              [execute_action]    [draft_email]    │
│                                      │           │
│                             [evaluate_compliance] │
│                        ┌─────────────┴────┐      │
│                        ▼                  ▼      │
│               [call_razorpay_tools]  [draft_email]│
│                        │              (rewrite)   │
│                        ▼                         │
│                 [execute_action]                  │
│                        │                         │
│                 [simulate_client]                 │
│                        │                         │
│                     [END]                        │
│                                                  │
│ ─────────────────────────────────────            │
│ Last Execution: Invoice #42 (Acme Corp)          │
│ Path: check_overdue → check_cooldown →           │
│   retrieve_context → draft_email →               │
│   evaluate_compliance(FAIL) → draft_email →      │
│   evaluate_compliance(PASS) → call_razorpay →    │
│   execute_action → simulate_client               │
└──────────────────────────────────────────────────┘
```

### [NEW] Components

#### `src/components/graph/LangGraphFlow.tsx`
- Uses `@xyflow/react` to render the LangGraph topology
- **Static nodes** matching the actual graph in `builder.py`:
  - `check_overdue`, `check_cooldown`, `log_blocked`, `retrieve_client_context`, `classify_reply`, `draft_email`, `evaluate_compliance`, `call_razorpay_tools`, `execute_action`, `simulate_client`
- **Edges** with labels matching `edges.py` routing conditions
- **Node colors:** Default gray. Highlight nodes in green when they were part of the last execution path
- Custom node component (`GraphNode`) showing:
  - Node name
  - Brief description
  - Active indicator (glow effect when highlighted)

#### `src/components/graph/GraphNode.tsx`
- Props: `name: string`, `description: string`, `isActive: boolean`, `color: string`
- Glass panel style node with conditional glow animation
- Small icon indicating node type (🔍 for check, 🧠 for LLM, 🔧 for tools, ⚖️ for compliance)

#### `src/components/graph/ExecutionTrace.tsx`
- Below the graph visualization
- Shows the most recent execution path as a horizontal breadcrumb trail
- Each step shows the node name, the key state values at that point, and duration
- Uses audit log data to reconstruct the path (event types map to node names)

---

## Phase 5: Client Intelligence Hub + Compliance Dashboard

### [NEW] `src/app/clients/page.tsx`

> [!IMPORTANT]
> **Backend requirement:** New endpoint `GET /api/clients/{name}/context` that queries ChromaDB and returns the RAG profile for a client.

#### `src/components/clients/ClientCard.tsx`
- Rich card for each of the 4 hero clients
- Shows: company name, tier badge, contract terms, key contact, risk level, payment history as a mini bar chart, strategic guardrails as warning tags
- Click → shows all invoices for that client inline

#### `src/components/clients/RagSearchBar.tsx`
- Text input: "Ask about any client..."
- Calls the RAG search endpoint
- Shows the raw ChromaDB results in a formatted response box
- Pre-loaded example queries: "What are Globex's payment terms?", "Has Pinnacle disputed before?"

#### `src/components/clients/ClientInvoiceList.tsx`
- Mini invoice table filtered to a specific client
- Shows status distribution as a mini funnel

### [NEW] `src/app/compliance/page.tsx`

#### `src/components/compliance/ComplianceScore.tsx`
- Large circular gauge showing "X/X emails passed compliance" 
- "100% compliance rate" in bold
- Total emails checked, total passes, total failures

#### `src/components/compliance/RejectedDraftsGallery.tsx`
- Feed of audit entries where `compliance_verdict == "FAIL"`
- Each entry shows:
  - The rejected email text (with violations highlighted)
  - The Judge's reason
  - The rule that was violated (Rule 1-8)
  - The rewritten, approved version (if available)
- Uses `ComplianceDiff` component from Phase 3

#### `src/components/compliance/CooldownBoard.tsx`
- For every active (non-terminal) invoice, show:
  - Client name
  - Last email sent date
  - Next email permitted date (last + 4 days)
  - Visual countdown timer or "Ready" badge

---

## Phase 6: Webhook & Event Simulator

### [NEW] `src/app/events/page.tsx`

#### `src/components/events/WebhookFirePanel.tsx`
- Dropdown: Select invoice (fetches from `/api/invoices`)
- Dropdown: Select event type:
  - `invoice.paid` — Payment received in full
  - `invoice.partially_paid` — Partial payment received
  - `payment_link.paid` — Payment Link clicked and paid
  - `payment.dispute.created` — Formal dispute filed
  - `payment.failed` — Payment attempt failed
  - `virtual_account.credited` — Bank transfer received
- "Fire Event" button → `POST /api/webhooks/razorpay`
- Response display showing what happened

#### `src/components/events/EventLog.tsx`
- Chronological log of all webhook events fired during this session (stored in React state)
- Each entry shows: timestamp, event type, invoice ID, system response

---

## Missing Backend Endpoints

> [!WARNING]
> The following endpoints MUST be added to the FastAPI backend before the frontend can work. Add these to `src/dashboard_api.py` in the backend.

| Endpoint | Method | Returns | Needed By |
|---|---|---|---|
| `/api/invoices` | GET | `{"invoices": [...]}` with optional `?status=` filter | Invoice Table (Phase 2) |
| `/api/invoices/{id}` | GET | Single invoice object | Invoice Detail (Phase 3) |
| `/api/clients` | GET | `{"clients": [{name, invoice_count, total_amount, recovered_amount, risk_level}]}` | Client Hub (Phase 5) |
| `/api/clients/{name}/context` | GET | `{"context": "RAG text", "profile": {...}}` — queries ChromaDB | Client Hub + RAG Panel (Phase 5) |
| `/api/compliance/stats` | GET | `{"total_checked": N, "passed": N, "failed": N, "rate": 100.0}` | Compliance Dashboard (Phase 5) |
| `/api/compliance/rejected` | GET | `{"rejected": [AuditLogEntry where compliance_verdict == "FAIL"]}` | Compliance Dashboard (Phase 5) |

---

## Execution Instructions for Antigravity IDE

Execute each phase as a separate prompt in the IDE:

### Phase 0 Prompt:
> "Read the frontend implementation plan at `.gemini/antigravity/brain/44ca47e4-6098-4598-b6ea-caf110cc4993/frontend_implementation_plan.md`. Execute Phase 0: Delete all v1 files listed in the DELETE section. Then create the new infrastructure files: `src/lib/api.ts`, `src/lib/types.ts`, `src/lib/constants.ts`, `src/hooks/useWebSocket.ts`, `src/hooks/useApi.ts`. Rewrite `src/components/Sidebar.tsx` with the new navigation. Do NOT create any pages yet."

### Phase 1 Prompt:
> "Continue executing the frontend plan. Phase 1: Rewrite `src/app/page.tsx` as the Command Center. Create all 4 components in `src/components/command-center/`. Use the existing `glass-panel`, `pill-btn`, `mono-label` CSS classes from globals.css. The API base URL is `http://localhost:8000`."

### Phase 2 Prompt:
> "Continue executing the frontend plan. Phase 2: Create the Invoice Management Table at `src/app/invoices/page.tsx`. Create all 4 components in `src/components/invoices/`. First, add the missing `GET /api/invoices` endpoint to the FastAPI backend at `v2_b2b/src/dashboard_api.py`."

### Phase 3 Prompt:
> "Continue executing the frontend plan. Phase 3: Create the Invoice Detail page at `src/app/invoices/[id]/page.tsx`. Create all 7 components in `src/components/invoice-detail/`. This is the most important page — the audit timeline with expandable AI reasoning, email previews, compliance diffs, RAG context sidebar, and interactive reply simulator. First, add the missing `GET /api/invoices/{id}` endpoint to the FastAPI backend."

### Phase 4 Prompt:
> "Continue executing the frontend plan. Phase 4: Install `@xyflow/react` via npm. Create the LangGraph Execution Visualizer at `src/app/graph/page.tsx`. Create all 3 components in `src/components/graph/`. The graph topology must match the actual LangGraph in `v2_b2b/src/graph/builder.py`."

### Phase 5 Prompt:
> "Continue executing the frontend plan. Phase 5: Create the Client Intelligence Hub at `src/app/clients/page.tsx` and the Compliance Dashboard at `src/app/compliance/page.tsx`. Create all 6 components in `src/components/clients/` and `src/components/compliance/`. First, add the missing backend endpoints: `GET /api/clients`, `GET /api/clients/{name}/context`, `GET /api/compliance/stats`, `GET /api/compliance/rejected`."

### Phase 6 Prompt:
> "Continue executing the frontend plan. Phase 6: Create the Webhook & Event Simulator at `src/app/events/page.tsx`. Create the 2 components in `src/components/events/`. This page calls `POST /api/webhooks/razorpay` which already exists in the backend."

---

## Verification Checklist

After all phases are complete, verify:

- [ ] `npm run dev` starts without errors on `http://localhost:3000`
- [ ] Command Center shows KPI cards and funnel when backend is running
- [ ] "Generate Batch" creates 100 invoices visible in the Invoice Table
- [ ] "Advance 1 Day" updates the virtual date and triggers agent processing
- [ ] Clicking an invoice opens the Detail page with full audit timeline
- [ ] Audit entries have expandable AI reasoning and email previews
- [ ] Reply Simulator sends a message and shows the classified intent
- [ ] LangGraph Visualizer renders the correct node topology
- [ ] Client Hub shows all 4 hero client profiles
- [ ] RAG Search returns relevant context
- [ ] Compliance Dashboard shows pass/fail stats
- [ ] Webhook Simulator fires events and updates invoice status in real-time
- [ ] WebSocket connection triggers automatic UI refreshes after every tick
