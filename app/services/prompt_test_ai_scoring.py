from __future__ import annotations

import json
import math
import statistics
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.llm_provider_registry import get_provider_defaults
from app.models.llm_provider import LLMModel, LLMProvider
from app.models.prompt_test import (
    PromptTestExperiment,
    PromptTestOptimizationRecommendation,
    PromptTestOptimizationRecommendationStatus,
    PromptTestOutputScore,
    PromptTestOutputScoreStatus,
    PromptTestTask,
    PromptTestUnit,
)
from app.services.system_settings import (
    DEFAULT_AI_OPTIMIZATION_TIMEOUT,
    DEFAULT_TEST_TASK_TIMEOUT,
    get_testing_timeout_config,
)

MAX_SCORE_RETRIES = 2
DEFAULT_SCORE_LANGUAGE = "zh-CN"
MAX_RECOMMENDATION_SCORE_ITEMS = 50
MAX_RECOMMENDATION_OUTPUT_CHARS = 800
MAX_RECOMMENDATION_JSON_CHARS = 800
MAX_RECOMMENDATION_REASON_CHARS = 300
MAX_RECOMMENDATION_SEMANTIC_GROUPS = 6


class PromptTestAIScoringError(Exception):
    """AI 评分业务异常。"""

    __test__ = False


@dataclass(frozen=True, slots=True)
class AIScoringConfig:
    """AI 评分配置。"""

    enabled: bool
    evaluator_provider_id: int
    evaluator_model_id: int
    evaluator_model_name: str
    language: str = DEFAULT_SCORE_LANGUAGE


@dataclass(frozen=True, slots=True)
class ParallelLimits:
    """测试调用与评分调用的并发分配。"""

    test_limit: int
    scoring_limit: int
    shared_single_lane: bool = False


