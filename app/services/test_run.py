from __future__ import annotations

import json
import random
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette import status

from app.core.llm_provider_registry import get_provider_defaults
from app.models.llm_provider import LLMModel, LLMProvider
from app.models.result import Result
from app.models.test_run import TestRun, TestRunStatus
from app.models.usage import LLMUsageLog
from app.services.system_settings import (
    DEFAULT_TEST_TASK_TIMEOUT,
    get_testing_timeout_config,
)

DEFAULT_TEST_TIMEOUT = DEFAULT_TEST_TASK_TIMEOUT
DEFAULT_CONCURRENCY_LIMIT = 5
REQUEST_SLEEP_RANGE = (0.05, 0.2)

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


@dataclass(frozen=True)
class RunRequestContext:
    test_run_id: int
    model_name: str
    prompt_id: int | None
    prompt_version_id: int | None
    timeout_seconds: float


class TestRunExecutionError(Exception):
    """执行测试任务过程中出现的业务异常。"""

    __test__ = False

    def __init__(
        self, message: str, *, status_code: int = status.HTTP_400_BAD_REQUEST
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


def execute_test_run(db: Session, test_run: TestRun) -> TestRun:
    """调用外部 LLM 完成测试任务，并记录结果与用量。"""

    if test_run.status not in {TestRunStatus.PENDING, TestRunStatus.RUNNING}:
        return test_run

    provider, model = _resolve_provider_and_model(db, test_run)

    prompt_version = test_run.prompt_version
    if not prompt_version:
        raise TestRunExecutionError("测试任务缺少关联的 Prompt 版本。")
    prompt_snapshot = prompt_version.content

    schema_data = _ensure_mapping(test_run.schema)
    schema_data.pop("last_error", None)
    schema_data.pop("last_error_status", None)
    schema_data.setdefault("prompt_snapshot", prompt_snapshot)
    schema_data.setdefault("llm_provider_id", provider.id)
    schema_data.setdefault("llm_provider_name", provider.provider_name)
    if model:
        schema_data.setdefault("llm_model_id", model.id)
    test_run.schema = schema_data

    parameters_template = _build_parameters(test_run, schema_data)
    base_url = _resolve_base_url(provider)
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }

    test_run.status = TestRunStatus.RUNNING
    db.flush()

    timeout_config = get_testing_timeout_config(db)
    request_timeout = float(timeout_config.test_task_timeout or DEFAULT_TEST_TIMEOUT)

    context = RunRequestContext(
        test_run_id=test_run.id,
        model_name=test_run.model_name,
        prompt_id=prompt_version.prompt_id,
        prompt_version_id=test_run.prompt_version_id,
        timeout_seconds=request_timeout,
    )

    concurrency_limit = DEFAULT_CONCURRENCY_LIMIT
    if model and isinstance(model.concurrency_limit, int):
        concurrency_limit = max(1, model.concurrency_limit)

    def _execute_single(run_index: int) -> tuple[int, Result, LLMUsageLog]:
        messages = _build_messages(schema_data, prompt_snapshot, run_index)
        payload: dict[str, Any] = dict(parameters_template)
        payload["model"] = model.name if model else test_run.model_name
        payload["messages"] = messages

        result, usage_log = _invoke_llm_once(
            provider=provider,
            model=model,
            base_url=base_url,
            headers=headers,
            payload=payload,
            context=context,
        )

        result.test_run_id = context.test_run_id
        result.run_index = run_index
        return run_index, result, usage_log

    run_indices = range(1, test_run.repetitions + 1)
    error_message: str | None = None
    error_status_code: int | None = None

    worker_count = max(1, min(concurrency_limit, test_run.repetitions))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(_execute_single, index): index for index in run_indices
        }
        for future in as_completed(future_map):
            try:
                _, result_obj, usage_obj = future.result()
            except TestRunExecutionError as exc:
                if error_message is None:
                    error_message = str(exc)
                    error_status_code = getattr(exc, "status_code", None)
            except Exception as exc:  # pragma: no cover - 防御性
                if error_message is None:
                    error_message = f"执行测试任务失败: {exc}"
                    error_status_code = status.HTTP_502_BAD_GATEWAY
            else:
                _persist_run_artifacts(db, result_obj, usage_obj)

    if error_message:
        test_run.status = TestRunStatus.FAILED
        test_run.last_error = error_message
        if error_status_code is not None:
            current_schema = _ensure_mapping(test_run.schema)
            current_schema["last_error_status"] = error_status_code
            test_run.schema = current_schema
    else:
        test_run.status = TestRunStatus.COMPLETED
        test_run.last_error = None
        current_schema = _ensure_mapping(test_run.schema)
        if current_schema:
            current_schema.pop("last_error_status", None)
            test_run.schema = current_schema or None

    db.flush()
    return test_run


def ensure_completed(db: Session, runs: Sequence[TestRun]) -> None:
    for run in runs:
        execute_test_run(db, run)
    db.flush()


