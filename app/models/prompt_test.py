from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as PgEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.types import JSONBCompat
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.prompt import PromptVersion


class PromptTestTaskStatus(str, Enum):
    """测试任务的状态枚举。"""

    __test__ = False
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PromptTestTask(Base):
    """测试任务表，描述一次测试活动的整体配置。"""

    __tablename__ = "prompt_test_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompts_versions.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    status: Mapped[PromptTestTaskStatus] = mapped_column(
        PgEnum(
            PromptTestTaskStatus,
            name="prompt_test_task_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=PromptTestTaskStatus.DRAFT,
        server_default=PromptTestTaskStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    prompt_version: Mapped["PromptVersion | None"] = relationship("PromptVersion")
    units: Mapped[list["PromptTestUnit"]] = relationship(
        "PromptTestUnit",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PromptTestUnit(Base):
    """最小测试单元，描述执行一次模型调用所需的上下文。"""

    __tablename__ = "prompt_test_units"
    __table_args__ = (
        UniqueConstraint("task_id", "name", name="uq_prompt_test_unit_task_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_test_tasks.id", ondelete="CASCADE"), nullable=False
    )
    prompt_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompts_versions.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    llm_provider_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature: Mapped[float | None] = mapped_column(nullable=True)
    top_p: Mapped[float | None] = mapped_column(nullable=True)
    rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    expectations: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONBCompat, nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    task: Mapped["PromptTestTask"] = relationship(
        "PromptTestTask", back_populates="units"
    )
    prompt_version: Mapped["PromptVersion | None"] = relationship("PromptVersion")
    experiments: Mapped[list["PromptTestExperiment"]] = relationship(
        "PromptTestExperiment",
        back_populates="unit",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PromptTestExperimentStatus(str, Enum):
    """记录实验执行状态，支持多轮执行与失败重试。"""

    __test__ = False
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PromptTestExperiment(Base):
    """实验执行结果，与最小测试单元关联。"""

    __tablename__ = "prompt_test_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_test_units.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[PromptTestExperimentStatus] = mapped_column(
        PgEnum(
            PromptTestExperimentStatus,
            name="prompt_test_experiment_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=PromptTestExperimentStatus.PENDING,
        server_default=PromptTestExperimentStatus.PENDING.value,
    )
    outputs: Mapped[list[dict] | None] = mapped_column(
        JSONBCompat, nullable=True, doc="多轮执行的返回结果列表"
    )
    metrics: Mapped[dict | None] = mapped_column(
        JSONBCompat, nullable=True, doc="自动化评估指标与统计信息"
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    unit: Mapped["PromptTestUnit"] = relationship(
        "PromptTestUnit", back_populates="experiments"
    )
    output_scores: Mapped[list["PromptTestOutputScore"]] = relationship(
        "PromptTestOutputScore",
        back_populates="experiment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PromptTestOutputScoreStatus(str, Enum):
    """单条测试输出的 AI 评分状态。"""

    __test__ = False
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PromptTestOutputScore(Base):
    """单条测试输出的 AI 评分记录。"""

    __tablename__ = "prompt_test_output_scores"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "run_index",
            name="uq_prompt_test_output_score_experiment_run",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_test_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_test_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_test_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PromptTestOutputScoreStatus] = mapped_column(
        PgEnum(
            PromptTestOutputScoreStatus,
            name="prompt_test_output_score_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=PromptTestOutputScoreStatus.PENDING,
        server_default=PromptTestOutputScoreStatus.PENDING.value,
    )
    evaluator_provider_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluator_model_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluator_model_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    language: Mapped[str] = mapped_column(
        String(20), nullable=False, default="zh-CN", server_default="zh-CN"
    )
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dimension_scores: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    task: Mapped["PromptTestTask"] = relationship("PromptTestTask")
    unit: Mapped["PromptTestUnit"] = relationship("PromptTestUnit")
    experiment: Mapped["PromptTestExperiment"] = relationship(
        "PromptTestExperiment", back_populates="output_scores"
    )


class PromptTestOptimizationRecommendationStatus(str, Enum):
    """测试任务优化建议生成状态。"""

    __test__ = False
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PromptTestOptimizationRecommendation(Base):
    """基于评分生成的测试任务优化建议。"""

    __tablename__ = "prompt_test_optimization_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_test_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompts_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[PromptTestOptimizationRecommendationStatus] = mapped_column(
        PgEnum(
            PromptTestOptimizationRecommendationStatus,
            name="prompt_test_optimization_recommendation_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=PromptTestOptimizationRecommendationStatus.RUNNING,
        server_default=PromptTestOptimizationRecommendationStatus.RUNNING.value,
    )
    evaluator_provider_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluator_model_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluator_model_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    language: Mapped[str] = mapped_column(
        String(20), nullable=False, default="zh-CN", server_default="zh-CN"
    )
    content: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    task: Mapped["PromptTestTask"] = relationship("PromptTestTask")


__all__ = [
    "PromptTestTask",
    "PromptTestTaskStatus",
    "PromptTestUnit",
    "PromptTestExperiment",
    "PromptTestExperimentStatus",
    "PromptTestOutputScore",
    "PromptTestOutputScoreStatus",
    "PromptTestOptimizationRecommendation",
    "PromptTestOptimizationRecommendationStatus",
]
