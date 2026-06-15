from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.llm_provider import LLMProvider
from app.models.usage import LLMUsageLog


@dataclass(slots=True)
class UsageOverviewTotals:
    total_tokens: int
    input_tokens: int
    output_tokens: int
    call_count: int
    total_cost: float
    cost_currency: str


@dataclass(slots=True)
class ModelUsageSummary:
    provider_id: int | None
    model_name: str
    provider_name: str | None
    total_tokens: int
    input_tokens: int
    output_tokens: int
    call_count: int
    total_cost: float
    cost_currency: str


@dataclass(slots=True)
class UsageTimeseriesPoint:
    date: date
    input_tokens: int
    output_tokens: int
    call_count: int
    total_cost: float
    cost_currency: str


def _prompt_tokens_expr():
    return func.coalesce(LLMUsageLog.prompt_tokens, 0)


def _completion_tokens_expr():
    return func.coalesce(LLMUsageLog.completion_tokens, 0)


def _total_tokens_expr():
    prompt_expr = _prompt_tokens_expr()
    completion_expr = _completion_tokens_expr()
    return func.coalesce(LLMUsageLog.total_tokens, prompt_expr + completion_expr, 0)


def _total_cost_expr():
    return func.coalesce(LLMUsageLog.total_cost, 0.0)


def _cost_currency_expr():
    return func.coalesce(LLMUsageLog.cost_currency, "CNY")


def _apply_date_filters(stmt: Select, start_date: date | None, end_date: date | None):
    if start_date:
        stmt = stmt.where(func.date(LLMUsageLog.created_at) >= start_date)
    if end_date:
        stmt = stmt.where(func.date(LLMUsageLog.created_at) <= end_date)
    return stmt


def calculate_usage_overview(
    db: Session, *, start_date: date | None = None, end_date: date | None = None
) -> UsageOverviewTotals | None:
    total_tokens = func.sum(_total_tokens_expr()).label("total_tokens")
    input_tokens = func.sum(_prompt_tokens_expr()).label("input_tokens")
    output_tokens = func.sum(_completion_tokens_expr()).label("output_tokens")
    call_count = func.count(LLMUsageLog.id).label("call_count")
    total_cost = func.sum(_total_cost_expr()).label("total_cost")
    cost_currency = func.max(_cost_currency_expr()).label("cost_currency")

    stmt = select(
        total_tokens, input_tokens, output_tokens, call_count, total_cost, cost_currency
    )
    stmt = _apply_date_filters(stmt, start_date, end_date)

    row = db.execute(stmt).one()
    data = row._mapping

    total = int(data.get("total_tokens") or 0)
    inputs = int(data.get("input_tokens") or 0)
    outputs = int(data.get("output_tokens") or 0)
    calls = int(data.get("call_count") or 0)
    cost = float(data.get("total_cost") or 0)
    currency = str(data.get("cost_currency") or "CNY")

    if total == 0 and inputs == 0 and outputs == 0 and calls == 0:
        return None

    return UsageOverviewTotals(
        total_tokens=total,
        input_tokens=inputs,
        output_tokens=outputs,
        call_count=calls,
        total_cost=round(cost, 8),
        cost_currency=currency,
    )


def aggregate_usage_by_model(
    db: Session, *, start_date: date | None = None, end_date: date | None = None
) -> list[ModelUsageSummary]:
    provider_id_col = LLMUsageLog.provider_id.label("provider_id")
    model_name_col = LLMUsageLog.model_name.label("model_name")
    provider_name_col = LLMProvider.provider_name.label("provider_name")

    total_tokens = func.sum(_total_tokens_expr()).label("total_tokens")
    input_tokens = func.sum(_prompt_tokens_expr()).label("input_tokens")
    output_tokens = func.sum(_completion_tokens_expr()).label("output_tokens")
    call_count = func.count(LLMUsageLog.id).label("call_count")
    total_cost = func.sum(_total_cost_expr()).label("total_cost")
    cost_currency = func.max(_cost_currency_expr()).label("cost_currency")

    stmt = (
        select(
            provider_id_col,
            model_name_col,
            provider_name_col,
            total_tokens,
            input_tokens,
            output_tokens,
            call_count,
            total_cost,
            cost_currency,
        )
        .where(LLMUsageLog.model_name.is_not(None))
        .outerjoin(LLMProvider, LLMProvider.id == LLMUsageLog.provider_id)
    )
    stmt = _apply_date_filters(stmt, start_date, end_date)
    stmt = stmt.group_by(provider_id_col, model_name_col, provider_name_col).order_by(
        total_cost.desc(), total_tokens.desc()
    )

    rows = db.execute(stmt).all()
    summaries: list[ModelUsageSummary] = []
    for row in rows:
        data = row._mapping
        summaries.append(
            ModelUsageSummary(
                provider_id=data.get("provider_id"),
                model_name=data.get("model_name"),
                provider_name=data.get("provider_name"),
                total_tokens=int(data.get("total_tokens") or 0),
                input_tokens=int(data.get("input_tokens") or 0),
                output_tokens=int(data.get("output_tokens") or 0),
                call_count=int(data.get("call_count") or 0),
                total_cost=round(float(data.get("total_cost") or 0), 8),
                cost_currency=str(data.get("cost_currency") or "CNY"),
            )
        )
    return summaries


def get_model_usage_timeseries(
    db: Session,
    *,
    provider_id: int | None,
    model_name: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[UsageTimeseriesPoint]:
    bucket_date = func.date(LLMUsageLog.created_at).label("bucket_date")
    input_tokens = func.sum(_prompt_tokens_expr()).label("input_tokens")
    output_tokens = func.sum(_completion_tokens_expr()).label("output_tokens")
    call_count = func.count(LLMUsageLog.id).label("call_count")
    total_cost = func.sum(_total_cost_expr()).label("total_cost")
    cost_currency = func.max(_cost_currency_expr()).label("cost_currency")

    stmt = select(
        bucket_date, input_tokens, output_tokens, call_count, total_cost, cost_currency
    ).where(LLMUsageLog.model_name == model_name)

    if provider_id is None:
        stmt = stmt.where(LLMUsageLog.provider_id.is_(None))
    else:
        stmt = stmt.where(LLMUsageLog.provider_id == provider_id)

    stmt = _apply_date_filters(stmt, start_date, end_date)
    stmt = stmt.group_by(bucket_date).order_by(bucket_date.asc())

    rows = db.execute(stmt).all()
    points: list[UsageTimeseriesPoint] = []
    for row in rows:
        data = row._mapping
        raw_date = data.get("bucket_date")
        if isinstance(raw_date, str):
            point_date = date.fromisoformat(raw_date)
        elif isinstance(raw_date, datetime):
            point_date = raw_date.date()
        else:
            point_date = raw_date
        points.append(
            UsageTimeseriesPoint(
                date=point_date,
                input_tokens=int(data.get("input_tokens") or 0),
                output_tokens=int(data.get("output_tokens") or 0),
                call_count=int(data.get("call_count") or 0),
                total_cost=round(float(data.get("total_cost") or 0), 8),
                cost_currency=str(data.get("cost_currency") or "CNY"),
            )
        )
    return points


__all__ = [
    "UsageOverviewTotals",
    "ModelUsageSummary",
    "UsageTimeseriesPoint",
    "calculate_usage_overview",
    "aggregate_usage_by_model",
    "get_model_usage_timeseries",
]
