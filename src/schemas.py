from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from src.persistence.models import InvoiceStatus

class SimulationBatchRequest(BaseModel):
    count: int = 100

class InvoiceResponse(BaseModel):
    id: int
    amount: float
    client_name: str
    client_email: str
    due_date: datetime
    status: InvoiceStatus
    promised_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(BaseModel):
    id: int
    invoice_id: int
    timestamp: datetime
    event_type: str
    agent_reasoning: Optional[str] = None
    action_taken: str

    model_config = ConfigDict(from_attributes=True)
