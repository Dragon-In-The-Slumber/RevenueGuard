# Execution Context & IDE Handoff

**To the Antigravity IDE Assistant:**
Hello! We have been planning this project in the chat interface and are now handing off execution to you in the IDE. Please read this document carefully to understand the current state and immediate next steps.

## 1. Project Background (MUST READ)
We are building **RevenueGuard (v2_b2b)** for the Razorpay AI Buildathon. It is an autonomous AI agent for B2B Receivables recovery with a Promise-to-Pay tracker.
👉 **CRITICAL:** Before writing any business logic, you MUST read the `project_core_context.md` file located in the `.gemini/antigravity/brain/44ca47e4-6098-4598-b6ea-caf110cc4993/` directory. That document contains the state machine, "The Bar" requirements, and agent architecture.

## 2. Current Workspace State
- `v1/`: Contains the user's previous "brute force" attempt. It is over-engineered (LangGraph, Celery, 6 agents). **Do not use the business logic from v1.**
- `v2_b2b/`: The clean slate directory where we are building the new, focused B2B agent.

## 3. Immediate Next Steps (Your Tasks)

### Phase 1: Infrastructure Migration
Your first task is to scaffold `v2_b2b` by copying the *reusable* infrastructure from `v1`, while stripping out the bloat.

1. **Docker & Env:** Copy `docker-compose.yml`, `Dockerfile`, and `.env.example` from `v1/` to `v2_b2b/`.
   - *Modification:* Edit `docker-compose.yml` to remove the `rabbitmq` and `worker` (Celery) services. We only want `api`, `db` (Postgres), and `redis` (if needed for simple caching).
2. **Backend Scaffold:** Copy `requirements.txt` (or `pyproject.toml`) and the basic `src/main.py`, `src/config.py` from `v1` to `v2_b2b/src/`.
   - *Modification:* Remove `langgraph`, `celery`, and `rabbitmq` dependencies. Keep `fastapi`, `sqlalchemy`, `asyncpg`, `pydantic`, `openai`.
3. **Frontend Scaffold:** Copy the entire `v1/dashboard/` folder to `v2_b2b/dashboard/`. We will keep the Next.js/Tailwind setup but rewrite the pages later.

### Phase 2: Database Modeling
Once the scaffold is running, create the new SQLAlchemy models in `v2_b2b/src/persistence/models.py`. We need:
1. `Invoice`: (id, amount, client_name, client_email, due_date, status [ISSUED, OVERDUE, NOTIFIED_1, PAUSED_PTP, RECOVERED, etc.], promised_date).
2. `AuditLog`: (id, invoice_id, timestamp, event_type, agent_reasoning, action_taken).

### Phase 3: The API & Simulation Engine
1. Build a FastAPI endpoint `POST /api/invoices/simulate_batch` that generates 100 fake invoices in the DB.
2. Build the core loop that scans for `OVERDUE` invoices and triggers the LLM (using the prompts from `project_core_context.md`).

**Please start with Phase 1 and confirm once the basic dockerized FastAPI app is running in the `v2_b2b` folder!**
