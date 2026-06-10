"""add prompt test ai scoring tables

Revision ID: 20260609_ai_scoring
Revises: b4c8f2d1a9e0
Create Date: 2026-06-09 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260609_ai_scoring"
down_revision: Union[str, None] = "b4c8f2d1a9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    score_status_enum = postgresql.ENUM(
        "pending",
        "running",
        "completed",
        "failed",
        name="prompt_test_output_score_status",
        create_type=False,
    )
    recommendation_status_enum = postgresql.ENUM(
        "running",
        "completed",
        "failed",
        name="prompt_test_optimization_recommendation_status",
        create_type=False,
    )
    score_status_enum.create(bind, checkfirst=True)
    recommendation_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "prompt_test_output_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("run_index", sa.Integer(), nullable=False),
        sa.Column(
            "status", score_status_enum, nullable=False, server_default="pending"
        ),
        sa.Column("evaluator_provider_id", sa.Integer(), nullable=True),
        sa.Column("evaluator_model_id", sa.Integer(), nullable=True),
        sa.Column("evaluator_model_name", sa.String(length=150), nullable=True),
        sa.Column(
            "language", sa.String(length=20), nullable=False, server_default="zh-CN"
        ),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("dimension_scores", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["prompt_test_tasks.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["prompt_test_units.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["prompt_test_experiments.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "experiment_id",
            "run_index",
            name="uq_prompt_test_output_score_experiment_run",
        ),
    )
    op.create_index(
        "ix_prompt_test_output_scores_task_id", "prompt_test_output_scores", ["task_id"]
    )
    op.create_index(
        "ix_prompt_test_output_scores_unit_id", "prompt_test_output_scores", ["unit_id"]
    )
    op.create_index(
        "ix_prompt_test_output_scores_experiment_id",
        "prompt_test_output_scores",
        ["experiment_id"],
    )

    op.create_table(
        "prompt_test_optimization_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            recommendation_status_enum,
            nullable=False,
            server_default="running",
        ),
        sa.Column("evaluator_provider_id", sa.Integer(), nullable=True),
        sa.Column("evaluator_model_id", sa.Integer(), nullable=True),
        sa.Column("evaluator_model_name", sa.String(length=150), nullable=True),
        sa.Column(
            "language", sa.String(length=20), nullable=False, server_default="zh-CN"
        ),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["prompt_test_tasks.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_prompt_test_optimization_recommendations_task_id",
        "prompt_test_optimization_recommendations",
        ["task_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prompt_test_optimization_recommendations_task_id",
        table_name="prompt_test_optimization_recommendations",
    )
    op.drop_table("prompt_test_optimization_recommendations")

    op.drop_index(
        "ix_prompt_test_output_scores_experiment_id",
        table_name="prompt_test_output_scores",
    )
    op.drop_index(
        "ix_prompt_test_output_scores_unit_id", table_name="prompt_test_output_scores"
    )
    op.drop_index(
        "ix_prompt_test_output_scores_task_id", table_name="prompt_test_output_scores"
    )
    op.drop_table("prompt_test_output_scores")

    bind = op.get_bind()
    sa.Enum(name="prompt_test_optimization_recommendation_status").drop(
        bind, checkfirst=True
    )
    sa.Enum(name="prompt_test_output_score_status").drop(bind, checkfirst=True)
