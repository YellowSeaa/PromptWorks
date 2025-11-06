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
        summary = _build_summary(data_frame)
        insights = _build_insights(summary)
        charts = _build_chart_configs(summary)
        return AnalysisResult(
            data_frame=summary,
            columns_meta=_build_columns_meta(),
            insights=insights,
            llm_usage=None,
            protocol_version=definition.protocol_version,
            extra={"module_id": MODULE_ID, "charts": charts},
        )

    registry.replace(definition, _handler)


def _build_summary(data_frame: pd.DataFrame) -> pd.DataFrame:
    """计算耗时与 tokens 相关指标。"""

    working_df = data_frame.copy()
    working_df["_latency_ms"] = pd.to_numeric(working_df["latency_ms"], errors="coerce")
    working_df["_tokens_used"] = pd.to_numeric(
        working_df["tokens_used"], errors="coerce"
    )

    latency_series = working_df["_latency_ms"].dropna()
    tokens_series = working_df["_tokens_used"].dropna()
    combined_series = working_df.dropna(subset=["_latency_ms", "_tokens_used"])

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
    total_runs = int(len(working_df))
    records.append({"metric": "样本数", "value": total_runs, "unit": "次"})

    if latency_series.empty:
        latency_avg = latency_p95 = latency_max = latency_min = None
    else:
        latency_avg = _round(latency_series.mean())
        latency_p95 = _round(_percentile(latency_series, 0.95))
        latency_max = _round(latency_series.max())
        latency_min = _round(latency_series.min())

    records.extend(
        [
            {"metric": "平均耗时", "value": latency_avg, "unit": "毫秒"},
            {"metric": "P95 耗时", "value": latency_p95, "unit": "毫秒"},
            {"metric": "最长耗时", "value": latency_max, "unit": "毫秒"},
            {"metric": "最短耗时", "value": latency_min, "unit": "毫秒"},
        ]
    )

    if tokens_series.empty:
        tokens_total = tokens_avg = tokens_p95 = tokens_max = None
    else:
        tokens_total_raw = tokens_series.sum()
        tokens_total = int(tokens_total_raw) if pd.notna(tokens_total_raw) else None
        tokens_avg = _round(tokens_series.mean())
        tokens_p95 = _round(_percentile(tokens_series, 0.95))
        tokens_max_raw = tokens_series.max()
        tokens_max = int(tokens_max_raw) if pd.notna(tokens_max_raw) else None

    records.extend(
        [
            {"metric": "总 tokens", "value": tokens_total, "unit": "tokens"},
            {"metric": "平均 tokens", "value": tokens_avg, "unit": "tokens"},
            {"metric": "P95 tokens", "value": tokens_p95, "unit": "tokens"},
            {"metric": "最大 tokens", "value": tokens_max, "unit": "tokens"},
        ]
    )

    if combined_series.empty:
        throughput = tokens_per_request = None
    else:
        token_per_second_series = combined_series["_tokens_used"] / (
            combined_series["_latency_ms"] / 1000.0
        )
        token_per_second_series = token_per_second_series.replace(
            [float("inf"), float("-inf")], pd.NA
        )
        valid_throughput = token_per_second_series.dropna()
        throughput = _round(valid_throughput.mean())
        tokens_per_request = _round(combined_series["_tokens_used"].mean())

    records.append(
        {
            "metric": "平均吞吐量",
            "value": throughput,
            "unit": "tokens/s",
        }
    )
    records.append(
        {
            "metric": "平均 tokens/请求",
            "value": tokens_per_request,
            "unit": "tokens",
        }
    )

    summary_df = pd.DataFrame(records, columns=["metric", "value", "unit"])
    return summary_df


def _build_columns_meta() -> list[AnalysisColumnMeta]:
    return [
        AnalysisColumnMeta(
            name="metric",
            label="指标",
            description="统计指标名称。",
            visualizable=[],
        ),
        AnalysisColumnMeta(
            name="value",
            label="数值",
            description="对应的统计值。",
            visualizable=["bar"],
        ),
        AnalysisColumnMeta(
            name="unit",
            label="单位",
            description="数值所对应的单位。",
            visualizable=[],
        ),
    ]


