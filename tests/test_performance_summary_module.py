from __future__ import annotations

import math

import pandas as pd

from app.services.analysis_modules import performance_summary as ps


def test_normalize_unit_id_branches():
    assert ps._normalize_unit_id(None, 7) == 7
    assert ps._normalize_unit_id(float("nan"), 8) == 8
    assert ps._normalize_unit_id(float("inf"), 9) == 9
    assert ps._normalize_unit_id(3.0, 0) == 3
    assert ps._normalize_unit_id(" ", 10) == 10
    assert ps._normalize_unit_id("abc", 11) == "abc"
    assert ps._normalize_unit_id("1.5", 12) == "1.5"
    assert ps._normalize_unit_id("inf", 13) == 13


def test_build_summary_handles_missing_columns_and_strings():
    raw = pd.DataFrame(
        {
            "unit_id": ["alpha", "beta"],
            "unit_name": ["Alpha 单元", "Beta 单元"],
        }
    )
    summary, label_map = ps._build_summary(raw)
    assert len(summary) == 2
    assert summary["avg_latency_ms"].isna().all()
    assert summary["avg_tokens"].isna().all()
    assert all(label_map[key].startswith("单元") for key in label_map)

    links = ps._build_unit_links(summary, label_map)
    assert {link["label"] for link in links} == {"单元1", "单元2"}

    charts = ps._build_chart_configs(summary, label_map)
    assert charts == []

    insights, details = ps._build_insights(summary, label_map)
    assert details == []
    assert insights == ["可进一步补充耗时或 tokens 数据，以生成对比洞察。"]


def test_build_summary_produces_metrics_for_multiple_units():
    df = pd.DataFrame(
        [
            {
                "unit_id": 1,
                "unit_name": "长名称A",
                "latency_ms": 120,
                "tokens_used": 60,
            },
            {
                "unit_id": 1,
                "unit_name": "长名称A",
                "latency_ms": 100,
                "tokens_used": 50,
            },
            {
                "unit_id": 2,
                "unit_name": "长名称B",
                "latency_ms": 210,
                "tokens_used": 40,
            },
            {
                "unit_id": 2,
                "unit_name": "长名称B",
                "latency_ms": 190,
                "tokens_used": 35,
            },
        ]
    )
    summary, label_map = ps._build_summary(df)
    insights, details = ps._build_insights(summary, label_map)

    assert any("最快的单元" in text for text in insights)
    latency_detail = next(
        item for item in details if item["type"] == "latency_comparison"
    )
    assert latency_detail["fast"]["label"] == "单元1"
    assert latency_detail["slow"]["label"] == "单元2"

    tokens_detail = next(item for item in details if item["type"] == "tokens_peak")
    assert tokens_detail["unit"]["label"] == "单元2"
    assert any("最低" in text for text in insights)

    charts = ps._build_chart_configs(summary, label_map)
    assert any(chart["id"] == "avg_latency" for chart in charts)
    bar_chart = next(chart for chart in charts if chart["id"] == "avg_latency")
    assert math.isclose(bar_chart["option"]["series"][0]["data"][0], 110.0)


def test_build_insights_with_empty_dataframe():
    insights, details = ps._build_insights(pd.DataFrame(), {})
    assert details == []
    assert insights == ["缺少最小测试单元数据，无法生成统计指标。"]


def test_build_unit_links_empty_summary():
    empty = pd.DataFrame(
        columns=[
            "unit_id",
            "unit_label",
            "unit_name",
            "sample_count",
            "avg_latency_ms",
            "avg_tokens",
        ]
    )
    assert ps._build_unit_links(empty, {}) == []
    assert ps._build_chart_configs(pd.DataFrame(), {}) == []


def test_safe_str_helper():
    assert ps._safe_str(None, "默认") == "默认"
    assert ps._safe_str("  值  ", "默认") == "值"
