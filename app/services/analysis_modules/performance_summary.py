from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import pandas as pd

from app.schemas.analysis_module import (
    AnalysisColumnMeta,
    AnalysisContext,
    AnalysisModuleDefinition,
    AnalysisResult,
)

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型提示
    from app.services.analysis_registry import AnalysisModuleRegistry

MODULE_ID = "latency_tokens_summary"


def register_latency_and_tokens_module(registry: "AnalysisModuleRegistry") -> None:
    """注册耗时与 tokens 分析模块。"""

    definition = AnalysisModuleDefinition(
        module_id=MODULE_ID,
        name="耗时与 Tokens 概览",
        description="统计测试任务的耗时与 tokens 分布，评估性能与成本。",
        parameters=[],
        required_columns=["latency_ms", "tokens_used"],
        tags=["performance", "cost"],
        allow_llm=False,
    )

    def _handler(
        data_frame: pd.DataFrame,
        params: dict[str, Any],
        context: AnalysisContext,
    ) -> AnalysisResult:
        summary, label_map = _build_summary(data_frame)
        insights, insight_details = _build_insights(summary, label_map)
        charts = _build_chart_configs(summary, label_map)
        unit_links = _build_unit_links(summary, label_map)
        return AnalysisResult(
            data_frame=summary,
            columns_meta=_build_columns_meta(),
            insights=insights,
            llm_usage=None,
            protocol_version=definition.protocol_version,
            extra={
                "module_id": MODULE_ID,
                "charts": charts,
                "unit_links": unit_links,
                "insight_details": insight_details,
            },
        )

    registry.replace(definition, _handler)


def _normalize_unit_id(value: Any, fallback: int | None) -> int | str | None:
    if value is None:
        return fallback
    if isinstance(value, (int,)):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return fallback
        return int(value)
    text = str(value).strip()
    if not text:
        return fallback
    try:
        numeric = float(text)
    except (TypeError, ValueError):
        return text
    if math.isnan(numeric) or math.isinf(numeric):
        return fallback
    if numeric.is_integer():
        return int(numeric)
    return text


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _build_summary(data_frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[Any, str]]:
    """按最小测试单元统计耗时与 tokens 指标，并生成短标签。"""

    working_df = data_frame.copy()
    if "latency_ms" in working_df.columns:
        working_df["_latency_ms"] = pd.to_numeric(
            working_df["latency_ms"], errors="coerce"
        )
    else:
        working_df["_latency_ms"] = pd.Series(
            data=[None] * len(working_df), index=working_df.index, dtype="float64"
        )

    if "tokens_used" in working_df.columns:
        working_df["_tokens_used"] = pd.to_numeric(
            working_df["tokens_used"], errors="coerce"
        )
    else:
        working_df["_tokens_used"] = pd.Series(
            data=[None] * len(working_df), index=working_df.index, dtype="float64"
        )

    if "unit_id" not in working_df.columns:
        working_df["unit_id"] = 1
    if "unit_name" not in working_df.columns:
        working_df["unit_name"] = "总体"

    group_fields = ["unit_id", "unit_name"]
    grouped = working_df.groupby(group_fields, dropna=False)

    def _round(value: float | None, digits: int = 2) -> float | None:
        if value is None:
            return None
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return round(numeric, digits)

    def _percentile(series: pd.Series, q: float) -> float | None:
        if series.empty:
            return None
        return float(series.quantile(q))

    records: list[dict[str, Any]] = []
    label_map: dict[Any, str] = {}

    for index, ((unit_id, unit_name), subset) in enumerate(grouped, start=1):
        safe_unit_id = _normalize_unit_id(unit_id, index)
        short_label = f"单元{index}"
        label_map[safe_unit_id] = short_label

        latency_series = subset["_latency_ms"].dropna()
        tokens_series = subset["_tokens_used"].dropna()
        combined_series = subset.dropna(subset=["_latency_ms", "_tokens_used"])

        latency_avg = (
            _round(latency_series.mean()) if not latency_series.empty else None
        )
        latency_p95 = (
            _round(_percentile(latency_series, 0.95))
            if not latency_series.empty
            else None
        )
        latency_max = _round(latency_series.max()) if not latency_series.empty else None
        latency_min = _round(latency_series.min()) if not latency_series.empty else None

        tokens_total = (
            int(tokens_series.sum())
            if not tokens_series.empty and pd.notna(tokens_series.sum())
            else None
        )
        tokens_avg = _round(tokens_series.mean()) if not tokens_series.empty else None
        tokens_p95 = (
            _round(_percentile(tokens_series, 0.95))
            if not tokens_series.empty
            else None
        )
        tokens_max = (
            int(tokens_series.max())
            if not tokens_series.empty and pd.notna(tokens_series.max())
            else None
        )

        if combined_series.empty:
            throughput = tokens_per_request = None
        else:
            token_per_second = combined_series["_tokens_used"] / (
                combined_series["_latency_ms"] / 1000.0
            )
            token_per_second = token_per_second.replace(
                [float("inf"), float("-inf")], pd.NA
            )
            valid_throughput = token_per_second.dropna()
            throughput = _round(valid_throughput.mean())
            tokens_per_request = _round(combined_series["_tokens_used"].mean())

        records.append(
            {
                "unit_id": safe_unit_id,
                "unit_label": short_label,
                "unit_name": _safe_str(unit_name, "总体"),
                "sample_count": int(len(subset)),
                "avg_latency_ms": latency_avg,
                "p95_latency_ms": latency_p95,
                "max_latency_ms": latency_max,
                "min_latency_ms": latency_min,
                "avg_tokens": tokens_avg,
                "p95_tokens": tokens_p95,
                "max_tokens": tokens_max,
                "total_tokens": tokens_total,
                "avg_tokens_per_request": tokens_per_request,
                "avg_throughput_tokens_per_s": throughput,
            }
        )

    summary_df = pd.DataFrame(records)
    if not summary_df.empty:
        summary_df = summary_df.convert_dtypes()
    return summary_df, label_map


