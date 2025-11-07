from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.result import Result
from app.models.test_run import TestRun
from app.models.prompt_test import PromptTestTask, PromptTestUnit
from app.schemas.analysis_module import (
    AnalysisContext,
    AnalysisResult,
    AnalysisResultPayload,
    AnalysisTargetType,
    ModuleExecutionRequest,
)
from app.services.analysis_registry import (
    AnalysisExecutionService,
    AnalysisModuleRegistry,
    ParameterValidationError,
    RequirementValidationError,
    UnknownModuleError,
    get_analysis_execution_service,
    get_analysis_registry,
)


class AnalysisTaskNotFoundError(Exception):
    """指定的测试任务不存在。"""

    __test__ = False


class AnalysisDataLoadError(Exception):
    """无法加载执行分析所需的数据。"""

    __test__ = False


@dataclass(slots=True)
class AnalysisExecutionDependencies:
    """组合执行分析所需的依赖。"""

    registry: AnalysisModuleRegistry
    execution_service: AnalysisExecutionService


def _parse_task_id(raw_task_id: str) -> int:
    try:
        return int(raw_task_id)
    except (TypeError, ValueError) as exc:  # pragma: no cover - 防御性
        raise AnalysisDataLoadError("任务标识无效，无法解析为整数。") from exc


def _load_test_run(db: Session, task_id: int) -> TestRun:
    test_run = db.get(TestRun, task_id)
    if test_run is None:
        raise AnalysisTaskNotFoundError(f"测试任务 {task_id} 不存在。")
    return test_run


def _load_prompt_test_task(db: Session, task_id: int) -> PromptTestTask:
    stmt = (
        select(PromptTestTask)
        .where(PromptTestTask.id == task_id, PromptTestTask.is_deleted.is_(False))
        .options(
            selectinload(PromptTestTask.units).selectinload(PromptTestUnit.experiments)
        )
    )
    task = db.execute(stmt).scalar_one_or_none()
    if task is None:
        raise AnalysisTaskNotFoundError(f"测试任务 {task_id} 不存在。")
    return task


def _load_results_dataframe(db: Session, task_id: int) -> pd.DataFrame:
    stmt = (
        select(
            Result.id.label("result_id"),
            Result.test_run_id,
            Result.run_index,
            Result.latency_ms,
            Result.tokens_used,
            Result.created_at,
        )
        .where(Result.test_run_id == task_id)
        .order_by(Result.run_index.asc(), Result.id.asc())
    )
    rows = db.execute(stmt).mappings().all()

    columns = [
        "result_id",
        "test_run_id",
        "run_index",
        "latency_ms",
        "tokens_used",
        "created_at",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    records = [{column: row.get(column) for column in columns} for row in rows]
    return pd.DataFrame.from_records(records, columns=columns)


def _sanitize_records(data_frame: pd.DataFrame) -> list[dict[str, Any]]:
    if data_frame.empty:
        return []
    sanitized_df = data_frame.copy()
    sanitized_df = sanitized_df.convert_dtypes()
    sanitized_df = sanitized_df.where(pd.notna(sanitized_df), None)
    return cast(list[dict[str, Any]], sanitized_df.to_dict(orient="records"))


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            numeric = float(text)
        except ValueError:
            return None
        if numeric != numeric or numeric in (float("inf"), float("-inf")):
            return None
        return int(numeric)
    return None


def _build_prompt_test_dataframe(task: PromptTestTask) -> pd.DataFrame:
    columns = [
        "task_id",
        "unit_id",
        "unit_name",
        "experiment_id",
        "run_index",
        "latency_ms",
        "tokens_used",
    ]

    rows: list[dict[str, Any]] = []
    for unit in task.units:
        experiments = getattr(unit, "experiments", []) or []
        for experiment in experiments:
            outputs = experiment.outputs if isinstance(experiment.outputs, list) else []
            for index, output in enumerate(outputs, start=1):
                if not isinstance(output, dict):
                    continue
                status_value = str(output.get("status", "")).strip().lower()
                if status_value in {"failed", "error"}:
                    # 过滤掉执行失败的输出，避免纳入耗时与 tokens 统计
                    continue
                run_index = output.get("run_index") or output.get("sequence") or index
                latency = output.get("latency_ms")
                total_tokens = output.get("total_tokens") or (
                    (output.get("prompt_tokens") or 0)
                    + (output.get("completion_tokens") or 0)
                )
                rows.append(
                    {
                        "task_id": task.id,
                        "unit_id": unit.id,
                        "unit_name": unit.name,
                        "experiment_id": experiment.id,
                        "run_index": _safe_int(run_index) or index,
                        "latency_ms": _safe_int(latency),
                        "tokens_used": _safe_int(total_tokens),
                    }
                )

    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows, columns=columns)


def serialize_analysis_result(
    module_id: str, result: AnalysisResult
) -> AnalysisResultPayload:
    records = _sanitize_records(result.data_frame)
    return AnalysisResultPayload(
        module_id=module_id,
        data=records,
        columns_meta=result.columns_meta,
        insights=result.insights,
        llm_usage=result.llm_usage,
        protocol_version=result.protocol_version,
        extra=result.extra,
    )


def get_execution_dependencies() -> AnalysisExecutionDependencies:
    return AnalysisExecutionDependencies(
        registry=get_analysis_registry(),
        execution_service=get_analysis_execution_service(),
    )


def execute_module_for_test_run(
    db: Session,
    request: ModuleExecutionRequest,
    *,
    user_id: int | None = None,
    dependencies: AnalysisExecutionDependencies | None = None,
) -> AnalysisResult:
    deps = dependencies or get_execution_dependencies()
    task_id = _parse_task_id(request.task_id)
    test_run = _load_test_run(db, task_id)
    data_frame = _load_results_dataframe(db, task_id)

    context = AnalysisContext(
        task_id=str(task_id),
        user_id=user_id,
        llm_client=None,
        metadata={
            "test_run_id": task_id,
            "module_id": request.module_id,
            "row_count": int(len(data_frame)),
            "status": test_run.status.value if test_run.status else None,
        },
    )
    return deps.execution_service.execute_now(data_frame, context, request)


def execute_module_for_prompt_test_task(
    db: Session,
    request: ModuleExecutionRequest,
    *,
    user_id: int | None = None,
    dependencies: AnalysisExecutionDependencies | None = None,
) -> AnalysisResult:
    deps = dependencies or get_execution_dependencies()
    task_id = _parse_task_id(request.task_id)
    task = _load_prompt_test_task(db, task_id)
    data_frame = _build_prompt_test_dataframe(task)

    context = AnalysisContext(
        task_id=str(task_id),
        user_id=user_id,
        llm_client=None,
        metadata={
            "prompt_test_task_id": task_id,
            "task_name": task.name,
            "module_id": request.module_id,
            "row_count": int(len(data_frame)),
            "status": task.status.value if task.status else None,
        },
    )
    return deps.execution_service.execute_now(data_frame, context, request)


__all__ = [
    "AnalysisTaskNotFoundError",
    "AnalysisDataLoadError",
    "serialize_analysis_result",
    "execute_module_for_test_run",
    "execute_module_for_prompt_test_task",
    "get_execution_dependencies",
    "UnknownModuleError",
    "ParameterValidationError",
    "RequirementValidationError",
]
