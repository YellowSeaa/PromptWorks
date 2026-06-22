from __future__ import annotations

import logging
import random
import statistics
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.llm_provider_registry import get_provider_defaults
from app.db import session as db_session_module
from app.models.llm_provider import LLMModel, LLMProvider
from app.models.prompt_test import (
    PromptTestExperiment,
    PromptTestExperimentStatus,
    PromptTestUnit,
)
from app.models.usage import LLMUsageLog
from app.services.llm_context import truncate_messages_for_context
from app.services.model_costs import apply_cost_to_usage_log, calculate_model_call_cost
from app.services.test_run import (
    DEFAULT_CONCURRENCY_LIMIT,
    REQUEST_SLEEP_RANGE,
    _format_error_detail,
    _try_parse_json,
)
from app.services.system_settings import (
    DEFAULT_TEST_TASK_TIMEOUT,
    get_testing_timeout_config,
)
from app.services.prompt_test_ai_scoring import (
    ensure_pending_output_score,
    parse_ai_scoring_config,
    resolve_parallel_limits,
    score_experiment_output,
)

logger = logging.getLogger("promptworks.prompt_test_engine")

_KNOWN_PARAMETER_KEYS = {
    "max_tokens",
    "presence_penalty",
    "frequency_penalty",
    "response_format",
    "stop",
    "logit_bias",
    "top_k",
    "seed",
    "user",
    "n",
    "parallel_tool_calls",
    "tool_choice",
    "tools",
    "metadata",
}

_NESTED_PARAMETER_KEYS = {"llm_parameters", "model_parameters", "parameters"}


