from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.llm_provider import LLMProvider
from app.models.usage import LLMUsageLog
from app.services import usage_dashboard


def _create_provider(db_session) -> LLMProvider:
    provider = LLMProvider(
        provider_name="Analytics",
        api_key="secret",
        is_custom=True,
        base_url="https://analytics.llm/api",
    )
    db_session.add(provider)
    db_session.commit()
    return provider


def _add_usage(
    db_session,
    *,
    provider_id: int | None,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    created_at: datetime,
    total_cost: float | None = None,
    cost_currency: str | None = "CNY",
) -> LLMUsageLog:
    log = LLMUsageLog(
        provider_id=provider_id,
        model_id=None,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        latency_ms=100,
        total_cost=total_cost,
        cost_currency=cost_currency,
        created_at=created_at,
    )
    db_session.add(log)
    db_session.commit()
    return log


def test_calculate_usage_overview_with_data(db_session):
    assert usage_dashboard.calculate_usage_overview(db_session) is None

    provider = _create_provider(db_session)
    ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    _add_usage(
        db_session,
        provider_id=provider.id,
        model_name="model-a",
        prompt_tokens=10,
        completion_tokens=20,
        total_cost=0.216,
        created_at=ts,
    )
    overview = usage_dashboard.calculate_usage_overview(db_session)
    assert overview == usage_dashboard.UsageOverviewTotals(
        total_tokens=30,
        input_tokens=10,
        output_tokens=20,
        call_count=1,
        total_cost=0.216,
        cost_currency="CNY",
    )

    filtered = usage_dashboard.calculate_usage_overview(
        db_session,
        start_date=ts.date(),
        end_date=ts.date(),
    )
    assert filtered.total_tokens == 30
    assert filtered.total_cost == 0.216


def test_aggregate_usage_by_model_groups_results(db_session):
    provider = _create_provider(db_session)
    base_time = datetime(2024, 2, 1, tzinfo=timezone.utc)
    _add_usage(
        db_session,
        provider_id=provider.id,
        model_name="model-a",
        prompt_tokens=5,
        completion_tokens=5,
        total_cost=0.5,
        created_at=base_time,
    )
    _add_usage(
        db_session,
        provider_id=provider.id,
        model_name="model-b",
        prompt_tokens=2,
        completion_tokens=1,
        total_cost=0.9,
        created_at=base_time,
    )
    summaries = usage_dashboard.aggregate_usage_by_model(db_session)
    assert [item.model_name for item in summaries] == ["model-b", "model-a"]
    assert summaries[0].total_cost == 0.9
    assert summaries[0].provider_name == "Analytics"


def test_get_model_usage_timeseries_handles_strings(db_session):
    provider = _create_provider(db_session)
    first_day = datetime(2024, 3, 1, 10, tzinfo=timezone.utc)
    second_day = datetime(2024, 3, 2, 11, tzinfo=timezone.utc)
    _add_usage(
        db_session,
        provider_id=provider.id,
        model_name="model-timeseries",
        prompt_tokens=3,
        completion_tokens=4,
        total_cost=0.7,
        created_at=first_day,
    )
    _add_usage(
        db_session,
        provider_id=None,
        model_name="model-timeseries",
        prompt_tokens=1,
        completion_tokens=2,
        total_cost=0.2,
        created_at=second_day,
    )

    with_provider = usage_dashboard.get_model_usage_timeseries(
        db_session,
        provider_id=provider.id,
        model_name="model-timeseries",
    )
    assert len(with_provider) == 1
    assert with_provider[0].input_tokens == 3
    assert with_provider[0].total_cost == 0.7

    without_provider = usage_dashboard.get_model_usage_timeseries(
        db_session,
        provider_id=None,
        model_name="model-timeseries",
    )
    assert len(without_provider) == 1
    assert without_provider[0].output_tokens == 2


def test_usage_queries_respect_date_filters(db_session):
    provider = _create_provider(db_session)
    early = datetime(2024, 4, 1, tzinfo=timezone.utc)
    late = datetime(2024, 4, 3, tzinfo=timezone.utc)
    first = _add_usage(
        db_session,
        provider_id=provider.id,
        model_name="model-filters",
        prompt_tokens=4,
        completion_tokens=4,
        created_at=early,
    )
    _add_usage(
        db_session,
        provider_id=provider.id,
        model_name="model-filters",
        prompt_tokens=2,
        completion_tokens=2,
        created_at=late,
    )

    totals = usage_dashboard.calculate_usage_overview(
        db_session,
        start_date=late.date(),
    )
    assert totals.total_tokens == 4

    summaries = usage_dashboard.aggregate_usage_by_model(
        db_session,
        end_date=early.date(),
    )
    assert summaries[0].total_tokens == 8

    timeseries = usage_dashboard.get_model_usage_timeseries(
        db_session,
        provider_id=provider.id,
        model_name="model-filters",
        end_date=early.date(),
    )
    assert len(timeseries) == 1
    assert timeseries[0].call_count == 1

    remaining = db_session.scalars(
        select(LLMUsageLog).where(LLMUsageLog.id == first.id)
    ).one()
    assert remaining.prompt_tokens == 4
