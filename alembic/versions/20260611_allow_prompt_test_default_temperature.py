"""allow prompt test units to use provider default temperature

Revision ID: 20260611_temp_default
Revises: 20260609_ai_scoring
Create Date: 2026-06-11 15:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260611_temp_default"
down_revision: Union[str, None] = "20260609_ai_scoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "prompt_test_units",
        "temperature",
        existing_type=sa.Float(),
        nullable=True,
        server_default=None,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE prompt_test_units SET temperature = 0.7 WHERE temperature IS NULL"
        )
    )
    op.alter_column(
        "prompt_test_units",
        "temperature",
        existing_type=sa.Float(),
        nullable=False,
        server_default="0.7",
    )
