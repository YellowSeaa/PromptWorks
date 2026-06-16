"""merge model cost and optimization heads

Revision ID: 20260615_merge_cost_heads
Revises: 20260612_opt_target_ver, 20260615_model_costs
Create Date: 2026-06-15 16:45:00.000000
"""

from typing import Sequence, Union


revision: str = "20260615_merge_cost_heads"
down_revision: Union[str, tuple[str, ...], None] = (
    "20260612_opt_target_ver",
    "20260615_model_costs",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
