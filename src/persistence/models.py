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
    razorpay_payment_link_id = Column(String(50), nullable=True)
    razorpay_virtual_account_id = Column(String(50), nullable=True)
    
    # Relationship to AuditLog
    audit_logs = relationship("AuditLog", back_populates="invoice")

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
    compliance_verdict = Column(String(10), nullable=True)
    
    # Relationship to Invoice
    invoice = relationship("Invoice", back_populates="audit_logs")
