<p align="center">
  <h1 align="center">💰 RevenueGuard</h1>
  <p align="center">
    <strong>AI-Driven B2B Receivables Recovery Agent</strong>
  </p>
  <p align="center">
    Built for the <a href="https://razorpay.com/">Razorpay AI Buildathon</a> — Track 03: AI Revenue Recovery
  </p>
</p>

---

RevenueGuard is an autonomous agent that recovers overdue B2B invoices using **LangGraph** for orchestration, **RAG** for client-aware context, a **dual-LLM compliance loop**, and **Razorpay** for payments — all surfaced through a real-time **Next.js 16** command-center dashboard.

## ✨ Key Features

| Capability | Description |
|---|---|
| **Agentic Recovery Workflow** | A 16-node LangGraph state machine decides *what* to do (email, SMS, offer a discount, wait, escalate) — not just *when* to email. |
| **Dual-LLM Compliance Loop** | A second model reviews every draft against an 8-rule rubric and can force a rewrite before anything is sent. |
| **RAG Client Profiles** | ChromaDB stores per-client narratives (contract terms, payment history, risk). The agent reads them; the policy guard enforces them. |
| **Razorpay Integration** | Payment Links and Smart Collect virtual accounts via the official SDK, with idempotent webhook ingestion for `payment_link.paid` events. |
| **Policy Guard & Stopping Rules** | Five hard-coded stopping rules (PTP grace, disputes, opt-outs, contact caps, legal holds) that the LLM cannot override. |
| **Simulation Harness** | A virtual-date simulation engine with seeded randomness for reproducible A/B comparison between the agent policy and a fixed-schedule baseline. |
| **Real-Time Dashboard** | WebSocket-powered Next.js 16 UI with live graph traversal animation, invoice drill-down, compliance audit trail, and simulation controls. |

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Next.js 16 Dashboard                        │
│  (Command Center · Invoices · Clients · Compliance · Graph · Events)│
└──────────────────────────────┬──────────────────────────────────────┘
                               │  REST + WebSocket
┌──────────────────────────────▼──────────────────────────────────────┐
│                        FastAPI  (src/main.py)                       │
│  Simulation endpoints · Razorpay webhooks · Dashboard API           │
└───────┬──────────────┬──────────────┬───────────────────────────────┘
        │              │              │
  ┌─────▼─────┐  ┌─────▼─────┐  ┌────▼────┐
  │ LangGraph │  │  Engine    │  │   RAG   │
  │  (graph/) │  │ core_loop  │  │ ChromaDB│
  │ 16 nodes  │  │  owns all  │  │ client  │
  │  + edges  │  │  DB writes │  │ context │
  └─────┬─────┘  └─────┬─────┘  └────┬────┘
        │              │              │
  ┌─────▼─────┐  ┌─────▼─────┐  ┌────▼────┐
  │    AI     │  │Persistence│  │  Tools  │
  │ LLM draft │  │SQLAlchemy │  │ Razorpay│
  │ Compliance│  │  Postgres │  │ Payment │
  │  Intent   │  │  Alembic  │  │  Links  │
  └───────────┘  └───────────┘  └─────────┘
```

### LangGraph Recovery Pipeline

```
check_overdue → check_stop_conditions → check_cooldown → retrieve_client_context
    → classify_reply → decide_action → validate_action (policy guard)
        ├── draft_email → evaluate_compliance → call_razorpay_tools → execute_action
        ├── draft_sms → evaluate_compliance → ...
        ├── prepare_offer → draft_email → ...
        ├── act_wait → simulate_client
        ├── act_escalate → notify_human
        └── act_close → notify_human