def _build_unit_links(
    summary_df: pd.DataFrame, label_map: dict[Any, str]
) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    if summary_df.empty:
        return links

    for row in summary_df.itertuples(index=False):
        raw_id = getattr(row, "unit_id", None)
        label = getattr(row, "unit_label", None)
        unit_name = getattr(row, "unit_name", None)
        normalized_id = (
            None if raw_id is None else _normalize_unit_id(raw_id, fallback=None)
        )
        lookup_key = normalized_id if normalized_id is not None else raw_id
        label_text = label_map.get(
            lookup_key,
            _safe_str(label, _safe_str(unit_name, "总体")),
        )
        links.append(
            {
                "unit_id": normalized_id,
                "unit_name": _safe_str(unit_name, "总体"),
                "label": _safe_str(label_text, _safe_str(unit_name, "总体")),
            }
        )
    return links


def _build_columns_meta() -> list[AnalysisColumnMeta]:
    return [
        AnalysisColumnMeta(
            name="unit_label",
            label="标签",
            description="用于快速辨识的短标签。",
            visualizable=[],
        ),
        AnalysisColumnMeta(
            name="unit_name",
            label="最小测试单元",
            description="测试单元名称。",
            visualizable=[],
        ),
        AnalysisColumnMeta(
            name="sample_count",
            label="样本数",
            description="统计所涉及的调用次数。",
            visualizable=["bar"],
        ),
        AnalysisColumnMeta(
            name="avg_latency_ms",
            label="平均耗时(ms)",
            description="平均耗时，单位毫秒。",
            visualizable=["bar", "line"],
        ),
        AnalysisColumnMeta(
            name="p95_latency_ms",
            label="P95 耗时(ms)",
            description="95% 请求耗时不超过该值。",
            visualizable=["bar", "line"],
        ),
        AnalysisColumnMeta(
            name="max_latency_ms",
            label="最长耗时(ms)",
            description="观测到的最大耗时。",
            visualizable=["bar"],
        ),
        AnalysisColumnMeta(
            name="min_latency_ms",
            label="最短耗时(ms)",
            description="观测到的最短耗时。",
            visualizable=["bar"],
        ),
        AnalysisColumnMeta(
            name="avg_tokens",
            label="平均 tokens",
            description="每次请求平均tokens消耗。",
            visualizable=["bar", "line"],
        ),
        AnalysisColumnMeta(
            name="p95_tokens",
            label="P95 tokens",
            description="95% 请求tokens消耗不超过该值。",
            visualizable=["bar"],
        ),
        AnalysisColumnMeta(
            name="max_tokens",
            label="最大 tokens",
            description="单次请求的最大tokens消耗。",
            visualizable=["bar"],
        ),
        AnalysisColumnMeta(
            name="total_tokens",
            label="总 tokens",
            description="该单元全部请求的 tokens 总量。",
            visualizable=["bar"],
        ),
        AnalysisColumnMeta(
            name="avg_tokens_per_request",
            label="平均 tokens/请求",
            description="单次请求的平均 tokens 消耗。",
            visualizable=["bar", "line"],
        ),
        AnalysisColumnMeta(
            name="avg_throughput_tokens_per_s",
            label="平均吞吐量(tokens/s)",
            description="单位时间内的 tokens 处理速度。",
            visualizable=["bar", "line"],
        ),
    ]


