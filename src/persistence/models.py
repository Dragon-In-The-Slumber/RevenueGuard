from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()

class InvoiceStatus(str, enum.Enum):
    ISSUED = "ISSUED"
    OVERDUE = "OVERDUE"
    NOTIFIED_1 = "NOTIFIED_1"
    NOTIFIED_2 = "NOTIFIED_2"
    NOTIFIED_3 = "NOTIFIED_3"
    PAUSED_PTP = "PAUSED_PTP"
    DISPUTE = "DISPUTE"
    LEGAL_HOLD = "LEGAL_HOLD"
    UNRESPONSIVE = "UNRESPONSIVE"
    RECOVERED = "RECOVERED"
    HUMAN_ESCALATED = "HUMAN_ESCALATED"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    client_name = Column(String, nullable=False)
    client_email = Column(String, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.ISSUED, nullable=False)
    promised_date = Column(DateTime, nullable=True)
    escalation_stage = Column(String(20), default="STAGE_1")
    # Outbound contact attempts. Stopping rule 5 caps this and routes to UNRESPONSIVE.
    contact_attempts = Column(Integer, default=0, nullable=False, server_default="0")
    # 1.0 = intact. Over-escalation reduces it, which costs recovery in the
    # simulated environment — this is what makes agent restraint measurable.
    relationship_score = Column(Float, default=1.0, nullable=False, server_default="1.0")
    # id and URL are separate: conflating them rendered the link as a path segment,
    # producing https://rzp.io/l/https://rzp.io/l/42_...
    razorpay_payment_link_id = Column(String(80), nullable=True)
    razorpay_payment_link_url = Column(String(255), nullable=True)
    razorpay_virtual_account_id = Column(String(80), nullable=True)

    # Relationship to AuditLog
    audit_logs = relationship("AuditLog", back_populates="invoice")


class WebhookEvent(Base):
    """
    Delivered webhook ids, for idempotency.

    Razorpay retries deliveries; without this a retried invoice.paid would write a
    duplicate PAYMENT_RECEIVED row every time.
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(120), nullable=False, unique=True, index=True)
    event_type = Column(String(80), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String, nullable=False)
    agent_reasoning = Column(String, nullable=True)
    rule_applied = Column(String, nullable=True)
    action_taken = Column(String, nullable=False)
    content_snapshot = Column(String, nullable=True)
    compliance_verdict = Column(String(12), nullable=True)
    # Who produced the verdict: "llm", "deterministic" (DEMO_FAST scaffolding) or
    # "unavailable". Without this the Compliance page cannot tell a real review
    # from demo scaffolding, and would present the latter as agent performance.
    verdict_source = Column(String(20), nullable=True)
    
    # Relationship to Invoice
    invoice = relationship("Invoice", back_populates="audit_logs")