class PromptTestExecutionError(Exception):
    """执行 Prompt 测试实验时抛出的业务异常。"""

    __test__ = False

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def execute_prompt_test_experiment(
    db: Session,
    experiment: PromptTestExperiment,
    progress_callback: Callable[[int], None] | None = None,
    cancellation_callback: Callable[[], bool] | None = None,
) -> PromptTestExperiment:
    """执行单个最小测试单元的实验，并存储结果。"""

    if experiment.status not in {
        PromptTestExperimentStatus.PENDING,
        PromptTestExperimentStatus.RUNNING,
        PromptTestExperimentStatus.FAILED,
    }:
        return experiment

    unit = experiment.unit
    if unit is None:
        raise PromptTestExecutionError("实验缺少关联的测试单元。")

    provider, model = _resolve_provider_and_model(db, unit)
    prompt_snapshot = _resolve_prompt_snapshot(unit)
    parameters = _collect_parameters(unit)
    context_template = unit.variables or {}

    experiment.status = PromptTestExperimentStatus.RUNNING
    experiment.started_at = datetime.now(UTC)
    experiment.error = None
    db.flush()

    timeout_config = get_testing_timeout_config(db)
    request_timeout = float(
        timeout_config.test_task_timeout or DEFAULT_TEST_TASK_TIMEOUT
    )

    run_records = _normalize_existing_outputs(experiment.outputs)
    completed_indexes = _collect_completed_run_indexes(run_records)

    rounds_per_case = max(1, int(unit.rounds or 1))
    case_count = _count_variable_cases(context_template)
    total_runs = rounds_per_case * max(case_count, 1)
    concurrency_limit = DEFAULT_CONCURRENCY_LIMIT
    if model and isinstance(model.concurrency_limit, int):
        concurrency_limit = max(1, model.concurrency_limit)
    scoring_config = parse_ai_scoring_config(unit.task.config if unit.task else None)
    scoring_limit = DEFAULT_CONCURRENCY_LIMIT
    shared_single_lane = False
    if scoring_config is not None and model is not None:
        evaluator_model = db.get(LLMModel, scoring_config.evaluator_model_id)
        evaluator_limit = (
            evaluator_model.concurrency_limit
            if evaluator_model and isinstance(evaluator_model.concurrency_limit, int)
            else DEFAULT_CONCURRENCY_LIMIT
        )
        limits = resolve_parallel_limits(
            test_model_id=model.id,
            evaluator_model_id=scoring_config.evaluator_model_id,
            test_concurrency_limit=concurrency_limit,
            evaluator_concurrency_limit=evaluator_limit,
        )
        concurrency_limit = limits.test_limit
        scoring_limit = limits.scoring_limit
        shared_single_lane = limits.shared_single_lane
    worker_count = max(1, min(concurrency_limit, total_runs))
    scoring_worker_count = max(1, scoring_limit)
    provider_for_call = cast(
        LLMProvider,
        SimpleNamespace(
            id=provider.id,
            provider_key=provider.provider_key,
            api_key=provider.api_key,
            base_url=provider.base_url,
        ),
    )
    model_for_call = (
        cast(
            LLMModel,
            SimpleNamespace(
                id=model.id,
                provider_id=model.provider_id,
                name=model.name,
                context_length=model.context_length,
            ),
        )
        if model
        else None
    )
    unit_for_call = cast(
        PromptTestUnit,
        SimpleNamespace(
            id=unit.id,
            model_name=unit.model_name,
            temperature=unit.temperature,
            parameters=unit.parameters,
            prompt_template=unit.prompt_template,
        ),
    )

    def _execute_run(run_index: int) -> dict[str, Any]:
        context = _resolve_context(context_template, run_index)
        return _execute_single_round(
            provider=provider_for_call,
            model=model_for_call,
            unit=unit_for_call,
            prompt_snapshot=prompt_snapshot,
            base_parameters=parameters,
            context=context,
            run_index=run_index,
            request_timeout=request_timeout,
        )

    records_by_index = {
        int(record["run_index"]): dict(record)
        for record in run_records
        if isinstance(record.get("run_index"), (int, float))
    }

    def _ordered_records() -> list[dict[str, Any]]:
        return [
            records_by_index[run_index]
            for run_index in range(1, total_runs + 1)
            if run_index in records_by_index
        ]

    def _persist_running_state(error: str | None) -> None:
        _persist_experiment_state(
            db,
            experiment,
            _ordered_records(),
            status=PromptTestExperimentStatus.RUNNING,
            error=error,
        )

    pending_indexes = [
        run_index
        for run_index in range(1, total_runs + 1)
        if run_index not in completed_indexes
    ]
    next_pending = 0
    futures: dict[Future[dict[str, Any]], int] = {}
    cancelled = False

    def _submit_available(executor: ThreadPoolExecutor) -> None:
        nonlocal next_pending
        while len(futures) < worker_count and next_pending < len(pending_indexes):
            if cancellation_callback is not None and cancellation_callback():
                return
            run_index = pending_indexes[next_pending]
            next_pending += 1
            futures[executor.submit(_execute_run, run_index)] = run_index

    scoring_executor: ThreadPoolExecutor | None = None
    if scoring_config is not None and not shared_single_lane:
        scoring_executor = ThreadPoolExecutor(max_workers=scoring_worker_count)

    def _score_output_with_new_session(output: dict[str, Any]) -> None:
        if scoring_config is None:
            raise PromptTestExecutionError("测试任务未配置 AI 评分模型。")
        scoring_db = db_session_module.SessionLocal()
        try:
            scoring_experiment = scoring_db.get(PromptTestExperiment, experiment.id)
            if scoring_experiment is None:
                raise PromptTestExecutionError("AI 评分关联的实验不存在。")
            score_experiment_output(
                scoring_db,
                experiment=scoring_experiment,
                output=output,
                scoring_config=scoring_config,
            )
            scoring_db.commit()
        except Exception:
            scoring_db.rollback()
            raise
        finally:
            scoring_db.close()

    def _log_scoring_failure(future: Future[None]) -> None:
        if future.cancelled():
            return
        try:
            future.result()
        except Exception:
            logger.exception("Prompt 测试输出 AI 评分后台任务失败")

    def _submit_scoring(run_index: int, run_record: dict[str, Any]) -> None:
        if scoring_config is None or not run_record.get("output_text"):
            return
        try:
            ensure_pending_output_score(
                db,
                experiment=experiment,
                output=run_record,
                scoring_config=scoring_config,
            )
            db.commit()
        except Exception:  # pragma: no cover - 评分状态初始化失败不影响测试任务
            db.rollback()
            logger.exception(
                "Prompt 测试单元 %s 的第 %s 次 AI 评分记录初始化失败",
                unit.id,
                run_index,
            )
            return
        if scoring_executor is None:
            try:
                score_experiment_output(
                    db,
                    experiment=experiment,
                    output=run_record,
                    scoring_config=scoring_config,
                )
            except Exception:  # pragma: no cover - 评分失败不影响测试任务
                logger.exception(
                    "Prompt 测试单元 %s 的第 %s 次 AI 评分失败",
                    unit.id,
                    run_index,
                )
            return
        future = scoring_executor.submit(
            _score_output_with_new_session, dict(run_record)
        )
        future.add_done_callback(_log_scoring_failure)

    executor = ThreadPoolExecutor(max_workers=worker_count)
    try:
        _submit_available(executor)
        while futures:
            if cancellation_callback is not None and cancellation_callback():
                cancelled = True
                for future in futures:
                    future.cancel()
                break

            done, _pending = wait(
                futures.keys(), timeout=0.1, return_when=FIRST_COMPLETED
            )
            if not done:
                continue

            for future in done:
                run_index = futures.pop(future)
                try:
                    run_record = future.result()
                except PromptTestExecutionError as exc:
                    run_record = {
                        "run_index": run_index,
                        "status": "failed",
                        "error": str(exc),
                        "variables": _extract_variables(
                            _resolve_context(context_template, run_index)
                        )
                        or None,
                    }
                    if exc.status_code is not None:
                        run_record["status_code"] = exc.status_code
                    records_by_index[run_index] = run_record
                    completed_indexes.add(run_index)
                    _persist_running_state(str(exc))
                    logger.warning(
                        "Prompt 测试单元 %s 的第 %s 次调用失败: %s",
                        unit.id,
                        run_index,
                        exc,
                    )
                else:
                    records_by_index[run_index] = run_record
                    completed_indexes.add(run_index)
                    _persist_running_state(None)
                    usage_log = _build_usage_log(
                        provider=provider,
                        model=model,
                        unit=unit,
                        run_record=run_record,
                    )
                    db.add(usage_log)
                    _submit_scoring(run_index, run_record)

                if progress_callback is not None:
                    try:
                        progress_callback(1)
                    except Exception:  # pragma: no cover - 防御性兜底
                        logger.exception("更新 Prompt 测试进度时出现异常")

            _submit_available(executor)
    finally:
        executor.shutdown(wait=not cancelled, cancel_futures=True)
        if scoring_executor is not None:
            scoring_executor.shutdown(wait=False, cancel_futures=cancelled)

    run_records = _ordered_records()
    if cancelled or (cancellation_callback is not None and cancellation_callback()):
        _persist_experiment_state(
            db,
            experiment,
            run_records,
            status=PromptTestExperimentStatus.CANCELLED,
            error="测试任务已取消",
            finished=True,
        )
        return experiment

    summary = _summarize_run_records(run_records)
    failed_runs = summary["failed_runs"]
    error: str | None
    if failed_runs and failed_runs == len(run_records):
        status = PromptTestExperimentStatus.FAILED
        error = f"全部 {failed_runs} 次调用失败"
    else:
        status = PromptTestExperimentStatus.COMPLETED
        error = f"{failed_runs} 次调用失败" if failed_runs else None
    _persist_experiment_state(
        db,
        experiment,
        run_records,
        status=status,
        error=error,
        finished=True,
        metrics=summary["metrics"],
    )
    return experiment


