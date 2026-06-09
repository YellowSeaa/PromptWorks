"""add context length to llm models

Revision ID: b4c8f2d1a9e0
Revises: 6d6a1f6dfb41
Create Date: 2026-06-09 10:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c8f2d1a9e0"
down_revision: Union[str, None] = "6d6a1f6dfb41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_models", sa.Column("context_length", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("llm_models", "context_length")
