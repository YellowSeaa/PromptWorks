from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.models.llm_provider import LLMModel
from app.models.usage import LLMUsageLog

DEFAULT_COST_DISPLAY_CURRENCY = "CNY"


@dataclass(frozen=True, slots=True)
class ModelCallCost:
    input_cost: float
    output_cost: float
    total_cost: float
    currency: str
    pricing_snapshot: dict[str, Any]


def calculate_model_call_cost(
    model: LLMModel | None,
    *,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
) -> ModelCallCost:
    """按模型成本配置计算单次调用费用，并返回可落库的价格快照。"""

    currency = _normalize_currency(
        getattr(model, "cost_display_currency", None), DEFAULT_COST_DISPLAY_CURRENCY
    )
    if model is None:
        return _zero_cost(currency, reason="model_missing")

    pricing_unit = _positive_int(getattr(model, "cost_pricing_unit", None), 1_000_000)
    exchange_rate = _positive_float(getattr(model, "cost_exchange_rate", None), 1.0)
    source_currency = _normalize_currency(getattr(model, "cost_currency", None), "USD")
    display_currency = _normalize_currency(
        getattr(model, "cost_display_currency", None), DEFAULT_COST_DISPLAY_CURRENCY
    )
    tier = _match_cost_tier(model, total_tokens)
    input_rate = _rate_from_tier_or_model(tier, model, "input_per_unit")
    output_rate = _rate_from_tier_or_model(tier, model, "output_per_unit")

    if input_rate is None and output_rate is None:
        return _zero_cost(
            display_currency,
            configured=False,
            reason="pricing_missing",
            pricing_unit=pricing_unit,
            exchange_rate=exchange_rate,
            source_currency=source_currency,
        )

    input_tokens = max(0, int(prompt_tokens or 0))
    output_tokens = max(0, int(completion_tokens or 0))
    input_cost = (input_tokens / pricing_unit) * float(input_rate or 0) * exchange_rate
    output_cost = (
        (output_tokens / pricing_unit) * float(output_rate or 0) * exchange_rate
    )
    total_cost = input_cost + output_cost
    snapshot = {
        "configured": True,
        "source_currency": source_currency,
        "display_currency": display_currency,
        "exchange_rate": exchange_rate,
        "pricing_unit": pricing_unit,
        "input_per_unit": input_rate,
        "output_per_unit": output_rate,
        "matched_tier": tier,
    }
    return ModelCallCost(
        input_cost=round(input_cost, 8),
        output_cost=round(output_cost, 8),
        total_cost=round(total_cost, 8),
        currency=display_currency,
        pricing_snapshot=snapshot,
    )


def apply_cost_to_usage_log(log: LLMUsageLog, model: LLMModel | None) -> LLMUsageLog:
    cost = calculate_model_call_cost(
        model,
        prompt_tokens=log.prompt_tokens,
        completion_tokens=log.completion_tokens,
        total_tokens=log.total_tokens,
    )
    log.input_cost = cost.input_cost
    log.output_cost = cost.output_cost
    log.total_cost = cost.total_cost
    log.cost_currency = cost.currency
    log.cost_pricing_snapshot = cost.pricing_snapshot
    return log


def _zero_cost(
    currency: str,
    *,
    configured: bool = False,
    reason: str,
    pricing_unit: int | None = None,
    exchange_rate: float | None = None,
    source_currency: str | None = None,
) -> ModelCallCost:
    snapshot: dict[str, Any] = {"configured": configured, "reason": reason}
    if pricing_unit is not None:
        snapshot["pricing_unit"] = pricing_unit
    if exchange_rate is not None:
        snapshot["exchange_rate"] = exchange_rate
    if source_currency is not None:
        snapshot["source_currency"] = source_currency
    return ModelCallCost(
        input_cost=0,
        output_cost=0,
        total_cost=0,
        currency=currency,
        pricing_snapshot=snapshot,
    )


def _match_cost_tier(
    model: LLMModel, total_tokens: int | None
) -> dict[str, Any] | None:
    tiers = getattr(model, "cost_tiers", None)
    if not isinstance(tiers, list) or not tiers:
        return None

    context_tokens = _positive_int(
        getattr(model, "context_length", None), _positive_int(total_tokens, 0)
    )
    normalized: list[dict[str, Any]] = []
    for raw_tier in tiers:
        if not isinstance(raw_tier, Mapping):
            continue
        limit = _positive_int(raw_tier.get("up_to_context_tokens"), 0)
        if limit <= 0:
            continue
        normalized.append(
            {
                "up_to_context_tokens": limit,
                "input_per_unit": _optional_float(raw_tier.get("input_per_unit")),
                "output_per_unit": _optional_float(raw_tier.get("output_per_unit")),
            }
        )
    if not normalized:
        return None
    normalized.sort(key=lambda item: int(item["up_to_context_tokens"]))
    for tier in normalized:
        if context_tokens <= int(tier["up_to_context_tokens"]):
            return tier
    return normalized[-1]


def _rate_from_tier_or_model(
    tier: Mapping[str, Any] | None, model: LLMModel, key: str
) -> float | None:
    if tier is not None:
        tier_value = _optional_float(tier.get(key))
        if tier_value is not None:
            return tier_value
    model_attr = (
        "cost_input_per_unit" if key == "input_per_unit" else "cost_output_per_unit"
    )
    return _optional_float(getattr(model, model_attr, None))


def _normalize_currency(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip().upper()
    return text or default


def _positive_int(value: Any, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _positive_float(value: Any, default: float) -> float:
    number = _optional_float(value)
    if number is None or number <= 0:
        return default
    return number


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number if number >= 0 else None


__all__ = [
    "DEFAULT_COST_DISPLAY_CURRENCY",
    "ModelCallCost",
    "apply_cost_to_usage_log",
    "calculate_model_call_cost",
]