def _build_insights(
    summary_df: pd.DataFrame, label_map: dict[Any, str]
) -> tuple[list[str], list[dict[str, Any]]]:
    if summary_df.empty:
        return ["缺少最小测试单元数据，无法生成统计指标。"], []

    insights: list[str] = []
    details: list[dict[str, Any]] = []

    latency_df = summary_df.dropna(subset=["avg_latency_ms"])
    if not latency_df.empty:
        fastest = latency_df.sort_values("avg_latency_ms").iloc[0]
        slowest = latency_df.sort_values("avg_latency_ms").iloc[-1]
        if len(latency_df) > 1 and fastest["unit_id"] != slowest["unit_id"]:
            insights.append(
                f"平均耗时最快的单元是 {fastest['unit_name']}，约 {fastest['avg_latency_ms']} ms；最慢单元为 {slowest['unit_name']}，约 {slowest['avg_latency_ms']} ms。"
            )
        else:
            insights.append(
                f"平均耗时约 {fastest['avg_latency_ms']} ms，可关注异常请求以进一步优化。"
            )

        fastest_id = _normalize_unit_id(fastest["unit_id"], None)
        slowest_id = _normalize_unit_id(slowest["unit_id"], None)
        fastest_label = label_map.get(
            fastest_id,
            _safe_str(
                fastest.get("unit_label"), _safe_str(fastest["unit_name"], "总体")
            ),
        )
        slowest_label = label_map.get(
            slowest_id,
            _safe_str(
                slowest.get("unit_label"), _safe_str(slowest["unit_name"], "总体")
            ),
        )

        details.append(
            {
                "type": "latency_comparison",
                "fast": {
                    "unit_id": fastest_id,
                    "unit_name": _safe_str(fastest["unit_name"], "总体"),
                    "label": fastest_label,
                    "value": (
                        float(fastest["avg_latency_ms"])
                        if fastest["avg_latency_ms"] is not None
                        else None
                    ),
                    "unit": "ms",
                },
                "slow": {
                    "unit_id": slowest_id,
                    "unit_name": _safe_str(slowest["unit_name"], "总体"),
                    "label": slowest_label,
                    "value": (
                        float(slowest["avg_latency_ms"])
                        if slowest["avg_latency_ms"] is not None
                        else None
                    ),
                    "unit": "ms",
                },
            }
        )

    tokens_df = summary_df.dropna(subset=["avg_tokens"])
    if not tokens_df.empty:
        max_tokens_unit = tokens_df.sort_values("avg_tokens", ascending=False).iloc[0]
        max_tokens_id = _normalize_unit_id(max_tokens_unit["unit_id"], None)
        max_tokens_label = label_map.get(
            max_tokens_id,
            _safe_str(
                max_tokens_unit.get("unit_label"),
                _safe_str(max_tokens_unit["unit_name"], "总体"),
            ),
        )
        insights.append(
            f"平均 tokens 消耗最高的单元是 {max_tokens_unit['unit_name']}，约 {max_tokens_unit['avg_tokens']} tokens/请求。"
        )
        details.append(
            {
                "type": "tokens_peak",
                "unit": {
                    "unit_id": max_tokens_id,
                    "unit_name": _safe_str(max_tokens_unit["unit_name"], "总体"),
                    "label": max_tokens_label,
                    "value": (
                        float(max_tokens_unit["avg_tokens"])
                        if max_tokens_unit["avg_tokens"] is not None
                        else None
                    ),
                    "unit": "tokens/请求",
                },
            }
        )

    throughput_df = summary_df.dropna(subset=["avg_throughput_tokens_per_s"])
    if not throughput_df.empty:
        best_throughput = throughput_df.sort_values(
            "avg_throughput_tokens_per_s", ascending=False
        ).iloc[0]
        best_throughput_id = _normalize_unit_id(best_throughput["unit_id"], None)
        best_throughput_label = label_map.get(
            best_throughput_id,
            _safe_str(
                best_throughput.get("unit_label"),
                _safe_str(best_throughput["unit_name"], "总体"),
            ),
        )
        insights.append(
            f"平均吞吐量最高的单元为 {best_throughput['unit_name']}，约 {best_throughput['avg_throughput_tokens_per_s']} tokens/s。"
        )
        details.append(
            {
                "type": "throughput_peak",
                "unit": {
                    "unit_id": best_throughput_id,
                    "unit_name": _safe_str(best_throughput["unit_name"], "总体"),
                    "label": best_throughput_label,
                    "value": (
                        float(best_throughput["avg_throughput_tokens_per_s"])
                        if best_throughput["avg_throughput_tokens_per_s"] is not None
                        else None
                    ),
                    "unit": "tokens/s",
                },
            }
        )

    if not insights:
        insights.append("可进一步补充耗时或 tokens 数据，以生成对比洞察。")

    return insights, details


