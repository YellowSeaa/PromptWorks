from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.llm_provider import LLMModel, LLMProvider
from app.models.usage import LLMUsageLog
from app.services.model_costs import calculate_model_call_cost


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


@dataclass(slots=True)
class _UsageCostRow:
    log: LLMUsageLog
    provider_name: str | None
    recalculated_cost: float
    cost_currency: str

    @property
    def input_tokens(self) -> int:
        return int(self.log.prompt_tokens or 0)

    @property
    def output_tokens(self) -> int:
        return int(self.log.completion_tokens or 0)

    @property
    def total_tokens(self) -> int:
        if self.log.total_tokens is not None:
            return int(self.log.total_tokens or 0)
        return self.input_tokens + self.output_tokens


@dataclass(slots=True)
class _UsageAccumulator:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0
    total_cost: float = 0.0
    cost_currency: str = "CNY"

    def add(self, row: _UsageCostRow) -> None:
        self.input_tokens += row.input_tokens
        self.output_tokens += row.output_tokens
        self.total_tokens += row.total_tokens
        self.call_count += 1
        self.total_cost += row.recalculated_cost
        self.cost_currency = row.cost_currency or self.cost_currency


def _apply_date_filters(stmt: Select, start_date: date | None, end_date: date | None):
    if start_date:
        stmt = stmt.where(func.date(LLMUsageLog.created_at) >= start_date)
    if end_date:
        stmt = stmt.where(func.date(LLMUsageLog.created_at) <= end_date)
    return stmt


def _load_usage_cost_rows(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    model_name: str | None = None,
    provider_id: int | None = None,
    filter_provider: bool = False,
) -> list[_UsageCostRow]:
    model_match = or_(
        LLMUsageLog.model_id == LLMModel.id,
        and_(
            LLMUsageLog.model_id.is_(None),
            LLMUsageLog.provider_id == LLMModel.provider_id,
            LLMUsageLog.model_name == LLMModel.name,
        ),
    )
    stmt = (
        select(LLMUsageLog, LLMProvider.provider_name, LLMModel)
        .outerjoin(LLMProvider, LLMProvider.id == LLMUsageLog.provider_id)
        .outerjoin(LLMModel, model_match)
    )
    if model_name is not None:
        stmt = stmt.where(LLMUsageLog.model_name == model_name)
    if filter_provider:
        if provider_id is None:
            stmt = stmt.where(LLMUsageLog.provider_id.is_(None))
        else:
            stmt = stmt.where(LLMUsageLog.provider_id == provider_id)
    stmt = _apply_date_filters(stmt, start_date, end_date)

    rows: list[_UsageCostRow] = []
    for log, provider_name, model in db.execute(stmt).all():
        cost = _calculate_current_or_snapshot_cost(log, model)
        rows.append(
            _UsageCostRow(
                log=log,
                provider_name=provider_name,
                recalculated_cost=cost[0],
                cost_currency=cost[1],
            )
        )
    return rows


def _calculate_current_or_snapshot_cost(
    log: LLMUsageLog, model: LLMModel | None
) -> tuple[float, str]:
    if model is not None:
        cost = calculate_model_call_cost(
            model,
            prompt_tokens=log.prompt_tokens,
            completion_tokens=log.completion_tokens,
            total_tokens=log.total_tokens,
        )
        return cost.total_cost, cost.currency
    return float(log.total_cost or 0), str(log.cost_currency or "CNY")


def _common_currency(rows: list[_UsageCostRow]) -> str:
    currencies = [row.cost_currency for row in rows if row.cost_currency]
    return currencies[0] if currencies else "CNY"


def calculate_usage_overview(
    db: Session, *, start_date: date | None = None, end_date: date | None = None
) -> UsageOverviewTotals | None:
    rows = _load_usage_cost_rows(
        db,
        start_date=start_date,
        end_date=end_date,
    )
    total = sum(row.total_tokens for row in rows)
    inputs = sum(row.input_tokens for row in rows)
    outputs = sum(row.output_tokens for row in rows)
    calls = len(rows)
    cost = sum(row.recalculated_cost for row in rows)
    currency = _common_currency(rows)

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
    rows = _load_usage_cost_rows(
        db,
        start_date=start_date,
        end_date=end_date,
    )
    summaries_by_model: dict[tuple[int | None, str, str | None], _UsageAccumulator] = {}
    for row in rows:
        if row.log.model_name is None:
            continue
        key = (row.log.provider_id, row.log.model_name, row.provider_name)
        grouped = summaries_by_model.setdefault(key, _UsageAccumulator())
        grouped.add(row)

    summaries: list[ModelUsageSummary] = []
    for (provider_id, model_name, provider_name), data in summaries_by_model.items():
        summaries.append(
            ModelUsageSummary(
                provider_id=provider_id,
                model_name=model_name,
                provider_name=provider_name,
                total_tokens=data.total_tokens,
                input_tokens=data.input_tokens,
                output_tokens=data.output_tokens,
                call_count=data.call_count,
                total_cost=round(data.total_cost, 8),
                cost_currency=data.cost_currency,
            )
        )
    summaries.sort(key=lambda item: (-item.total_cost, -item.total_tokens))
    return summaries


def get_model_usage_timeseries(
    db: Session,
    *,
    provider_id: int | None,
    model_name: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[UsageTimeseriesPoint]:
    rows = _load_usage_cost_rows(
        db,
        start_date=start_date,
        end_date=end_date,
        model_name=model_name,
        provider_id=provider_id,
        filter_provider=True,
    )
    points_by_date: dict[date, _UsageAccumulator] = {}
    for row in rows:
        raw_date = row.log.created_at
        if isinstance(raw_date, str):
            point_date = date.fromisoformat(raw_date)
        elif isinstance(raw_date, datetime):
            point_date = raw_date.date()
        else:
            point_date = raw_date
        grouped = points_by_date.setdefault(point_date, _UsageAccumulator())
        grouped.add(row)

    points: list[UsageTimeseriesPoint] = []
    for point_date in sorted(points_by_date):
        data = points_by_date[point_date]
        points.append(
            UsageTimeseriesPoint(
                date=point_date,
                input_tokens=data.input_tokens,
                output_tokens=data.output_tokens,
                call_count=data.call_count,
                total_cost=round(data.total_cost, 8),
                cost_currency=data.cost_currency,
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