def _normalize_existing_outputs(outputs: Any) -> list[dict[str, Any]]:
    if not isinstance(outputs, Sequence) or isinstance(
        outputs, (str, bytes, bytearray)
    ):
        return []
    return [dict(item) for item in outputs if isinstance(item, Mapping)]


def _collect_completed_run_indexes(records: Sequence[Mapping[str, Any]]) -> set[int]:
    indexes: set[int] = set()
    for record in records:
        if record.get("status") == "failed" or record.get("error"):
            continue
        value = record.get("run_index")
        if isinstance(value, (int, float)) and int(value) > 0:
            indexes.add(int(value))
    return indexes


def _summarize_run_records(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    latencies: list[int] = []
    token_totals: list[int] = []
    json_success = 0
    failed_runs = 0

    for record in records:
        if record.get("status") == "failed" or record.get("error"):
            failed_runs += 1
            continue

        latency = record.get("latency_ms")
        if isinstance(latency, (int, float)):
            latencies.append(int(latency))
        tokens = record.get("total_tokens")
        if isinstance(tokens, (int, float)):
            token_totals.append(int(tokens))
        if record.get("parsed_output") is not None:
            json_success += 1

    metrics = _aggregate_metrics(
        latencies=latencies,
        tokens=token_totals,
        total_rounds=len(records),
        json_success=json_success,
    )
    metrics["failed_runs"] = failed_runs
    metrics["success_runs"] = len(records) - failed_runs
    return {"metrics": metrics, "failed_runs": failed_runs}


def _persist_experiment_state(
    db: Session,
    experiment: PromptTestExperiment,
    records: Sequence[Mapping[str, Any]],
    *,
    status: PromptTestExperimentStatus,
    error: str | None,
    finished: bool = False,
    metrics: dict[str, Any] | None = None,
) -> None:
    experiment.outputs = [dict(record) for record in records]
    summary_metrics = metrics or _summarize_run_records(records)["metrics"]
    experiment.metrics = summary_metrics
    experiment.status = status
    experiment.error = error
    if finished:
        experiment.finished_at = datetime.now(UTC)
    db.flush()


def _resolve_provider_and_model(
    db: Session, unit: PromptTestUnit
) -> tuple[LLMProvider, LLMModel | None]:
    provider: LLMProvider | None = None
    model: LLMModel | None = None

    if isinstance(unit.llm_provider_id, int):
        provider = db.get(LLMProvider, unit.llm_provider_id)

    extra_data = unit.extra if isinstance(unit.extra, Mapping) else {}
    provider_key = extra_data.get("provider_key")
    if provider is None and isinstance(provider_key, str):
        provider = db.scalar(
            select(LLMProvider).where(LLMProvider.provider_key == provider_key)
        )

    model_id = extra_data.get("llm_model_id")
    if provider and isinstance(model_id, int):
        model = db.get(LLMModel, model_id)

    if provider is None:
        stmt = (
            select(LLMProvider, LLMModel)
            .join(LLMModel, LLMModel.provider_id == LLMProvider.id)
            .where(LLMModel.name == unit.model_name)
        )
        record = db.execute(stmt).first()
        if record:
            provider, model = record

    if provider is None:
        provider = db.scalar(
            select(LLMProvider).where(LLMProvider.provider_name == unit.model_name)
        )

    if provider is None:
        raise PromptTestExecutionError("未找到合适的模型提供者配置。")

    if model is None:
        model = db.scalar(
            select(LLMModel).where(
                LLMModel.provider_id == provider.id,
                LLMModel.name == unit.model_name,
            )
        )

    if model is not None and model.model_type != "chat":
        raise PromptTestExecutionError("测试任务调用模型必须是 chat 类型模型。")

    return provider, model


def _resolve_prompt_snapshot(unit: PromptTestUnit) -> str:
    if unit.prompt_template:
        return str(unit.prompt_template)
    if unit.prompt_version and unit.prompt_version.content:
        return unit.prompt_version.content
    return ""


def _collect_parameters(unit: PromptTestUnit) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if unit.temperature is not None:
        params["temperature"] = unit.temperature
    if unit.top_p is not None:
        params["top_p"] = unit.top_p

    raw_parameters = unit.parameters if isinstance(unit.parameters, Mapping) else {}
    for key in _NESTED_PARAMETER_KEYS:
        nested = raw_parameters.get(key)
        if isinstance(nested, Mapping):
            params.update(dict(nested))

    for key, value in raw_parameters.items():
        if key in {"conversation", "messages"}:
            continue
        if key in _KNOWN_PARAMETER_KEYS and value is not None:
            params[key] = value

    return params


def _build_recorded_parameters(
    unit: PromptTestUnit, params: Mapping[str, Any]
) -> dict[str, Any]:
    recorded = dict(params)
    if unit.temperature is None:
        recorded.pop("temperature", None)
        recorded["temperature_mode"] = "llm_default"
    else:
        recorded["temperature"] = unit.temperature
        recorded["temperature_mode"] = "explicit"
    return recorded


def _execute_single_round(
    *,
    provider: LLMProvider,
    model: LLMModel | None,
    unit: PromptTestUnit,
    prompt_snapshot: str,
    base_parameters: Mapping[str, Any],
    context: Mapping[str, Any],
    run_index: int,
    request_timeout: float,
) -> dict[str, Any]:
    messages = _build_messages(unit, prompt_snapshot, context, run_index)
    messages = truncate_messages_for_context(messages, model, base_parameters)
    payload = {
        "model": model.name if model else unit.model_name,
        "messages": messages,
        **base_parameters,
    }

    request_parameters = {
        key: value for key, value in payload.items() if key not in {"model", "messages"}
    }
    recorded_parameters = _build_recorded_parameters(unit, request_parameters)

    base_url = _resolve_base_url(provider)
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }

    try:
        sleep_lower, sleep_upper = REQUEST_SLEEP_RANGE
        if sleep_upper > 0:
            jitter = random.uniform(sleep_lower, sleep_upper)
            if jitter > 0:
                time.sleep(jitter)
    except Exception:  # pragma: no cover - 容错兜底
        pass

    start_time = time.perf_counter()
    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=request_timeout,
        )
    except httpx.HTTPError as exc:  # pragma: no cover - 网络异常兜底
        raise PromptTestExecutionError(f"调用外部 LLM 失败: {exc}") from exc

    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {"message": response.text}
        detail = _format_error_detail(error_payload)
        raise PromptTestExecutionError(
            f"LLM 请求失败 (HTTP {response.status_code}): {detail}",
            status_code=response.status_code,
        )

    try:
        payload_obj = response.json()
    except ValueError as exc:  # pragma: no cover - 响应解析异常
        raise PromptTestExecutionError("LLM 响应解析失败。") from exc

    elapsed = response.elapsed.total_seconds() * 1000 if response.elapsed else None
    latency_ms = (
        int(elapsed)
        if elapsed is not None
        else int((time.perf_counter() - start_time) * 1000)
    )
    latency_ms = max(latency_ms, 0)

    output_text = _extract_output(payload_obj)
    parsed_output = _try_parse_json(output_text)

    usage = (
        payload_obj.get("usage")
        if isinstance(payload_obj.get("usage"), Mapping)
        else {}
    )
    prompt_tokens = _safe_int(usage.get("prompt_tokens"))
    completion_tokens = _safe_int(usage.get("completion_tokens"))
    total_tokens = _safe_int(usage.get("total_tokens"))

    if (
        total_tokens is None
        and prompt_tokens is not None
        and completion_tokens is not None
    ):
        total_tokens = prompt_tokens + completion_tokens

    variables = _extract_variables(context)
    cost = calculate_model_call_cost(
        model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    return {
        "run_index": run_index,
        "messages": messages,
        "parameters": recorded_parameters or None,
        "variables": variables,
        "output_text": output_text,
        "parsed_output": parsed_output,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "input_cost": cost.input_cost,
        "output_cost": cost.output_cost,
        "total_cost": cost.total_cost,
        "cost_currency": cost.currency,
        "cost_pricing_snapshot": cost.pricing_snapshot,
        "latency_ms": latency_ms,
        "raw_response": payload_obj,
    }


def _resolve_context(
    template: Mapping[str, Any] | Sequence[Any], run_index: int
) -> dict[str, Any]:
    context: dict[str, Any] = {"run_index": run_index}

    if isinstance(template, Mapping):
        defaults = template.get("defaults")
        if isinstance(defaults, Mapping):
            context.update(
                {k: v for k, v in defaults.items() if not isinstance(k, (int, float))}
            )

        cases = template.get("cases")
        if isinstance(cases, Sequence) and cases:
            selected = cases[(run_index - 1) % len(cases)]
            if isinstance(selected, Mapping):
                context.update(selected)
            else:
                context["case"] = selected

        for key, value in template.items():
            if key in {"defaults", "cases"}:
                continue
            if isinstance(value, Mapping):
                continue
            if isinstance(value, Sequence) and not isinstance(
                value, (str, bytes, bytearray)
            ):
                continue
            context.setdefault(key, value)
    elif (
        isinstance(template, Sequence)
        and not isinstance(template, (str, bytes, bytearray))
        and template
    ):
        selected = template[(run_index - 1) % len(template)]
        if isinstance(selected, Mapping):
            context.update(selected)
        else:
            context["value"] = selected

    return context


def _count_variable_cases(template: Mapping[str, Any] | Sequence[Any] | None) -> int:
    if isinstance(template, Mapping):
        cases = template.get("cases")
        if isinstance(cases, Sequence) and not isinstance(
            cases, (str, bytes, bytearray)
        ):
            return len(cases)
        return 1 if template else 0
    if isinstance(template, Sequence) and not isinstance(
        template, (str, bytes, bytearray)
    ):
        return len(template)
    return 0


def _extract_variables(context: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(context, Mapping):
        return None
    sanitized: dict[str, Any] = {}
    for key, value in context.items():
        if key == "run_index":
            continue
        sanitized[key] = value
    return sanitized or None


def _build_messages(
    unit: PromptTestUnit,
    prompt_snapshot: str,
    context: Mapping[str, Any],
    run_index: int,
) -> list[dict[str, Any]]:
    conversation: Any = None
    if isinstance(unit.parameters, Mapping):
        conversation = unit.parameters.get("conversation") or unit.parameters.get(
            "messages"
        )

    messages: list[dict[str, Any]] = []
    if isinstance(conversation, Sequence):
        for item in conversation:
            if not isinstance(item, Mapping):
                continue
            role = str(item.get("role", "")).strip() or "user"
            content = _format_text(item.get("content"), context, run_index)
            if content is None:
                continue
            messages.append({"role": role, "content": content})

    snapshot_message: dict[str, Any] | None = None
    prompt_message = _format_text(prompt_snapshot, context, run_index)
    if prompt_message:
        if not messages:
            snapshot_message = {"role": "user", "content": prompt_message}
            messages.append(snapshot_message)
        elif not any(msg["role"] == "system" for msg in messages):
            snapshot_message = {"role": "user", "content": prompt_message}
            messages.insert(0, snapshot_message)

    user_template = unit.prompt_template or context.get("user_prompt")
    user_message = _format_text(user_template, context, run_index)

    has_user = any(
        msg.get("role") == "user"
        and (snapshot_message is None or msg is not snapshot_message)
        for msg in messages
    )

    if user_message and not has_user:
        messages.append({"role": "user", "content": user_message})

    if not messages:
        messages.append(
            {
                "role": "user",
                "content": f"请生成第 {run_index} 次响应。",
            }
        )

    return messages


def _format_text(
    template: Any, context: Mapping[str, Any], run_index: int
) -> str | None:
    if template is None:
        return None
    if not isinstance(template, str):
        return str(template)
    try:
        replaced = template.replace("{{run_index}}", str(run_index))
        return replaced.format(**context)
    except Exception:
        return template.replace("{{run_index}}", str(run_index))


def _extract_output(payload_obj: Mapping[str, Any]) -> str:
    choices = payload_obj.get("choices")
    if isinstance(choices, Sequence) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping) and isinstance(message.get("content"), str):
                return message["content"]
            text_value = first.get("text")
            if isinstance(text_value, str):
                return text_value
    return ""


def _safe_int(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    try:
        if isinstance(value, str) and value.strip():
            return int(float(value))
    except Exception:  # pragma: no cover - 容错
        return None
    return None


def _aggregate_metrics(
    *,
    latencies: Sequence[int],
    tokens: Sequence[int],
    total_rounds: int,
    json_success: int,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "rounds": total_rounds,
    }

    if latencies:
        metrics["avg_latency_ms"] = statistics.fmean(latencies)
        metrics["max_latency_ms"] = max(latencies)
        metrics["min_latency_ms"] = min(latencies)

    if tokens:
        metrics["avg_total_tokens"] = statistics.fmean(tokens)
        metrics["max_total_tokens"] = max(tokens)
        metrics["min_total_tokens"] = min(tokens)

    if total_rounds:
        metrics["json_success_rate"] = round(json_success / total_rounds, 4)

    return metrics


def _build_usage_log(
    *,
    provider: LLMProvider,
    model: LLMModel | None,
    unit: PromptTestUnit,
    run_record: Mapping[str, Any],
) -> LLMUsageLog:
    prompt_version = unit.prompt_version
    prompt_id: int | None = None
    prompt_version_id = unit.prompt_version_id

    if (
        prompt_version is not None
        and getattr(prompt_version, "prompt_id", None) is not None
    ):
        prompt_id = prompt_version.prompt_id
    else:
        task = getattr(unit, "task", None)
        task_prompt_version = getattr(task, "prompt_version", None) if task else None
        if prompt_version_id is None and task is not None:
            prompt_version_id = getattr(task, "prompt_version_id", None)
        if (
            task_prompt_version is not None
            and getattr(task_prompt_version, "prompt_id", None) is not None
        ):
            prompt_id = task_prompt_version.prompt_id

    def _safe_int_value(key: str) -> int | None:
        value = run_record.get(key)
        if isinstance(value, (int, float)):
            return int(value)
        return None

    latency_value = _safe_int_value("latency_ms")

    log = LLMUsageLog(
        provider_id=provider.id,
        model_id=model.id if model else None,
        model_name=model.name if model else unit.model_name,
        source="prompt_test",
        prompt_id=prompt_id,
        prompt_version_id=prompt_version_id,
        messages=run_record.get("messages"),
        parameters=run_record.get("parameters"),
        response_text=run_record.get("output_text"),
        temperature=unit.temperature,
        latency_ms=latency_value,
        prompt_tokens=_safe_int_value("prompt_tokens"),
        completion_tokens=_safe_int_value("completion_tokens"),
        total_tokens=_safe_int_value("total_tokens"),
    )
    apply_cost_to_usage_log(log, model)
    return log


def _resolve_base_url(provider: LLMProvider) -> str:
    defaults = get_provider_defaults(provider.provider_key)
    base_url = provider.base_url or (defaults.base_url if defaults else None)
    if not base_url:
        raise PromptTestExecutionError("模型提供者缺少基础 URL 配置。")
    return base_url.rstrip("/")


__all__ = ["execute_prompt_test_experiment", "PromptTestExecutionError"]