```

## 🧰 Tech Stack

### Backend
- **Python 3.11** · **FastAPI** · **Uvicorn**
- **LangGraph** — agentic state-machine orchestration
- **LangChain** + **Anthropic** / **Google Gemini** — LLM provider (auto-selects whichever key is present)
- **ChromaDB** — vector store for RAG client profiles
- **SQLAlchemy 2.0** (async) + **Alembic** — PostgreSQL ORM & migrations
- **Redis** — caching & pub/sub
- **Razorpay SDK** — payment links, Smart Collect, webhooks

### Frontend
- **Next.js 16** (App Router) · **React 19** · **TypeScript 5**
- **SWR** — data fetching & cache invalidation
- **@xyflow/react** — interactive graph visualisation
- **Tailwind CSS 4** — styling
- **WebSocket** — real-time simulation updates

### Infrastructure
- **Docker Compose** — API + Dashboard + PostgreSQL + Redis
- **Render** — cloud deployment (render.yaml blueprint)

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Node.js 20+](https://nodejs.org/) (for local dashboard development)
- At least one LLM API key (Anthropic or Google). Without one, the agent falls back to a keyword-based heuristic.

### 1. Clone & Configure

```bash
git clone https://github.com/<your-org>/RevenueGuard.git
cd RevenueGuard
cp .env.example .env
```

Edit `.env` and add your API keys:

```dotenv
# Pick one (or both — the system auto-selects):
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Optional — enables real payment link creation:
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
```

### 2. Start Everything

```bash
# Spin up the full stack (API :8000, Dashboard :3000, Postgres :5433, Redis :6380)
docker compose up --build
```

Or, run the dashboard in dev mode for hot-reload:

```bash
docker compose up --build api db redis   # Backend services
cd dashboard && npm install && npm run dev  # Dashboard on :3000
```

### 3. Open the Dashboard

Navigate to **http://localhost:3000** — the Command Center is the home page.

### 4. Run a Simulation

1. Click **Reset & Seed** to generate invoices for the 4 hero clients.
2. Hit **▶ Start** to begin ticking through virtual days.
3. Watch the agent decide, draft, comply, and recover in real time.

## 📁 Project Structure

```
RevenueGuard/
├── src/
│   ├── main.py                  # FastAPI app — simulation + webhook endpoints
│   ├── dashboard_api.py         # Read-only REST endpoints for the UI + WebSocket
│   ├── config.py                # Pydantic Settings (env vars)
│   ├── schemas.py               # Request/response models
│   ├── websocket.py             # WebSocket connection manager
│   │
│   ├── graph/                   # LangGraph orchestration
│   │   ├── state.py             # RecoveryState TypedDict (30+ fields)
│   │   ├── nodes.py             # 16 graph nodes (pure state mutations)
│   │   ├── edges.py             # Conditional routing functions
│   │   ├── builder.py           # Graph compilation (recovery + reply sub-graph)
│   │   └── policy_guard.py      # Policy validation & action veto logic
│   │
│   ├── ai/                      # LLM layer
│   │   ├── llm.py               # Email drafting + intent classification
│   │   ├── compliance_judge.py  # 8-rule compliance rubric (dual-LLM)
│   │   └── agent_policy.py      # Agentic action selection (Phase 2)
│   │
│   ├── rag/                     # Retrieval-Augmented Generation
│   │   ├── vector_store.py      # ChromaDB query interface
│   │   └── seed_data.py         # Hero client profile seeding
│   │
│   ├── domain/
│   │   └── clients.py           # Client profiles — single source of truth
│   │
│   ├── engine/
│   │   └── core_loop.py         # Per-tick orchestrator (sole DB writer)
│   │
│   ├── persistence/             # Database layer
│   │   ├── models.py            # SQLAlchemy models (Invoice, AuditLog, WebhookEvent)
│   │   ├── crud.py              # Create/Read/Update operations
│   │   └── database.py          # Async engine & session factory
│   │
│   ├── integrations/
│   │   └── razorpay_client.py   # Razorpay SDK wrapper (payment links, webhooks)
│   │
│   ├── tools/
│   │   └── registry.py          # Audited tool layer (all side effects)
│   │
│   ├── simulation/
│   │   ├── runner.py            # A/B simulation runner
│   │   └── client_env.py        # Simulated client responses (seeded RNG)
│   │
│   └── mcp_server/              # Model Context Protocol server
│
├── dashboard/                   # Next.js 16 frontend
│   └── src/
│       ├── app/                 # App Router pages
│       │   ├── page.tsx         # Command Center (home)
│       │   ├── invoices/        # Invoice list & detail
│       │   ├── clients/         # Client profiles
│       │   ├── compliance/      # Compliance audit trail
│       │   ├── events/          # Event log
│       │   ├── graph/           # Live LangGraph visualisation
│       │   └── approvals/       # Human approval queue
│       ├── components/          # Reusable UI components
│       ├── hooks/               # Custom React hooks (useApi, etc.)
│       └── lib/                 # Constants, utilities
│
├── alembic/                     # Database migrations
├── tests/                       # Pytest test suite
├── MD files/                    # Planning docs & audit reports
├── docker-compose.yml           # Full-stack orchestration
├── Dockerfile                   # API container (Python 3.11-slim)
├── render.yaml                  # Render.com deployment blueprint
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment variable template
```

## ⚙️ Configuration

All configuration is via environment variables (see [`.env.example`](.env.example)):

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `auto` | `auto`, `anthropic`, or `google` |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `GOOGLE_API_KEY` | — | Google AI API key |
| `TICK_CONCURRENCY` | `3` | Parallel invoices per tick (raise on paid key) |
| `DEMO_FAST` | `true` | Only hero clients use the LLM (saves API credits) |
| `RAZORPAY_KEY_ID` | — | Razorpay key ID (test or live) |
| `RAZORPAY_KEY_SECRET` | — | Razorpay key secret |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `DEMO_TOKEN` | — | Token to protect `/reset` endpoint |

## 🧪 Testing

```bash
# Run the test suite
pytest

# With coverage
pytest --cov=src --cov-report=term-missing
```

> **Tip:** Test with 5 invoices and 5 ticks. Never run the full 30-day simulation to verify a change — it takes hours and costs real API credits.

## 🚢 Deployment

### Render (One-Click)

The included [`render.yaml`](render.yaml) blueprint provisions:
- **revenueguard-api** — Dockerized FastAPI service
- **revenueguard-dashboard** — Node.js Next.js service
- **revenueguard-db** — PostgreSQL (free tier)
- **revenueguard-redis** — Redis (free tier)

After deploy, set `NEXT_PUBLIC_API_URL` to the API service's public URL in the Render dashboard.

### Docker Compose (Self-Hosted)

```bash
docker compose up --build -d
```

### Schema Changes

Schema changes are **not** migrated automatically. `create_all` creates missing tables but never adds missing columns. After any model change, rebuild the database:

```bash
docker compose down -v && docker compose up --build
```

## 🔑 Key Design Decisions

1. **`core_loop.py` owns all database writes.** Graph nodes are pure — they mutate `RecoveryState` and append to `state["audit_entries"]`. Nodes never touch the database directly.

2. **Two clocks.** Wall-clock time and `simulation_state["virtual_date"]` are different things. Audit timestamps, cooldowns, and escalation timing all run on the *virtual* clock.

3. **Audited tool layer.** Every side effect (payment links, emails, Slack notifications) flows through `src/tools/registry.py`, which records the call to the audit trail before executing it.

4. **Five stopping rules** are enforced at the graph level, not inside the LLM prompt. The model cannot escalate past them.

5. **Reproducible simulation.** Same seed + same portfolio = same run. The simulated client environment uses seeded RNG so A/B comparisons are apples-to-apples.

## 📄 License

This project was built for the Razorpay AI Buildathon. See the repository for license details.
