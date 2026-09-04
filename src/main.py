from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.config import settings
from src.persistence.database import init_db, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas import SimulationBatchRequest
from src.persistence.crud import generate_fake_invoices
from src.engine.core_loop import process_simulation_tick
from src.dashboard_api import router as dashboard_router
from src.websocket import manager
from datetime import datetime, timedelta
from src.rag.seed_data import seed_database
from pydantic import BaseModel
from src.persistence.models import Invoice
from sqlalchemy.future import select
from src.graph.builder import compiled_graph

# Global state for simulation virtual date
simulation_state = {
    "virtual_date": datetime.utcnow()
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Initialize ChromaDB and seed RAG context on startup
    seed_database()
    yield

app = FastAPI(
    title="RevenueGuard API v2 B2B",
    description="Scalable API for AI Revenue Recovery",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "v2_b2b"}

@app.post("/api/invoices/simulate_batch")
async def create_simulation_batch(request: SimulationBatchRequest, db: AsyncSession = Depends(get_db)):
    """Generates fake overdue invoices in the database."""
    count = await generate_fake_invoices(db, request.count)
    await manager.broadcast({"event": "state_updated"})
    return {"status": "success", "message": f"Generated {count} invoices."}

@app.post("/api/simulation/tick")
async def advance_simulation_tick(db: AsyncSession = Depends(get_db)):
    """Advances the virtual simulation date by 1 day and processes the core loop."""
    simulation_state["virtual_date"] += timedelta(days=1)
    processed_count = await process_simulation_tick(db, simulation_state["virtual_date"])
    
    await manager.broadcast({"event": "state_updated", "virtual_date": simulation_state["virtual_date"].isoformat()})
    
    return {
        "status": "success", 
        "virtual_date": simulation_state["virtual_date"].isoformat(),
        "invoices_processed": processed_count
    }

class ClientReplyRequest(BaseModel):
    message: str

@app.post("/api/invoices/{id}/reply")
async def client_reply(id: int, request: ClientReplyRequest, db: AsyncSession = Depends(get_db)):
    """Simulates a client email reply for interactive demo."""
    # Fetch invoice, build state, pass through classify_reply node
    result = await db.execute(select(Invoice).where(Invoice.id == id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        return {"error": "Invoice not found"}
        
    state = {
        "invoice_id": invoice.id,
        "client_name": invoice.client_name,
        "client_email": invoice.client_email,
        "amount": invoice.amount,
        "current_status": invoice.status.value,
        "client_reply": request.message,
        "audit_entries": [],
        "should_send_email": False
    }
    
    # We invoke the graph with the mock reply
    # In a real scenario, we'd start at the classify_reply node
    final_state = await compiled_graph.ainvoke(state)
    
    await manager.broadcast({"event": "state_updated"})
    return {"status": "success", "classified_intent": final_state.get("classified_intent")}

@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    """Receives simulated Razorpay webhook events (invoice.paid, payment.dispute.created, etc.)"""
    event = payload.get("event")
    print(f"Received Webhook: {event}")
    
    # Normally this would route through execute_action or transition states
    await manager.broadcast({"event": "state_updated"})
    return {"status": "received"}
