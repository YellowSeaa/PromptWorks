from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from app.models.llm_provider import LLMModel

APPROX_CHARS_PER_TOKEN = 4
_OUTPUT_TOKEN_KEYS = ("max_tokens", "max_completion_tokens")


def truncate_messages_for_context(
    messages: Sequence[Mapping[str, Any]],
    model: LLMModel | None,
    parameters: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """按模型上下文长度近似截断消息，优先保留系统指令和靠后的内容。"""

    normalized = [dict(message) for message in messages]
    context_length = _resolve_context_length(model)
    if context_length is None or not normalized:
        return normalized

    reserved_tokens = _resolve_reserved_output_tokens(parameters)
    prompt_token_budget = max(1, context_length - reserved_tokens)
    char_budget = max(1, prompt_token_budget * APPROX_CHARS_PER_TOKEN)

    if _estimate_messages_chars(normalized) <= char_budget:
        return normalized

    return _truncate_by_priority(normalized, char_budget)


def _resolve_context_length(model: LLMModel | None) -> int | None:
    value = getattr(model, "context_length", None)
    if isinstance(value, int) and value > 0:
        return value
    return None


def _resolve_reserved_output_tokens(parameters: Mapping[str, Any] | None) -> int:
    if not isinstance(parameters, Mapping):
        return 0
    for key in _OUTPUT_TOKEN_KEYS:
        value = parameters.get(key)
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, float) and value > 0:
            return math.ceil(value)
        if isinstance(value, str) and value.strip():
            try:
                parsed = int(float(value))
            except ValueError:
                continue
            if parsed > 0:
                return parsed
    return 0


def _estimate_messages_chars(messages: Sequence[Mapping[str, Any]]) -> int:
    total = 0
    for message in messages:
        total += len(str(message.get("role", "")))
        total += len(_content_to_text(message.get("content")))
    return total


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        return str(content)


def _truncate_by_priority(
    messages: Sequence[Mapping[str, Any]], char_budget: int
) -> list[dict[str, Any]]:
    result = [dict(message) for message in messages]
    remaining = char_budget
    content_by_index = {
        index: _content_to_text(message.get("content"))
        for index, message in enumerate(result)
    }
    preserved: dict[int, str] = {}

    system_indexes = [
        index
        for index, message in enumerate(result)
        if str(message.get("role", "")).strip().lower() == "system"
    ]
    other_indexes = [
        index for index in range(len(result)) if index not in system_indexes
    ]
    priority_indexes = [*system_indexes, *reversed(other_indexes)]

    for index in priority_indexes:
        if remaining <= 0:
            preserved[index] = ""
            continue
        content = content_by_index[index]
        if len(content) <= remaining:
            preserved[index] = content
            remaining -= len(content)
        else:
            preserved[index] = content[-remaining:]
            remaining = 0

    for index, message in enumerate(result):
        message["content"] = preserved.get(index, "")

    return result


__all__ = ["truncate_messages_for_context"]