def resolve_parallel_limits(
    *,
    test_model_id: int | None,
    evaluator_model_id: int | None,
    test_concurrency_limit: int,
    evaluator_concurrency_limit: int,
) -> ParallelLimits:
    """按模型关系计算测试与评分并发上限。"""

    test_limit = max(1, int(test_concurrency_limit or 1))
    scoring_limit = max(1, int(evaluator_concurrency_limit or 1))
    if (
        test_model_id is None
        or evaluator_model_id is None
        or test_model_id != evaluator_model_id
    ):
        return ParallelLimits(test_limit=test_limit, scoring_limit=scoring_limit)

    shared_limit = max(1, min(test_limit, scoring_limit))
    if shared_limit == 1:
        return ParallelLimits(test_limit=1, scoring_limit=1, shared_single_lane=True)
    split_for_test = max(1, shared_limit // 2)
    return ParallelLimits(
        test_limit=split_for_test,
        scoring_limit=max(1, shared_limit - split_for_test),
    )


def parse_ai_scoring_config(
    config: Mapping[str, Any] | None,
) -> AIScoringConfig | None:
    """从任务配置中解析 AI 评分设置。"""

    if not isinstance(config, Mapping):
        return None
    raw = config.get("ai_scoring")
    if not isinstance(raw, Mapping) or not raw.get("enabled"):
        return None
    provider_id = _safe_int(raw.get("evaluator_provider_id"))
    model_id = _safe_int(raw.get("evaluator_model_id"))
    model_name = _safe_str(raw.get("evaluator_model_name"))
    if provider_id is None or model_id is None or not model_name:
        return None
    language = _safe_str(raw.get("language")) or DEFAULT_SCORE_LANGUAGE
    return AIScoringConfig(
        enabled=True,
        evaluator_provider_id=provider_id,
        evaluator_model_id=model_id,
        evaluator_model_name=model_name,
        language=language,
    )


def build_ai_scoring_config_dict(config: AIScoringConfig) -> dict[str, Any]:
    """序列化 AI 评分配置。"""

    return {
        "enabled": config.enabled,
        "evaluator_provider_id": config.evaluator_provider_id,
        "evaluator_model_id": config.evaluator_model_id,
        "evaluator_model_name": config.evaluator_model_name,
        "language": config.language or DEFAULT_SCORE_LANGUAGE,
    }


def update_task_ai_scoring_status(
    task: PromptTestTask,
    *,
    scoring_config: AIScoringConfig | None = None,
    status: str | None = None,
    last_error: str | None = None,
    progress: dict[str, Any] | None = None,
) -> None:
    """更新任务配置中的 AI 评分状态。"""

    base = dict(task.config) if isinstance(task.config, dict) else {}
    raw = base.get("ai_scoring")
    ai_scoring = dict(raw) if isinstance(raw, dict) else {}
    if scoring_config is not None:
        ai_scoring.update(build_ai_scoring_config_dict(scoring_config))
    if status is not None:
        ai_scoring["status"] = status
        now = datetime.now(UTC).isoformat()
        if status == "running":
            ai_scoring["started_at"] = now
            ai_scoring.pop("finished_at", None)
        if status in {"completed", "failed"}:
            ai_scoring["finished_at"] = now
    if progress is not None:
        ai_scoring["progress"] = progress
    if last_error:
        ai_scoring["last_error"] = last_error
    else:
        ai_scoring.pop("last_error", None)
    base["ai_scoring"] = ai_scoring
    task.config = base


def score_task_outputs(
    db: Session, task_id: int, *, force: bool = False, commit_progress: bool = False
) -> dict[str, Any]:
    """对任务最新实验中的已有成功输出执行补评分。"""

    task = _load_task_with_outputs(db, task_id)
    scoring_config = parse_ai_scoring_config(task.config)
    if scoring_config is None:
        raise PromptTestAIScoringError("测试任务未配置 AI 评分模型。")

    candidates = _collect_latest_outputs(task)
    update_task_ai_scoring_status(
        task,
        scoring_config=scoring_config,
        status="running",
        progress={"current": 0, "total": len(candidates), "percentage": 0},
    )
    db.flush()
    if commit_progress:
        db.commit()

    completed = 0
    for experiment, output in candidates:
        existing = _find_existing_score(db, experiment.id, output)
        if _should_skip_existing_score(existing, force=force):
            completed += 1
            continue
        score_experiment_output(
            db,
            experiment=experiment,
            output=output,
            scoring_config=scoring_config,
            force=force,
        )
        completed += 1
        total = len(candidates)
        update_task_ai_scoring_status(
            task,
            scoring_config=scoring_config,
            status="running",
            progress={
                "current": completed,
                "total": total,
                "percentage": int(round((completed / total) * 100)) if total else 100,
            },
        )
        db.flush()
        if commit_progress:
            db.commit()

    update_task_ai_scoring_status(
        task,
        scoring_config=scoring_config,
        status="completed",
        progress={
            "current": len(candidates),
            "total": len(candidates),
            "percentage": 100,
        },
    )
    db.flush()
    if commit_progress:
        db.commit()
    return build_task_score_summary(db, task_id)


def score_experiment_output(
    db: Session,
    *,
    experiment: PromptTestExperiment,
    output: Mapping[str, Any],
    scoring_config: AIScoringConfig,
    force: bool = False,
) -> PromptTestOutputScore:
    """对单条测试输出执行 AI 评分并持久化。"""

    run_index = _resolve_run_index(output)
    existing = _find_existing_score(db, experiment.id, output)
    if existing is not None and _should_skip_existing_score(existing, force=force):
        return existing

    unit = experiment.unit
    if unit is None:
        raise PromptTestAIScoringError("实验缺少关联测试单元。")

    score = existing or PromptTestOutputScore(
        task_id=unit.task_id,
        unit_id=unit.id,
        experiment_id=experiment.id,
        run_index=run_index,
    )
    score.status = PromptTestOutputScoreStatus.RUNNING
    score.evaluator_provider_id = scoring_config.evaluator_provider_id
    score.evaluator_model_id = scoring_config.evaluator_model_id
    score.evaluator_model_name = scoring_config.evaluator_model_name
    score.language = scoring_config.language or DEFAULT_SCORE_LANGUAGE
    score.started_at = datetime.now(UTC)
    score.finished_at = None
    score.error = None
    score.retry_count = 0
    if existing is None:
        db.add(score)
    db.flush()

    last_error: Exception | None = None
    for attempt in range(MAX_SCORE_RETRIES + 1):
        score.retry_count = attempt
        try:
            payload, raw_response = _invoke_score_llm(
                db,
                unit=unit,
                output=output,
                scoring_config=scoring_config,
            )
            overall_score, dimension_scores, reason = _normalize_score_payload(payload)
            score.status = PromptTestOutputScoreStatus.COMPLETED
            score.overall_score = overall_score
            score.dimension_scores = dimension_scores
            score.reason = reason
            score.raw_response = raw_response
            score.error = None
            score.finished_at = datetime.now(UTC)
            db.flush()
            return score
        except Exception as exc:  # noqa: BLE001 - 需要记录外部模型失败原因
            last_error = exc
            if attempt < MAX_SCORE_RETRIES:
                time.sleep(0.05 * (attempt + 1))

    score.status = PromptTestOutputScoreStatus.FAILED
    score.error = str(last_error) if last_error else "AI 评分失败"
    score.finished_at = datetime.now(UTC)
    db.flush()
    return score


def ensure_pending_output_score(
    db: Session,
    *,
    experiment: PromptTestExperiment,
    output: Mapping[str, Any],
    scoring_config: AIScoringConfig,
) -> PromptTestOutputScore:
    """为待异步评分的输出预创建 pending 记录。"""

    existing = _find_existing_score(db, experiment.id, output)
    if existing is not None:
        return existing

    unit = experiment.unit
    if unit is None:
        raise PromptTestAIScoringError("实验缺少关联测试单元。")

    score = PromptTestOutputScore(
        task_id=unit.task_id,
        unit_id=unit.id,
        experiment_id=experiment.id,
        run_index=_resolve_run_index(output),
        status=PromptTestOutputScoreStatus.PENDING,
        evaluator_provider_id=scoring_config.evaluator_provider_id,
        evaluator_model_id=scoring_config.evaluator_model_id,
        evaluator_model_name=scoring_config.evaluator_model_name,
        language=scoring_config.language or DEFAULT_SCORE_LANGUAGE,
    )
    db.add(score)
    db.flush()
    return score


def retry_output_score(
    db: Session, score: PromptTestOutputScore
) -> PromptTestOutputScore:
    """重试单条失败评分。"""

    experiment = db.execute(
        select(PromptTestExperiment)
        .where(PromptTestExperiment.id == score.experiment_id)
        .options(
            selectinload(PromptTestExperiment.unit).selectinload(PromptTestUnit.task),
            selectinload(PromptTestExperiment.unit).selectinload(
                PromptTestUnit.prompt_version
            ),
        )
    ).scalar_one_or_none()
    if experiment is None:
        raise PromptTestAIScoringError("评分关联的实验不存在。")
    config = AIScoringConfig(
        enabled=True,
        evaluator_provider_id=score.evaluator_provider_id or 0,
        evaluator_model_id=score.evaluator_model_id or 0,
        evaluator_model_name=score.evaluator_model_name or "",
        language=score.language or DEFAULT_SCORE_LANGUAGE,
    )
    outputs = experiment.outputs if isinstance(experiment.outputs, list) else []
    output = next(
        (
            item
            for item in outputs
            if isinstance(item, Mapping) and _resolve_run_index(item) == score.run_index
        ),
        None,
    )
    if output is None:
        raise PromptTestAIScoringError("评分关联的测试输出不存在。")
    return score_experiment_output(
        db, experiment=experiment, output=output, scoring_config=config, force=True
    )


def build_task_score_summary(db: Session, task_id: int) -> dict[str, Any]:
    """生成任务级评分列表和单元聚合统计。"""

    return build_task_score_summary_for_prompt_version(db, task_id)


def build_task_score_summary_for_prompt_version(
    db: Session, task_id: int, prompt_version_id: int | None = None
) -> dict[str, Any]:
    """生成任务评分列表，可限定目标 Prompt 版本。"""

    filtered_unit_ids: set[int] | None = None
    if prompt_version_id is not None:
        filtered_unit_ids = set(
            db.scalars(
                select(PromptTestUnit.id).where(
                    PromptTestUnit.task_id == task_id,
                    PromptTestUnit.prompt_version_id == prompt_version_id,
                )
            )
        )

    scores = list(
        db.scalars(
            select(PromptTestOutputScore)
            .where(PromptTestOutputScore.task_id == task_id)
            .order_by(
                PromptTestOutputScore.unit_id.asc(),
                PromptTestOutputScore.run_index.asc(),
                PromptTestOutputScore.id.asc(),
            )
        )
    )
    if filtered_unit_ids is not None:
        scores = [score for score in scores if score.unit_id in filtered_unit_ids]
    completed_scores = [
        score
        for score in scores
        if score.status == PromptTestOutputScoreStatus.COMPLETED
        and score.overall_score is not None
    ]
    unit_summaries: dict[str, Any] = {}
    completed_unit_ids = sorted({score.unit_id for score in completed_scores})
    for unit_id in completed_unit_ids:
        unit_scores = [score for score in completed_scores if score.unit_id == unit_id]
        values = [float(score.overall_score or 0) for score in unit_scores]
        unit_summaries[str(unit_id)] = {
            "unit_id": unit_id,
            "count": len(values),
            "avg_score": _round(statistics.fmean(values)) if values else None,
            "variance": _round(_variance(values)) if values else None,
            "stddev": _round(math.sqrt(_variance(values))) if values else None,
            "min_score": _round(min(values)) if values else None,
            "max_score": _round(max(values)) if values else None,
            "dimension_stats": _build_dimension_stats(unit_scores),
        }

    task = db.get(PromptTestTask, task_id)
    status = _build_status_from_scores(scores)
    status = _merge_task_scoring_status(status, task)
    return {"status": status, "scores": scores, "unit_summaries": unit_summaries}


def create_optimization_recommendation(
    db: Session,
    *,
    task_id: int,
    prompt_version_id: int,
    evaluator_provider_id: int,
    evaluator_model_id: int,
    evaluator_model_name: str,
    language: str,
) -> PromptTestOptimizationRecommendation:
    """基于评分生成优化建议。"""

    task = _load_task_with_outputs(db, task_id)
    _validate_recommendation_prompt_version(task, prompt_version_id)
    summary = build_task_score_summary_for_prompt_version(
        db, task_id, prompt_version_id
    )
    valid_count = sum(item["count"] for item in summary["unit_summaries"].values())
    if valid_count <= 0:
        raise PromptTestAIScoringError("当前版本没有有效评分，无法生成优化建议。")

    recommendation = PromptTestOptimizationRecommendation(
        task_id=task_id,
        prompt_version_id=prompt_version_id,
        status=PromptTestOptimizationRecommendationStatus.RUNNING,
        evaluator_provider_id=evaluator_provider_id,
        evaluator_model_id=evaluator_model_id,
        evaluator_model_name=evaluator_model_name,
        language=language or DEFAULT_SCORE_LANGUAGE,
        started_at=datetime.now(UTC),
    )
    db.add(recommendation)
    db.flush()

    try:
        content, raw_response = _invoke_recommendation_llm(
            db,
            task=task,
            summary=summary,
            prompt_version_id=prompt_version_id,
            evaluator_provider_id=evaluator_provider_id,
            evaluator_model_id=evaluator_model_id,
            evaluator_model_name=evaluator_model_name,
            language=language or DEFAULT_SCORE_LANGUAGE,
        )
        recommendation.status = PromptTestOptimizationRecommendationStatus.COMPLETED
        recommendation.content = content
        recommendation.raw_response = raw_response
        recommendation.error = None
    except Exception as exc:  # noqa: BLE001 - 外部模型失败需要落库
        recommendation.status = PromptTestOptimizationRecommendationStatus.FAILED
        recommendation.error = str(exc)
    recommendation.finished_at = datetime.now(UTC)
    db.flush()
    return recommendation


def get_latest_recommendation(
    db: Session, task_id: int, prompt_version_id: int | None = None
) -> PromptTestOptimizationRecommendation | None:
    """读取任务最近一次优化建议。"""

    stmt = (
        select(PromptTestOptimizationRecommendation)
        .where(PromptTestOptimizationRecommendation.task_id == task_id)
        .order_by(PromptTestOptimizationRecommendation.created_at.desc())
    )
    if prompt_version_id is not None:
        stmt = stmt.where(
            PromptTestOptimizationRecommendation.prompt_version_id == prompt_version_id
        )
    return db.scalar(stmt)


def list_recommendations(
    db: Session, task_id: int, prompt_version_id: int | None = None
) -> list[PromptTestOptimizationRecommendation]:
    """读取任务优化建议历史。"""

    stmt = (
        select(PromptTestOptimizationRecommendation)
        .where(PromptTestOptimizationRecommendation.task_id == task_id)
        .order_by(PromptTestOptimizationRecommendation.created_at.desc())
    )
    if prompt_version_id is not None:
        stmt = stmt.where(
            PromptTestOptimizationRecommendation.prompt_version_id == prompt_version_id
        )
    return list(db.scalars(stmt))


def _validate_recommendation_prompt_version(
    task: PromptTestTask, prompt_version_id: int
) -> None:
    """确认目标版本属于当前任务并有对应测试单元。"""

    version_ids = {
        unit.prompt_version_id
        for unit in task.units
        if unit.prompt_version_id is not None
    }
    if prompt_version_id not in version_ids:
        raise PromptTestAIScoringError("目标 Prompt 版本不属于当前测试任务。")


def _target_units(
    task: PromptTestTask, prompt_version_id: int | None
) -> list[PromptTestUnit]:
    if prompt_version_id is None:
        return list(task.units)
    return [unit for unit in task.units if unit.prompt_version_id == prompt_version_id]


def _invoke_score_llm(
    db: Session,
    *,
    unit: PromptTestUnit,
    output: Mapping[str, Any],
    scoring_config: AIScoringConfig,
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider, model = _resolve_evaluator(db, scoring_config)
    language = scoring_config.language or DEFAULT_SCORE_LANGUAGE
    messages = [
        {
            "role": "system",
            "content": (
                "你是严格的 Prompt 测试评审专家。只返回 JSON，不要返回 Markdown。"
                if language.startswith("zh")
                else "You are a strict prompt evaluation judge. Return JSON only, no Markdown."
            ),
        },
        {
            "role": "user",
            "content": _build_score_prompt(unit, output, language),
        },
    ]
    raw_response = _post_chat_completion(
        db,
        provider=provider,
        model_name=model.name,
        messages=messages,
        parameters={"temperature": 0.1, "response_format": {"type": "json_object"}},
    )
    text = _extract_output_text(raw_response)
    parsed = _parse_json_object(text)
    if "overall_score" not in parsed:
        raise PromptTestAIScoringError("评分响应缺少 overall_score。")
    return parsed, raw_response


def _invoke_recommendation_llm(
    db: Session,
    *,
    task: PromptTestTask,
    summary: dict[str, Any],
    prompt_version_id: int,
    evaluator_provider_id: int,
    evaluator_model_id: int,
    evaluator_model_name: str,
    language: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider = db.get(LLMProvider, evaluator_provider_id)
    model = db.get(LLMModel, evaluator_model_id)
    if provider is None or model is None or model.provider_id != provider.id:
        raise PromptTestAIScoringError("未找到可用的优化建议模型。")
    messages = [
        {
            "role": "system",
            "content": (
                "你是 Prompt 优化专家。只返回 JSON。"
                if language.startswith("zh")
                else "You are a prompt optimization expert. Return JSON only."
            ),
        },
        {
            "role": "user",
            "content": _build_recommendation_prompt(
                task, summary, language, prompt_version_id=prompt_version_id
            ),
        },
    ]
    timeout_config = get_testing_timeout_config(db)
    raw_response = _post_chat_completion(
        db,
        provider=provider,
        model_name=model.name or evaluator_model_name,
        messages=messages,
        parameters={"temperature": 0.2, "response_format": {"type": "json_object"}},
        timeout_seconds=float(
            timeout_config.ai_optimization_timeout or DEFAULT_AI_OPTIMIZATION_TIMEOUT
        ),
    )
    content = _parse_json_object(_extract_output_text(raw_response))
    return _normalize_recommendation_content(content), raw_response


def _normalize_recommendation_content(content: dict[str, Any]) -> dict[str, Any]:
    """将模型返回的建议内容归一成前端可直接展示的自然语言字段。"""

    normalized = dict(content)
    if "parameter_advice" not in normalized and normalized.get("temperature_advice"):
        normalized["parameter_advice"] = normalized["temperature_advice"]
    if "parameter_advice" in normalized:
        normalized["parameter_advice"] = _format_recommendation_advice(
            normalized["parameter_advice"]
        )
    return normalized


def _format_recommendation_advice(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        lines = []
        for key, item in value.items():
            text = _format_recommendation_advice(item)
            if text:
                lines.append(f"{key}：{text}")
        return "\n".join(lines)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        lines = []
        for item in value:
            text = _format_recommendation_advice(item)
            if text:
                lines.append(text)
        return "\n".join(lines)
    return str(value).strip()


def _post_chat_completion(
    db: Session,
    *,
    provider: LLMProvider,
    model_name: str,
    messages: list[dict[str, Any]],
    parameters: dict[str, Any],
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    base_url = _resolve_base_url(provider)
    timeout_config = get_testing_timeout_config(db)
    timeout = float(
        timeout_seconds
        if timeout_seconds is not None
        else timeout_config.test_task_timeout or DEFAULT_TEST_TASK_TIMEOUT
    )
    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model_name, "messages": messages, **parameters},
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise PromptTestAIScoringError(
            f"LLM 请求超时（{timeout:g} 秒），请调大测试任务超时时间或减少测试输出内容后重试。"
        ) from exc
    except httpx.RequestError as exc:
        raise PromptTestAIScoringError(f"LLM 请求失败：{exc}") from exc
    if response.status_code >= 400:
        raise PromptTestAIScoringError(f"LLM 请求失败 (HTTP {response.status_code})")
    try:
        payload = response.json()
    except ValueError as exc:
        raise PromptTestAIScoringError("LLM 评分响应解析失败。") from exc
    if not isinstance(payload, dict):
        raise PromptTestAIScoringError("LLM 评分响应格式无效。")
    return payload


def _resolve_evaluator(
    db: Session, scoring_config: AIScoringConfig
) -> tuple[LLMProvider, LLMModel]:
    provider = db.get(LLMProvider, scoring_config.evaluator_provider_id)
    model = db.get(LLMModel, scoring_config.evaluator_model_id)
    if provider is None or model is None or model.provider_id != provider.id:
        raise PromptTestAIScoringError("未找到可用的 AI 评分模型。")
    return provider, model


def _load_task_with_outputs(db: Session, task_id: int) -> PromptTestTask:
    task = db.execute(
        select(PromptTestTask)
        .where(PromptTestTask.id == task_id, PromptTestTask.is_deleted.is_(False))
        .options(
            selectinload(PromptTestTask.prompt_version),
            selectinload(PromptTestTask.units).selectinload(
                PromptTestUnit.prompt_version
            ),
            selectinload(PromptTestTask.units)
            .selectinload(PromptTestUnit.experiments)
            .selectinload(PromptTestExperiment.output_scores),
        )
    ).scalar_one_or_none()
    if task is None:
        raise PromptTestAIScoringError("测试任务不存在。")
    return task


def _collect_latest_outputs(
    task: PromptTestTask,
) -> list[tuple[PromptTestExperiment, Mapping[str, Any]]]:
    candidates: list[tuple[PromptTestExperiment, Mapping[str, Any]]] = []
    for unit in task.units:
        latest = _latest_experiment(unit)
        if latest is None:
            continue
        outputs = latest.outputs if isinstance(latest.outputs, list) else []
        for output in outputs:
            if not isinstance(output, Mapping):
                continue
            if _is_failed_output(output):
                continue
            if not _safe_str(output.get("output_text")):
                continue
            candidates.append((latest, output))
    return candidates


def _latest_experiment(unit: PromptTestUnit) -> PromptTestExperiment | None:
    experiments = list(unit.experiments or [])
    if not experiments:
        return None
    return max(
        experiments,
        key=lambda item: (
            item.sequence or 0,
            item.created_at or datetime.min.replace(tzinfo=UTC),
            item.id or 0,
        ),
    )


def _find_existing_score(
    db: Session, experiment_id: int, output: Mapping[str, Any]
) -> PromptTestOutputScore | None:
    return db.scalar(
        select(PromptTestOutputScore).where(
            PromptTestOutputScore.experiment_id == experiment_id,
            PromptTestOutputScore.run_index == _resolve_run_index(output),
        )
    )


def _should_skip_existing_score(
    score: PromptTestOutputScore | None, *, force: bool
) -> bool:
    if score is None or force:
        return False
    return score.status in {
        PromptTestOutputScoreStatus.COMPLETED,
        PromptTestOutputScoreStatus.FAILED,
        PromptTestOutputScoreStatus.RUNNING,
    }


def _build_score_prompt(
    unit: PromptTestUnit, output: Mapping[str, Any], language: str
) -> str:
    task = unit.task
    prompt_description = ""
    if unit.prompt_version and unit.prompt_version.prompt:
        prompt_description = unit.prompt_version.prompt.description or ""
    prompt_text = unit.prompt_template or (
        unit.prompt_version.content if unit.prompt_version else ""
    )
    payload = {
        "language": language,
        "task_description": task.description if task else None,
        "unit_description": unit.description,
        "prompt_description": prompt_description,
        "prompt": prompt_text,
        "temperature": unit.temperature,
        "temperature_mode": _resolve_temperature_mode(unit, output),
        "parameters": _resolve_output_parameters(unit, output),
        "messages": output.get("messages"),
        "variables": output.get("variables"),
        "llm_output": output.get("output_text"),
    }
    return (
        "请基于以下 JSON 对 LLM 输出做多角度评分。必须只返回 JSON，不要返回 Markdown。"
        "评分统一使用 0-100 的百分制整数，0 表示完全不可用，100 表示完全满足且无需改进。"
        "禁止使用 0-5、1-5、0-10 或 1-10 分制；如果你习惯给 8/10，请返回 80。"
        "返回结构必须为："
        '{"overall_score": number, "dimension_scores": {"准确性": number, '
        '"完整性": number, "清晰度": number, "稳定性": number}, "reason": string}。'
        "overall_score 和所有 dimension_scores 都必须是 0 到 100 之间的数字。"
        f"理由必须使用 {language} 对应语言。\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def _build_recommendation_prompt(
    task: PromptTestTask,
    summary: dict[str, Any],
    language: str,
    *,
    prompt_version_id: int | None = None,
) -> str:
    units_payload: list[dict[str, Any]] = []
    for unit in _target_units(task, prompt_version_id):
        latest = _latest_experiment(unit)
        outputs = latest.outputs if latest and isinstance(latest.outputs, list) else []
        units_payload.append(
            {
                "unit_id": unit.id,
                "prompt_version_id": unit.prompt_version_id,
                "unit_name": unit.name,
                "model_name": unit.model_name,
                "temperature": unit.temperature,
                "temperature_mode": _resolve_temperature_mode(unit, None),
                "top_p": unit.top_p,
                "prompt": unit.prompt_template
                or (unit.prompt_version.content if unit.prompt_version else ""),
                "sample_outputs": [
                    _compact_recommendation_output(output) for output in outputs[:3]
                ],
            }
        )
    payload = {
        "language": language,
        "task": {"id": task.id, "name": task.name, "description": task.description},
        "target_prompt_version_id": prompt_version_id,
        "score_summary": _compact_recommendation_score_summary(summary),
        "units": units_payload,
    }
    semantic_summary = _build_recommendation_semantic_summary(summary)
    if semantic_summary:
        payload["semantic_summary"] = semantic_summary
    semantic_instruction = (
        "semantic_summary 是 embedding 语义分析的额外信号，不能替代现有 AI 评分；"
        "请结合其中的目标、关键指标和风险提示调整优化方向。"
        if semantic_summary
        else ""
    )
    return (
        "请基于评分结果生成 Prompt 测试优化建议。只返回 JSON，字段包括 "
        "overall_advice、parameter_advice、model_advice、prompt_revision、validation_plan。"
        f"{semantic_instruction}"
        "parameter_advice 应覆盖本次测试实际使用的参数，例如 temperature、top_p、max_tokens、response_format 或其他模型参数。"
        "prompt_revision 必须是完整可直接落库的新 Prompt 文本，不能只返回修改片段、摘要或解释。"
        f"所有文本使用 {language} 对应语言。\n"
        f"{json.dumps(payload, ensure_ascii=False, default=str)}"
    )


def _resolve_temperature_mode(
    unit: PromptTestUnit, output: Mapping[str, Any] | None
) -> str:
    parameters = output.get("parameters") if isinstance(output, Mapping) else None
    if isinstance(parameters, Mapping):
        raw_mode = parameters.get("temperature_mode")
        if raw_mode in {"llm_default", "explicit"}:
            return str(raw_mode)
        if "temperature" not in parameters and unit.temperature is None:
            return "llm_default"
    return "llm_default" if unit.temperature is None else "explicit"


def _resolve_output_parameters(
    unit: PromptTestUnit, output: Mapping[str, Any]
) -> dict[str, Any]:
    raw_parameters = output.get("parameters")
    parameters = dict(raw_parameters) if isinstance(raw_parameters, Mapping) else {}
    temperature_mode = _resolve_temperature_mode(unit, output)
    parameters["temperature_mode"] = temperature_mode
    if temperature_mode == "llm_default":
        parameters.pop("temperature", None)
    else:
        parameters["temperature"] = unit.temperature
    return parameters


def _extract_output_text(payload: Mapping[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, Sequence) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping) and isinstance(message.get("content"), str):
                return message["content"]
            text = first.get("text")
            if isinstance(text, str):
                return text
    return ""


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(cleaned[start : end + 1])
        else:
            raise PromptTestAIScoringError("LLM 评分响应不是有效 JSON。") from exc
    if not isinstance(parsed, dict):
        raise PromptTestAIScoringError("LLM 评分响应不是 JSON 对象。")
    return parsed


def _normalize_score_payload(
    payload: Mapping[str, Any],
) -> tuple[float, dict[str, float], str | None]:
    overall_score = _parse_score_value(
        payload.get("overall_score"), field="overall_score"
    )
    dimension_scores = _normalize_dimension_scores(payload.get("dimension_scores"))
    _reject_compact_score_scale([overall_score, *dimension_scores.values()])
    return overall_score, dimension_scores, _safe_str(payload.get("reason"))


def _normalize_dimension_scores(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping) or not value:
        raise PromptTestAIScoringError("评分响应缺少 dimension_scores。")
    result: dict[str, float] = {}
    for key, raw_score in value.items():
        label = str(key).strip()
        if not label:
            continue
        result[label] = _parse_score_value(raw_score, field=f"dimension_scores.{label}")
    if not result:
        raise PromptTestAIScoringError("评分响应缺少有效的维度评分。")
    return result


def _build_dimension_stats(scores: Sequence[PromptTestOutputScore]) -> dict[str, Any]:
    values_by_dimension: dict[str, list[float]] = {}
    for score in scores:
        if not isinstance(score.dimension_scores, Mapping):
            continue
        for key, value in score.dimension_scores.items():
            if isinstance(value, (int, float)):
                values_by_dimension.setdefault(str(key), []).append(float(value))
    return {
        key: {
            "avg": _round(statistics.fmean(values)),
            "variance": _round(_variance(values)),
            "stddev": _round(math.sqrt(_variance(values))),
        }
        for key, values in values_by_dimension.items()
        if values
    }


def _build_status_from_scores(
    scores: Sequence[PromptTestOutputScore],
) -> dict[str, Any]:
    total = len(scores)
    completed = sum(
        1 for item in scores if item.status == PromptTestOutputScoreStatus.COMPLETED
    )
    failed = sum(
        1 for item in scores if item.status == PromptTestOutputScoreStatus.FAILED
    )
    running = sum(
        1 for item in scores if item.status == PromptTestOutputScoreStatus.RUNNING
    )
    pending = sum(
        1 for item in scores if item.status == PromptTestOutputScoreStatus.PENDING
    )
    if running:
        status = "running"
    elif pending:
        status = "pending"
    elif failed and completed == 0:
        status = "failed"
    elif total and completed + failed >= total:
        status = "completed"
    else:
        status = "idle"
    return {
        "status": status,
        "total": total,
        "completed": completed,
        "failed": failed,
        "running": running,
        "pending": pending,
        "percentage": int(round(((completed + failed) / total) * 100)) if total else 0,
        "language": scores[0].language if scores else DEFAULT_SCORE_LANGUAGE,
    }


def _merge_task_scoring_status(
    status: dict[str, Any], task: PromptTestTask | None
) -> dict[str, Any]:
    if task is None or not isinstance(task.config, Mapping):
        return status
    ai_scoring = task.config.get("ai_scoring")
    if not isinstance(ai_scoring, Mapping):
        return status
    task_status = _safe_str(ai_scoring.get("status"))
    if task_status not in {"running", "pending"}:
        return status
    progress = ai_scoring.get("progress")
    progress_map = progress if isinstance(progress, Mapping) else {}
    merged = dict(status)
    current = _safe_int(progress_map.get("current"))
    total = _safe_int(progress_map.get("total"))
    percentage = _safe_int(progress_map.get("percentage"))
    merged["status"] = task_status
    if current is not None:
        merged["current"] = current
    if total is not None:
        merged["total"] = total
    if percentage is not None:
        merged["percentage"] = max(0, min(100, percentage))
    merged["language"] = _safe_str(ai_scoring.get("language")) or merged.get(
        "language", DEFAULT_SCORE_LANGUAGE
    )
    return merged


def _compact_recommendation_score_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    scores_payload: list[dict[str, Any]] = []
    raw_scores = summary.get("scores")
    scores = raw_scores if isinstance(raw_scores, Sequence) else []
    for score in scores[:MAX_RECOMMENDATION_SCORE_ITEMS]:
        scores_payload.append(
            {
                "unit_id": getattr(score, "unit_id", None),
                "run_index": getattr(score, "run_index", None),
                "status": _enum_value(getattr(score, "status", None)),
                "overall_score": getattr(score, "overall_score", None),
                "dimension_scores": _plain_mapping(
                    getattr(score, "dimension_scores", None)
                ),
                "reason": _truncate_text(
                    getattr(score, "reason", None),
                    max_chars=MAX_RECOMMENDATION_REASON_CHARS,
                ),
            }
        )
    return {
        "status": summary.get("status"),
        "unit_summaries": summary.get("unit_summaries"),
        "scores": scores_payload,
    }


def _build_recommendation_semantic_summary(
    summary: Mapping[str, Any],
) -> dict[str, Any] | None:
    raw_semantic = _resolve_semantic_summary(summary)
    if not isinstance(raw_semantic, Mapping):
        return None
    raw_groups = raw_semantic.get("group_summaries")
    groups = raw_groups if isinstance(raw_groups, Sequence) else []
    compact_groups = [
        _compact_semantic_group(group)
        for group in groups[:MAX_RECOMMENDATION_SEMANTIC_GROUPS]
        if isinstance(group, Mapping)
    ]
    if not compact_groups:
        return None
    return {
        "title": "语义分析摘要",
        "scope_note": (
            "语义指标按测试单元和变量组合分组计算，不能把不同变量组合直接比较。"
        ),
        "usage_note": "embedding 语义分析是优化参考信号，不替代 AI 评分。",
        "group_count": raw_semantic.get("group_count") or len(compact_groups),
        "groups": compact_groups,
    }


def _resolve_semantic_summary(summary: Mapping[str, Any]) -> Any:
    direct = summary.get("semantic_summary")
    if isinstance(direct, Mapping):
        return direct
    extra = summary.get("extra")
    if isinstance(extra, Mapping):
        semantic_summary = extra.get("semantic_summary")
        if isinstance(semantic_summary, Mapping):
            return semantic_summary
    return None


def _compact_semantic_group(group: Mapping[str, Any]) -> dict[str, Any]:
    objective = _safe_str(group.get("semantic_objective")) or "consistency"
    sample_count = _safe_int(group.get("sample_count"))
    risk_notes = _build_semantic_risk_notes(group, objective, sample_count)
    return {
        "unit_id": group.get("unit_id"),
        "unit_name": group.get("unit_name"),
        "variable_case_hash": group.get("variable_case_hash"),
        "objective": objective,
        "objective_note": _semantic_objective_note(objective),
        "sample_count": sample_count,
        "mean_pairwise_similarity": _safe_metric(group.get("mean_pairwise_similarity")),
        "semantic_dispersion": _safe_metric(group.get("semantic_dispersion")),
        "outlier_count": _safe_int(group.get("outlier_count")),
        "interpretation": _truncate_text(
            group.get("interpretation"), max_chars=MAX_RECOMMENDATION_REASON_CHARS
        ),
        "risk_notes": risk_notes,
    }


def _semantic_objective_note(objective: str) -> str:
    if objective == "diversity":
        return "目标：多样性，关注回答是否覆盖不同角度；相似度过高可能表示过度收敛，应鼓励差异。"
    if objective == "balanced":
        return "目标：平衡，既避免语义漂移，也避免输出过度收敛到单一表达。"
    return "目标：一致性，关注同一变量组合下回答是否稳定贴合任务。"


def _build_semantic_risk_notes(
    group: Mapping[str, Any], objective: str, sample_count: int | None
) -> list[str]:
    notes = []
    if sample_count is None or sample_count < 2:
        notes.append("样本不足，语义指标只能作为弱参考。")
    outlier_count = _safe_int(group.get("outlier_count")) or 0
    if outlier_count > 0:
        notes.append("存在异常样本方向，优化时要检查离群输出是否偏离任务。")
    interpretation = _safe_str(group.get("interpretation"))
    if interpretation:
        notes.append(interpretation)
    if objective == "diversity":
        notes.append(
            "多样性目标下高相似度可能代表过度收敛，应优先检查是否需要扩展回答角度。"
        )
    elif objective == "balanced":
        notes.append("平衡目标下同时关注相似度与离散度，不追求单一方向极值。")
    return notes


def _safe_metric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return _round(float(value))
    if isinstance(value, str) and value.strip():
        try:
            return _round(float(value))
        except ValueError:
            return None
    return None


def _compact_recommendation_output(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "run_index": _resolve_run_index(output),
        "variables": _truncate_json(
            output.get("variables"), max_chars=MAX_RECOMMENDATION_JSON_CHARS
        ),
        "messages_excerpt": _truncate_json(
            output.get("messages"), max_chars=MAX_RECOMMENDATION_JSON_CHARS
        ),
        "output_excerpt": _truncate_text(
            output.get("output_text"), max_chars=MAX_RECOMMENDATION_OUTPUT_CHARS
        ),
        "latency_ms": output.get("latency_ms"),
        "total_tokens": output.get("total_tokens"),
        "total_cost": output.get("total_cost"),
        "cost_currency": output.get("cost_currency"),
    }


def _truncate_json(value: Any, *, max_chars: int) -> str | None:
    if value is None:
        return None
    return _truncate_text(
        json.dumps(value, ensure_ascii=False, default=str), max_chars=max_chars
    )


def _truncate_text(value: Any, *, max_chars: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}...（已截断）"


def _plain_mapping(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    return dict(value)


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _resolve_base_url(provider: LLMProvider) -> str:
    base_url = provider.base_url
    if not base_url:
        defaults = get_provider_defaults(provider.provider_key)
        base_url = defaults.base_url if defaults else None
    if not base_url:
        raise PromptTestAIScoringError("评分模型提供方未配置基础 URL。")
    return base_url.rstrip("/")


def _resolve_run_index(output: Mapping[str, Any]) -> int:
    value = output.get("run_index") or output.get("sequence") or 1
    parsed = _safe_int(value)
    return parsed if parsed is not None and parsed > 0 else 1


def _is_failed_output(output: Mapping[str, Any]) -> bool:
    status = _safe_str(output.get("status"))
    if status and status.lower() in {"failed", "error"}:
        return True
    return bool(_safe_str(output.get("error")))


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def _safe_str(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _parse_score_value(value: Any, *, field: str) -> float:
    numeric: float | None = None
    if isinstance(value, bool):
        numeric = None
    elif isinstance(value, (int, float)) and math.isfinite(float(value)):
        numeric = float(value)
    elif isinstance(value, str) and value.strip():
        try:
            numeric = float(value)
        except ValueError:
            numeric = None
    if numeric is None or not 0 <= numeric <= 100:
        raise PromptTestAIScoringError(f"评分字段 {field} 必须是 0-100 的数字。")
    return float(numeric)


def _reject_compact_score_scale(values: Sequence[float]) -> None:
    if not values:
        raise PromptTestAIScoringError("评分响应缺少有效分数。")
    max_score = max(values)
    if 0 < max_score <= 10:
        raise PromptTestAIScoringError(
            "评分疑似使用 5 分制或 10 分制，请按 0-100 百分制重新评分。"
        )


def _variance(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    avg = statistics.fmean(values)
    return statistics.fmean([(item - avg) ** 2 for item in values])


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    if not math.isfinite(float(value)):
        return None
    return round(float(value), 4)


__all__ = [
    "AIScoringConfig",
    "ParallelLimits",
    "PromptTestAIScoringError",
    "build_ai_scoring_config_dict",
    "parse_ai_scoring_config",
    "resolve_parallel_limits",
    "score_experiment_output",
    "score_task_outputs",
    "retry_output_score",
    "build_task_score_summary",
    "build_task_score_summary_for_prompt_version",
    "create_optimization_recommendation",
    "ensure_pending_output_score",
    "get_latest_recommendation",
    "list_recommendations",
    "update_task_ai_scoring_status",
]
