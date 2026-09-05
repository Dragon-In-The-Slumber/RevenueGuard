"""Add relationship_score to invoices

The agentic core penalises over-escalation. The score has to survive across ticks,
so it lives on the invoice rather than only in graph state.

Revision ID: 0002_relationship
Revises: 0001_initial
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_relationship"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("relationship_score", sa.Float(), nullable=False, server_default="1.0"),
    )


def downgrade() -> None:
    op.drop_column("invoices", "relationship_score")
