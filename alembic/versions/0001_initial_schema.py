"""Initial schema matching src/persistence/models.py

Baseline revision. `create_all` creates missing tables but never missing columns,
so a database predating any model change silently 500s every query. This revision
is the starting point that makes such changes migratable.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INVOICE_STATUS = sa.Enum(
    "ISSUED", "OVERDUE", "NOTIFIED_1", "NOTIFIED_2", "NOTIFIED_3", "PAUSED_PTP",
    "DISPUTE", "LEGAL_HOLD", "UNRESPONSIVE", "RECOVERED", "HUMAN_ESCALATED",
    name="invoicestatus",
)


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("client_name", sa.String(), nullable=False),
        sa.Column("client_email", sa.String(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=False),
        sa.Column("status", INVOICE_STATUS, nullable=False),
        sa.Column("promised_date", sa.DateTime(), nullable=True),
        sa.Column("escalation_stage", sa.String(length=20), nullable=True),
        sa.Column("contact_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("razorpay_payment_link_id", sa.String(length=50), nullable=True),
        sa.Column("razorpay_virtual_account_id", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoices_id"), "invoices", ["id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("agent_reasoning", sa.String(), nullable=True),
        sa.Column("rule_applied", sa.String(), nullable=True),
        sa.Column("action_taken", sa.String(), nullable=False),
        sa.Column("content_snapshot", sa.String(), nullable=True),
        sa.Column("compliance_verdict", sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_invoices_id"), table_name="invoices")
    op.drop_table("invoices")
    INVOICE_STATUS.drop(op.get_bind(), checkfirst=True)
