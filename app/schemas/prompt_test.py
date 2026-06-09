from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.prompt_test import (
    PromptTestOptimizationRecommendationStatus,
    PromptTestExperimentStatus,
    PromptTestOutputScoreStatus,
    PromptTestTaskStatus,
)


class PromptTestTaskBase(BaseModel):
    """测试任务基础字段定义。"""

    __test__ = False

    name: str = Field(..., max_length=120)
    description: str | None = None
    prompt_version_id: int | None = None
    owner_id: int | None = None
    config: dict[str, Any] | None = None


class PromptTestTaskCreate(PromptTestTaskBase):
    """创建测试任务时使用的结构，可附带预置的测试单元。"""

    __test__ = False

    units: list["PromptTestUnitCreate"] | None = None
    auto_execute: bool = False


class PromptTestTaskUpdate(BaseModel):
    """更新测试任务时可修改的字段。"""

    __test__ = False

    name: str | None = Field(default=None, max_length=120)
    description: str | None = None
    config: dict[str, Any] | None = None
    status: PromptTestTaskStatus | None = None


class PromptTestTaskRead(PromptTestTaskBase):
    """返回给前端的测试任务结构。"""

    __test__ = False

    id: int
    status: PromptTestTaskStatus
    created_at: datetime
    updated_at: datetime
    units: list["PromptTestUnitRead"] | None = None

    model_config = ConfigDict(from_attributes=True)


class PromptTestUnitBase(BaseModel):
    """最小测试单元基础字段。"""

    __test__ = False

    name: str = Field(..., max_length=120)
    description: str | None = None
    model_name: str = Field(..., max_length=100)
    llm_provider_id: int | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    rounds: int = Field(default=1, ge=1, le=100)
    prompt_template: str | None = None
    variables: dict[str, Any] | list[Any] | None = None
    parameters: dict[str, Any] | None = None
    expectations: dict[str, Any] | None = None
    tags: list[str] | None = None
    extra: dict[str, Any] | None = None


class PromptTestUnitCreate(PromptTestUnitBase):
    """创建测试单元需要提供所属测试任务 ID。"""

    __test__ = False

    task_id: int | None = Field(default=None, ge=1)
    prompt_version_id: int | None = None


class PromptTestUnitUpdate(BaseModel):
    """更新测试单元时允许修改的字段。"""

    __test__ = False

    description: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    rounds: int | None = Field(default=None, ge=1, le=100)
    prompt_template: str | None = None
    variables: dict[str, Any] | list[Any] | None = None
    parameters: dict[str, Any] | None = None
    expectations: dict[str, Any] | None = None
    tags: list[str] | None = None
    extra: dict[str, Any] | None = None


class PromptTestUnitRead(PromptTestUnitBase):
    """返回给前端的最小测试单元结构。"""

    __test__ = False

    id: int
    task_id: int
    prompt_version_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptTestExperimentBase(BaseModel):
    """新建实验需要提供的基础字段。"""

    __test__ = False

    unit_id: int | None = Field(default=None, ge=1)
    batch_id: str | None = Field(default=None, max_length=64)
    sequence: int | None = Field(default=None, ge=1, le=1000)


class PromptTestExperimentCreate(PromptTestExperimentBase):
    """创建实验的结构体，可选自动执行。"""

    __test__ = False

    auto_execute: bool = False


class PromptTestExperimentRead(BaseModel):
    """返回给前端的实验结果结构。"""

    __test__ = False

    id: int
    unit_id: int
    batch_id: str | None = None
    sequence: int
    status: PromptTestExperimentStatus
    outputs: list[dict[str, Any]] | None = None
    metrics: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptTestAIScoringRequest(BaseModel):
    """开启或重新执行 AI 评分的请求结构。"""

    __test__ = False

    enabled: bool = True
    evaluator_provider_id: int = Field(..., ge=1)
    evaluator_model_id: int = Field(..., ge=1)
    evaluator_model_name: str = Field(..., min_length=1, max_length=150)
    language: str = Field(default="zh-CN", max_length=20)
    force: bool = False


class PromptTestOutputScoreRead(BaseModel):
    """单条测试输出的评分结果。"""

    __test__ = False

    id: int
    task_id: int
    unit_id: int
    experiment_id: int
    run_index: int
    status: PromptTestOutputScoreStatus
    evaluator_provider_id: int | None = None
    evaluator_model_id: int | None = None
    evaluator_model_name: str | None = None
    language: str
    overall_score: float | None = None
    dimension_scores: dict[str, Any] | None = None
    reason: str | None = None
    retry_count: int
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptTestAIScoreSummaryRead(BaseModel):
    """测试任务评分汇总。"""

    __test__ = False

    status: dict[str, Any]
    scores: list[PromptTestOutputScoreRead]
    unit_summaries: dict[str, Any]


class PromptTestOptimizationRecommendationRequest(BaseModel):
    """生成优化建议的请求结构。"""

    __test__ = False

    evaluator_provider_id: int = Field(..., ge=1)
    evaluator_model_id: int = Field(..., ge=1)
    evaluator_model_name: str = Field(..., min_length=1, max_length=150)
    language: str = Field(default="zh-CN", max_length=20)


class PromptTestOptimizationRecommendationRead(BaseModel):
    """测试任务优化建议结果。"""

    __test__ = False

    id: int
    task_id: int
    status: PromptTestOptimizationRecommendationStatus
    evaluator_provider_id: int | None = None
    evaluator_model_id: int | None = None
    evaluator_model_name: str | None = None
    language: str
    content: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


PromptTestTaskRead.model_rebuild()
PromptTestUnitRead.model_rebuild()
PromptTestExperimentRead.model_rebuild()

__all__ = [
    "PromptTestTaskCreate",
    "PromptTestTaskUpdate",
    "PromptTestTaskRead",
    "PromptTestUnitCreate",
    "PromptTestUnitUpdate",
    "PromptTestUnitRead",
    "PromptTestExperimentCreate",
    "PromptTestExperimentRead",
    "PromptTestAIScoringRequest",
    "PromptTestOutputScoreRead",
    "PromptTestAIScoreSummaryRead",
    "PromptTestOptimizationRecommendationRequest",
    "PromptTestOptimizationRecommendationRead",
]