def _resolve_provider_and_model(
    db: Session, test_run: TestRun
) -> tuple[LLMProvider, LLMModel | None]:
    schema_data = _ensure_mapping(test_run.schema)

    provider: LLMProvider | None = None
    model: LLMModel | None = None

    provider_id = schema_data.get("llm_provider_id") or schema_data.get("provider_id")
    model_id = schema_data.get("llm_model_id") or schema_data.get("model_id")

    if isinstance(provider_id, int):
        provider = db.get(LLMProvider, provider_id)
    elif isinstance(provider_id, str) and provider_id.isdigit():
        provider = db.get(LLMProvider, int(provider_id))

    if provider and isinstance(model_id, int):
        model = db.get(LLMModel, model_id)
    elif provider and isinstance(model_id, str) and model_id.isdigit():
        model = db.get(LLMModel, int(model_id))

    if model and provider and model.provider_id != provider.id:
        model = None

    if provider is None and test_run.model_version:
        provider = db.scalar(
            select(LLMProvider).where(
                LLMProvider.provider_name == test_run.model_version
            )
        )

    if provider is None and isinstance(
        schema_key := schema_data.get("provider_key"), str
    ):
        provider = db.scalar(
            select(LLMProvider).where(LLMProvider.provider_key == schema_key)
        )

    if provider is None:
        stmt = (
            select(LLMProvider, LLMModel)
            .join(LLMModel, LLMModel.provider_id == LLMProvider.id)
            .where(LLMModel.name == test_run.model_name)
        )
        record = db.execute(stmt).first()
        if record:
            provider, model = record

    if provider is None:
        raise TestRunExecutionError(
            "未找到可用的模型提供者配置。", status_code=status.HTTP_404_NOT_FOUND
        )

    if model is None:
        model = db.scalar(
            select(LLMModel).where(
                LLMModel.provider_id == provider.id,
                LLMModel.name == test_run.model_name,
            )
        )

    return provider, model


def _resolve_base_url(provider: LLMProvider) -> str:
    defaults = get_provider_defaults(provider.provider_key)
    base_url = provider.base_url or (defaults.base_url if defaults else None)
    if not base_url:
        raise TestRunExecutionError("模型提供者缺少基础 URL 配置。")
    return base_url.rstrip("/")


