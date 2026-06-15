from __future__ import annotations

import pytest

from app.models.llm_provider import LLMModel
from app.services.model_costs import calculate_model_call_cost


def test_calculate_model_call_cost_uses_tier_and_exchange_rate() -> None:
    model = LLMModel(
        name="chat-cost",
        context_length=128_000,
        cost_currency="USD",
        cost_display_currency="CNY",
        cost_exchange_rate=7.2,
        cost_pricing_unit=1_000_000,
        cost_input_per_unit=2.0,
        cost_output_per_unit=8.0,
        cost_tiers=[
            {
                "up_to_context_tokens": 32_000,
                "input_per_unit": 1.0,
                "output_per_unit": 3.0,
            },
            {
                "up_to_context_tokens": 128_000,
                "input_per_unit": 2.0,
                "output_per_unit": 8.0,
            },
        ],
    )

    cost = calculate_model_call_cost(
        model,
        prompt_tokens=1_000_000,
        completion_tokens=500_000,
        total_tokens=1_500_000,
    )

    assert cost.input_cost == pytest.approx(14.4)
    assert cost.output_cost == pytest.approx(28.8)
    assert cost.total_cost == pytest.approx(43.2)
    assert cost.currency == "CNY"
    assert cost.pricing_snapshot["matched_tier"]["up_to_context_tokens"] == 128_000


def test_calculate_model_call_cost_falls_back_to_usage_length_for_tier() -> None:
    model = LLMModel(
        name="chat-short-context",
        cost_currency="USD",
        cost_display_currency="USD",
        cost_exchange_rate=1,
        cost_pricing_unit=1_000,
        cost_input_per_unit=1.0,
        cost_output_per_unit=2.0,
        cost_tiers=[
            {
                "up_to_context_tokens": 1_000,
                "input_per_unit": 1.0,
                "output_per_unit": 2.0,
            },
            {
                "up_to_context_tokens": 8_000,
                "input_per_unit": 1.5,
                "output_per_unit": 3.0,
            },
        ],
    )

    cost = calculate_model_call_cost(
        model,
        prompt_tokens=2_000,
        completion_tokens=1_000,
        total_tokens=3_000,
    )

    assert cost.input_cost == pytest.approx(3.0)
    assert cost.output_cost == pytest.approx(3.0)
    assert cost.total_cost == pytest.approx(6.0)
    assert cost.pricing_snapshot["matched_tier"]["up_to_context_tokens"] == 8_000


def test_calculate_model_call_cost_returns_zero_without_pricing() -> None:
    cost = calculate_model_call_cost(
        LLMModel(name="free-model"),
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
    )

    assert cost.input_cost == 0
    assert cost.output_cost == 0
    assert cost.total_cost == 0
    assert cost.currency == "CNY"
    assert cost.pricing_snapshot["configured"] is False
