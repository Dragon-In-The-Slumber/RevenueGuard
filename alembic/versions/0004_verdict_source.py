"""Add verdict_source to audit_logs, widen compliance_verdict

UNREVIEWED is 10 characters, which fits, but the column is widened to 12 for
headroom. verdict_source records whether a model actually reviewed the draft or
whether the row came from DEMO_FAST scaffolding.

Revision ID: 0004_verdict_source
Revises: 0003_razorpay
Create Date: 2026-09-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_verdict_source"
down_revision: Union[str, None] = "0003_razorpay"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("audit_logs", "compliance_verdict",
                    existing_type=sa.String(length=10), type_=sa.String(length=12))
    op.add_column("audit_logs", sa.Column("verdict_source", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_logs", "verdict_source")
    op.alter_column("audit_logs", "compliance_verdict",
                    existing_type=sa.String(length=12), type_=sa.String(length=10))
