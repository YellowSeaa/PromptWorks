"""add prompt version scope to optimization recommendations

Revision ID: 20260612_opt_target_ver
Revises: 20260611_temp_default
Create Date: 2026-06-12 15:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260612_opt_target_ver"
down_revision: Union[str, None] = "20260611_temp_default"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "prompt_test_optimization_recommendations",
        sa.Column("prompt_version_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_prompt_test_optimization_recommendations_prompt_version_id",
        "prompt_test_optimization_recommendations",
        ["prompt_version_id"],
    )
    op.create_foreign_key(
        "fk_prompt_test_optimization_recommendations_prompt_version_id",
        "prompt_test_optimization_recommendations",
        "prompts_versions",
        ["prompt_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_prompt_test_optimization_recommendations_prompt_version_id",
        "prompt_test_optimization_recommendations",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_prompt_test_optimization_recommendations_prompt_version_id",
        table_name="prompt_test_optimization_recommendations",
    )
    op.drop_column("prompt_test_optimization_recommendations", "prompt_version_id")
