"""Split payment link id/url and add webhook idempotency

Revision ID: 0003_razorpay
Revises: 0002_relationship
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_razorpay"
down_revision: Union[str, None] = "0002_relationship"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widen: real Razorpay ids (plink_XXXXXXXXXXXXXXXX) exceed the old 50 chars.
    op.alter_column("invoices", "razorpay_payment_link_id",
                    existing_type=sa.String(length=50), type_=sa.String(length=80))
    op.alter_column("invoices", "razorpay_virtual_account_id",
                    existing_type=sa.String(length=50), type_=sa.String(length=80))
    op.add_column("invoices", sa.Column("razorpay_payment_link_url", sa.String(length=255), nullable=True))

    # Existing rows stored the full URL in the id column. Move it to the url column
    # and clear the id, rather than leaving a URL masquerading as an identifier.
    op.execute("""
        UPDATE invoices
           SET razorpay_payment_link_url = razorpay_payment_link_id,
               razorpay_payment_link_id = NULL
         WHERE razorpay_payment_link_id LIKE 'http%'
    """)

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_webhook_events_id"), "webhook_events", ["id"])
    op.create_index(op.f("ix_webhook_events_event_id"), "webhook_events", ["event_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_webhook_events_event_id"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_id"), table_name="webhook_events")
    op.drop_table("webhook_events")
    op.execute("""
        UPDATE invoices
           SET razorpay_payment_link_id = razorpay_payment_link_url
         WHERE razorpay_payment_link_id IS NULL
           AND razorpay_payment_link_url IS NOT NULL
    """)
    op.drop_column("invoices", "razorpay_payment_link_url")
    op.alter_column("invoices", "razorpay_virtual_account_id",
                    existing_type=sa.String(length=80), type_=sa.String(length=50))
    op.alter_column("invoices", "razorpay_payment_link_id",
                    existing_type=sa.String(length=80), type_=sa.String(length=50))
