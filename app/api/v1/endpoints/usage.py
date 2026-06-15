from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import UsageModelSummary, UsageOverview, UsageTimeseriesPoint
from app.services.usage_dashboard import (
    ModelUsageSummary as ModelUsageSummaryEntity,
    UsageTimeseriesPoint as UsageTimeseriesPointEntity,
    aggregate_usage_by_model,
    calculate_usage_overview,
    get_model_usage_timeseries,
)


router = APIRouter()


def _validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="结束日期必须晚于开始日期")


def _compose_model_key(provider_id: int | None, model_name: str) -> str:
    prefix = str(provider_id) if provider_id is not None else "none"
    return f"{prefix}::{model_name}"


def _parse_model_key(model_key: str) -> tuple[int | None, str]:
    parts = model_key.split("::", 1)
    if len(parts) != 2 or not parts[1]:
        raise HTTPException(status_code=400, detail="无效的模型标识")
    provider_part, model_name = parts
    if provider_part == "none":
        provider_id = None
    else:
        try:
            provider_id = int(provider_part)
        except ValueError as exc:  # pragma: no cover - 防御性判断
            raise HTTPException(status_code=400, detail="无效的模型标识") from exc
    return provider_id, model_name


def _map_model_summary(entity: ModelUsageSummaryEntity) -> UsageModelSummary:
    provider_name = entity.provider_name or "未命名提供商"
    return UsageModelSummary(
        model_key=_compose_model_key(entity.provider_id, entity.model_name),
        model_name=entity.model_name,
        provider=provider_name,
        total_tokens=entity.total_tokens,
        input_tokens=entity.input_tokens,
        output_tokens=entity.output_tokens,
        call_count=entity.call_count,
        total_cost=entity.total_cost,
        cost_currency=entity.cost_currency,
    )


def _map_timeseries_point(entity: UsageTimeseriesPointEntity) -> UsageTimeseriesPoint:
    return UsageTimeseriesPoint(
        date=entity.date,
        input_tokens=entity.input_tokens,
        output_tokens=entity.output_tokens,
        call_count=entity.call_count,
        total_cost=entity.total_cost,
        cost_currency=entity.cost_currency,
    )


@router.get("/overview", response_model=UsageOverview | None)
def read_usage_overview(
    *,
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None, description="开始日期"),
    end_date: date | None = Query(default=None, description="结束日期"),
) -> UsageOverview | None:
    """汇总全局用量指标。"""

    _validate_date_range(start_date, end_date)
    overview = calculate_usage_overview(db, start_date=start_date, end_date=end_date)
    if overview is None:
        return None
    return UsageOverview(
        total_tokens=overview.total_tokens,
        input_tokens=overview.input_tokens,
        output_tokens=overview.output_tokens,
        call_count=overview.call_count,
        total_cost=overview.total_cost,
        cost_currency=overview.cost_currency,
    )


@router.get("/models", response_model=list[UsageModelSummary])
def read_model_usage(
    *,
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None, description="开始日期"),
    end_date: date | None = Query(default=None, description="结束日期"),
) -> list[UsageModelSummary]:
    """按模型聚合用量数据。"""

    _validate_date_range(start_date, end_date)
    summaries = aggregate_usage_by_model(db, start_date=start_date, end_date=end_date)
    return [_map_model_summary(item) for item in summaries]


@router.get("/models/{model_key}/timeseries", response_model=list[UsageTimeseriesPoint])
def read_model_usage_timeseries(
    *,
    db: Session = Depends(get_db),
    model_key: str,
    start_date: date | None = Query(default=None, description="开始日期"),
    end_date: date | None = Query(default=None, description="结束日期"),
) -> list[UsageTimeseriesPoint]:
    """获取指定模型的按日用量趋势。"""

    _validate_date_range(start_date, end_date)
    provider_id, model_name = _parse_model_key(model_key)
    points = get_model_usage_timeseries(
        db,
        provider_id=provider_id,
        model_name=model_name,
        start_date=start_date,
        end_date=end_date,
    )
    return [_map_timeseries_point(point) for point in points]


__all__ = ["router"]