def _build_insights(summary_df: pd.DataFrame) -> list[str]:
    """基于 summary_df 生成简要洞察。"""

    insights: list[str] = []

    def _get_value(metric: str) -> float | int | None:
        row = summary_df.loc[summary_df["metric"] == metric]
        if row.empty:
            return None
        raw_value = row.iloc[0]["value"]
        if pd.isna(raw_value):
            return None
        return raw_value

    avg_latency = _get_value("平均耗时")
    p95_latency = _get_value("P95 耗时")
    avg_tokens = _get_value("平均 tokens")
    throughput = _get_value("平均吞吐量")

    if avg_latency is not None and p95_latency is not None:
        insights.append(f"平均耗时约 {avg_latency} ms，P95 达到 {p95_latency} ms。")
    elif avg_latency is not None:
        insights.append(f"平均耗时约 {avg_latency} ms。")

    if avg_tokens is not None:
        insights.append(f"单次请求平均消耗 {avg_tokens} tokens。")

    if throughput is not None:
        insights.append(f"平均吞吐量约为 {throughput} tokens/s。")

    if not insights:
        insights.append("缺少足够的耗时或 tokens 数据，无法生成统计指标。")

    return insights


def _metric_value(summary_df: pd.DataFrame, metric: str) -> float | None:
    row = summary_df.loc[summary_df["metric"] == metric]
    if row.empty:
        return None
    value = row.iloc[0]["value"]
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _build_chart_configs(summary_df: pd.DataFrame) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []

    latency_metrics = [
        ("平均耗时", "平均耗时"),
        ("P95 耗时", "P95 耗时"),
        ("最长耗时", "最长耗时"),
        ("最短耗时", "最短耗时"),
    ]
    latency_values = [
        _metric_value(summary_df, metric_id) for metric_id, _ in latency_metrics
    ]
    if any(value is not None for value in latency_values):
        charts.append(
            {
                "id": "latency_stats",
                "title": "耗时统计（毫秒）",
                "description": "平均、P95、最长、最短耗时对比",
                "option": {
                    "tooltip": {"trigger": "axis"},
                    "grid": {
                        "left": "6%",
                        "right": "4%",
                        "bottom": "8%",
                        "containLabel": True,
                    },
                    "xAxis": {
                        "type": "category",
                        "data": [label for _, label in latency_metrics],
                        "axisTick": {"alignWithLabel": True},
                    },
                    "yAxis": {"type": "value", "name": "毫秒"},
                    "series": [
                        {
                            "type": "bar",
                            "data": [
                                value if value is not None else 0
                                for value in latency_values
                            ],
                            "itemStyle": {"color": "#5470C6"},
                            "barWidth": "45%",
                        }
                    ],
                },
            }
        )

    token_metrics = [
        ("总 tokens", "总 tokens"),
        ("平均 tokens", "平均 tokens"),
        ("P95 tokens", "P95 tokens"),
        ("最大 tokens", "最大 tokens"),
        ("平均 tokens/请求", "平均 tokens/请求"),
    ]
    token_values = [
        _metric_value(summary_df, metric_id) for metric_id, _ in token_metrics
    ]
    if any(value is not None for value in token_values):
        charts.append(
            {
                "id": "token_stats",
                "title": "Tokens 消耗对比",
                "description": "总量、平均、P95、最大以及单请求平均 tokens 指标",
                "option": {
                    "tooltip": {"trigger": "axis"},
                    "grid": {
                        "left": "6%",
                        "right": "4%",
                        "bottom": "8%",
                        "containLabel": True,
                    },
                    "xAxis": {
                        "type": "category",
                        "data": [label for _, label in token_metrics],
                        "axisTick": {"alignWithLabel": True},
                    },
                    "yAxis": {"type": "value", "name": "tokens"},
                    "series": [
                        {
                            "type": "bar",
                            "data": [
                                value if value is not None else 0
                                for value in token_values
                            ],
                            "itemStyle": {"color": "#91CC75"},
                            "barWidth": "45%",
                        }
                    ],
                },
            }
        )

    throughput_value = _metric_value(summary_df, "平均吞吐量")
    if throughput_value is not None:
        charts.append(
            {
                "id": "throughput",
                "title": "平均吞吐量",
                "description": "单位时间内平均 tokens 消耗（tokens/s）",
                "option": {
                    "tooltip": {"trigger": "item"},
                    "xAxis": {
                        "type": "category",
                        "data": ["平均吞吐量"],
                        "axisTick": {"show": False},
                    },
                    "yAxis": {"type": "value", "name": "tokens/s"},
                    "series": [
                        {
                            "type": "bar",
                            "data": [throughput_value],
                            "itemStyle": {"color": "#FAC858"},
                            "barWidth": "35%",
                        }
                    ],
                },
            }
        )

    return charts
