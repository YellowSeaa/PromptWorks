"""add embedding model configuration

Revision ID: 20260617_embedding_cfg
Revises: 20260615_merge_cost_heads
Create Date: 2026-06-17 22:55:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260617_embedding_cfg"
down_revision: Union[str, None] = "20260615_merge_cost_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_models",
        sa.Column(
            "model_type",
            sa.String(length=20),
            nullable=False,
            server_default="chat",
        ),
    )
    op.add_column(
        "llm_models",
        sa.Column("embedding_api_style", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "llm_models", sa.Column("embedding_dimensions", sa.Integer(), nullable=True)
    )
    op.add_column(
        "llm_models", sa.Column("embedding_batch_size", sa.Integer(), nullable=True)
    )
    op.add_column(
        "llm_models",
        sa.Column("embedding_max_input_tokens", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("llm_models", "embedding_max_input_tokens")
    op.drop_column("llm_models", "embedding_batch_size")
    op.drop_column("llm_models", "embedding_dimensions")
    op.drop_column("llm_models", "embedding_api_style")
    op.drop_column("llm_models", "model_type")