def _ensure_mapping(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return dict(raw)
    return {}


def _build_parameters(
    test_run: TestRun, schema_data: Mapping[str, Any]
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "temperature": test_run.temperature,
    }
    if test_run.top_p is not None:
        parameters["top_p"] = test_run.top_p

    for key in _NESTED_PARAMETER_KEYS:
        nested = schema_data.get(key)
        if isinstance(nested, Mapping):
            parameters.update(dict(nested))

    for key in _KNOWN_PARAMETER_KEYS:
        if key in schema_data and schema_data[key] is not None:
            parameters[key] = schema_data[key]

    return parameters


def _render_content(content: Any, run_index: int) -> Any:
    if isinstance(content, str):
        return content.replace("{{run_index}}", str(run_index))
    return content


def _build_messages(
    schema_data: Mapping[str, Any], prompt_snapshot: str, run_index: int
) -> list[dict[str, Any]]:
    raw_conversation = schema_data.get("conversation")
    messages: list[dict[str, Any]] = []

    if isinstance(raw_conversation, Sequence):
        for item in raw_conversation:
            if not isinstance(item, Mapping):
                continue
            role = str(item.get("role", "")).strip()
            content = _render_content(item.get("content"), run_index)
            if not role or content is None:
                continue
            messages.append({"role": role, "content": content})

    snapshot_message: dict[str, Any] | None = None
    if prompt_snapshot:
        if not messages:
            snapshot_message = {"role": "user", "content": prompt_snapshot}
            messages.append(snapshot_message)
        elif not any(message.get("role") == "system" for message in messages):
            snapshot_message = {"role": "user", "content": prompt_snapshot}
            messages.insert(0, snapshot_message)

    has_user = any(
        message.get("role") == "user"
        and (snapshot_message is None or message is not snapshot_message)
        for message in messages
    )
    if not has_user:
        user_inputs = schema_data.get("inputs") or schema_data.get("test_inputs")
        user_message: str
        if isinstance(user_inputs, Sequence) and user_inputs:
            index = (run_index - 1) % len(user_inputs)
            candidate = user_inputs[index]
            user_message = (
                _render_content(candidate, run_index)
                if isinstance(candidate, str)
                else str(candidate)
            )
        else:
            user_message = f"请根据提示生成第 {run_index} 次响应。"
        messages.append({"role": "user", "content": user_message})

    normalized: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role", "")).strip() or "user"
        content = message.get("content")
        normalized.append({"role": role, "content": content})
    return normalized


def _invoke_llm_once(
    *,
    provider: LLMProvider,
    model: LLMModel | None,
    base_url: str,
    headers: Mapping[str, str],
    payload: dict[str, Any],
    context: RunRequestContext,
) -> tuple[Result, LLMUsageLog]:
    url = f"{base_url}/chat/completions"
    start_time = time.perf_counter()

    try:
        sleep_lower, sleep_upper = REQUEST_SLEEP_RANGE
        if sleep_upper > 0:
            jitter = random.uniform(sleep_lower, sleep_upper)
            if jitter > 0:
                time.sleep(jitter)
    except Exception:  # pragma: no cover - 容错
        pass

    try:
        timeout_value = getattr(context, "timeout_seconds", DEFAULT_TEST_TIMEOUT)
        response = httpx.post(
            url, headers=dict(headers), json=payload, timeout=timeout_value
        )
    except httpx.HTTPError as exc:  # pragma: no cover - 网络异常场景
        raise TestRunExecutionError(
            f"调用外部 LLM 失败: {exc}", status_code=status.HTTP_502_BAD_GATEWAY
        ) from exc

    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {"message": response.text}
        detail_text = _format_error_detail(error_payload)
        raise TestRunExecutionError(
            f"LLM 请求失败 (HTTP {response.status_code}): {detail_text}",
            status_code=response.status_code,
        ) from None

    try:
        payload_obj = response.json()
    except ValueError as exc:  # pragma: no cover - 防御性
        raise TestRunExecutionError(
            "LLM 响应解析失败。", status_code=status.HTTP_502_BAD_GATEWAY
        ) from exc

    choices = payload_obj.get("choices")
    output_text = ""
    if isinstance(choices, Sequence) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping) and isinstance(message.get("content"), str):
                output_text = message["content"]
            elif isinstance(first.get("text"), str):
                output_text = str(first["text"])
    output_text = str(output_text)

    parsed_output = _try_parse_json(output_text)

    usage = (
        payload_obj.get("usage")
        if isinstance(payload_obj.get("usage"), Mapping)
        else {}
    )
    prompt_tokens = usage.get("prompt_tokens") if isinstance(usage, Mapping) else None
    completion_tokens = (
        usage.get("completion_tokens") if isinstance(usage, Mapping) else None
    )
    total_tokens = usage.get("total_tokens") if isinstance(usage, Mapping) else None

    if total_tokens is None and any(
        isinstance(value, (int, float)) for value in (prompt_tokens, completion_tokens)
    ):
        total_tokens = 0
        if isinstance(prompt_tokens, (int, float)):
            total_tokens += int(prompt_tokens)
        if isinstance(completion_tokens, (int, float)):
            total_tokens += int(completion_tokens)

    elapsed_delta = getattr(response, "elapsed", None)
    if elapsed_delta is not None:
        latency_ms = int(elapsed_delta.total_seconds() * 1000)
    else:
        latency_ms = int((time.perf_counter() - start_time) * 1000)

    latency_ms = max(latency_ms, 0)

    result = Result(
        output=output_text,
        parsed_output=parsed_output,
        tokens_used=int(total_tokens)
        if isinstance(total_tokens, (int, float))
        else None,
        latency_ms=latency_ms,
    )

    request_parameters = {
        key: value for key, value in payload.items() if key not in {"model", "messages"}
    }

    usage_log = LLMUsageLog(
        provider_id=provider.id,
        model_id=model.id if model else None,
        model_name=model.name if model else payload.get("model", context.model_name),
        source="test_run",
        prompt_id=context.prompt_id,
        prompt_version_id=context.prompt_version_id,
        messages=payload.get("messages"),
        parameters=request_parameters or None,
        response_text=output_text or None,
        temperature=request_parameters.get("temperature"),
        latency_ms=latency_ms,
        prompt_tokens=int(prompt_tokens)
        if isinstance(prompt_tokens, (int, float))
        else None,
        completion_tokens=int(completion_tokens)
        if isinstance(completion_tokens, (int, float))
        else None,
        total_tokens=int(total_tokens)
        if isinstance(total_tokens, (int, float))
        else None,
    )

    return result, usage_log


def _format_error_detail(payload: Any) -> str:
    if isinstance(payload, Mapping):
        error_obj = payload.get("error")
        if isinstance(error_obj, Mapping):
            message_parts: list[str] = []
            code = error_obj.get("code")
            if isinstance(code, str) and code.strip():
                message_parts.append(code.strip())
            error_type = error_obj.get("type")
            if isinstance(error_type, str) and error_type.strip():
                message_parts.append(error_type.strip())
            message = error_obj.get("message")
            if isinstance(message, str) and message.strip():
                prefix = " | ".join(message_parts)
                return f"{prefix}: {message.strip()}" if prefix else message.strip()
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        try:
            return json.dumps(payload, ensure_ascii=False)
        except Exception:  # pragma: no cover - 容错
            return str(payload)
    return str(payload)


def _try_parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None


def _persist_run_artifacts(db: Session, result: Result, usage_log: LLMUsageLog) -> None:
    db.add(result)
    db.add(usage_log)
    db.flush()


__all__ = ["execute_test_run", "ensure_completed", "TestRunExecutionError"]