def _column_values(summary_df: pd.DataFrame, column: str) -> tuple[list[float], bool]:
    values: list[float] = []
    found = False
    for raw in summary_df[column].tolist():
        if raw is None or (isinstance(raw, float) and math.isnan(raw)):
            values.append(0.0)
        else:
            numeric = float(raw)
            values.append(numeric)
            found = True
    return values, found


def _single_metric_chart(
    *,
    unit_labels: list[str],
    values: list[float],
    chart_id: str,
    title: str,
    description: str,
    unit_name: str,
    color: str,
    unit_meta: dict[str, Any],
) -> dict[str, Any]:
    option = {
        "tooltip": {"trigger": "axis"},
        "grid": {"left": "6%", "right": "6%", "bottom": "12%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": unit_labels,
            "axisTick": {"alignWithLabel": True},
            "axisLabel": {"interval": 0},
        },
        "yAxis": {"type": "value", "name": unit_name},
        "series": [
            {
                "type": "bar",
                "data": values,
                "barWidth": "50%",
                "name": title,
                "itemStyle": {"color": color},
            }
        ],
    }
    return {
        "id": chart_id,
        "title": title,
        "description": description,
        "option": option,
        "meta": unit_meta,
    }


def _build_chart_configs(
    summary_df: pd.DataFrame, label_map: dict[Any, str]
) -> list[dict[str, Any]]:
    if summary_df.empty:
        return []

    unit_labels = summary_df["unit_label"].astype(str).tolist()
    unit_meta = {
        "unit_labels": unit_labels,
        "unit_ids": [
            _normalize_unit_id(raw_id, None)
            for raw_id in summary_df["unit_id"].tolist()
        ],
        "unit_names": summary_df["unit_name"].astype(str).tolist(),
    }

    charts: list[dict[str, Any]] = []

    metric_configs = [
        (
            "avg_latency_ms",
            {
                "chart_id": "avg_latency",
                "title": "平均耗时对比",
                "description": "比较各测试单元的平均耗时",
                "unit": "毫秒",
                "color": "#5470C6",
            },
        ),
        (
            "p95_latency_ms",
            {
                "chart_id": "p95_latency",
                "title": "P95 耗时",
                "description": "95% 请求耗时不超过该值",
                "unit": "毫秒",
                "color": "#91CC75",
            },
        ),
        (
            "avg_tokens",
            {
                "chart_id": "avg_tokens",
                "title": "平均 tokens",
                "description": "单次请求的平均 tokens",
                "unit": "tokens",
                "color": "#EE6666",
            },
        ),
        (
            "total_tokens",
            {
                "chart_id": "total_tokens",
                "title": "总 tokens",
                "description": "该单元在整个测试周期的 tokens 总量",
                "unit": "tokens",
                "color": "#73C0DE",
            },
        ),
        (
            "avg_throughput_tokens_per_s",
            {
                "chart_id": "avg_throughput",
                "title": "平均吞吐量",
                "description": "单位时间处理 tokens 的速度",
                "unit": "tokens/s",
                "color": "#FAC858",
            },
        ),
    ]

    for column, config in metric_configs:
        values, found = _column_values(summary_df, column)
        if found:
            charts.append(
                _single_metric_chart(
                    unit_labels=unit_labels,
                    values=values,
                    chart_id=config["chart_id"],
                    title=config["title"],
                    description=config["description"],
                    unit_name=config["unit"],
                    color=config["color"],
                    unit_meta=unit_meta,
                )
            )

    return charts
