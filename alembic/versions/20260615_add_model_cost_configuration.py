"""add model cost configuration

Revision ID: 20260615_model_costs
Revises: 2d8d3a4e0c8b
Create Date: 2026-06-15 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.types import JSONBCompat


revision: str = "20260615_model_costs"
down_revision: Union[str, None] = "2d8d3a4e0c8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_models",
        sa.Column(
            "cost_currency",
            sa.String(length=12),
            nullable=False,
            server_default="USD",
        ),
    )
    op.add_column(
        "llm_models",
        sa.Column(
            "cost_display_currency",
            sa.String(length=12),
            nullable=False,
            server_default="CNY",
        ),
    )
    op.add_column(
        "llm_models",
        sa.Column(
            "cost_exchange_rate",
            sa.Float(),
            nullable=False,
            server_default="7.2",
        ),
    )
    op.add_column(
        "llm_models",
        sa.Column(
            "cost_pricing_unit",
            sa.Integer(),
            nullable=False,
            server_default="1000000",
        ),
    )
    op.add_column(
        "llm_models", sa.Column("cost_input_per_unit", sa.Float(), nullable=True)
    )
    op.add_column(
        "llm_models", sa.Column("cost_output_per_unit", sa.Float(), nullable=True)
    )
    op.add_column("llm_models", sa.Column("cost_tiers", JSONBCompat(), nullable=True))

    op.add_column("llm_usage_logs", sa.Column("input_cost", sa.Float(), nullable=True))
    op.add_column("llm_usage_logs", sa.Column("output_cost", sa.Float(), nullable=True))
    op.add_column("llm_usage_logs", sa.Column("total_cost", sa.Float(), nullable=True))
    op.add_column(
        "llm_usage_logs",
        sa.Column("cost_currency", sa.String(length=12), nullable=True),
    )
    op.add_column(
        "llm_usage_logs",
        sa.Column("cost_pricing_snapshot", JSONBCompat(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("llm_usage_logs", "cost_pricing_snapshot")
    op.drop_column("llm_usage_logs", "cost_currency")
    op.drop_column("llm_usage_logs", "total_cost")
    op.drop_column("llm_usage_logs", "output_cost")
    op.drop_column("llm_usage_logs", "input_cost")
    op.drop_column("llm_models", "cost_tiers")
    op.drop_column("llm_models", "cost_output_per_unit")
    op.drop_column("llm_models", "cost_input_per_unit")
    op.drop_column("llm_models", "cost_pricing_unit")
    op.drop_column("llm_models", "cost_exchange_rate")
    op.drop_column("llm_models", "cost_display_currency")
    op.drop_column("llm_models", "cost_currency")
