from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.prompt import Prompt, PromptClass, PromptVersion
from app.models.result import Result
from app.models.test_run import TestRun, TestRunStatus
from app.models.prompt_test import (
    PromptTestTask,
    PromptTestTaskStatus,
    PromptTestUnit,
    PromptTestExperiment,
    PromptTestExperimentStatus,
)


def _create_test_run_with_results(db_session: Session) -> TestRun:
    prompt_class = PromptClass(name="分析类")
    prompt = Prompt(name="性能测试", prompt_class=prompt_class)
    prompt_version = PromptVersion(prompt=prompt, version="v1", content="测试内容")

    test_run = TestRun(
        prompt_version=prompt_version,
        model_name="gpt-mini",
        repetitions=2,
        status=TestRunStatus.COMPLETED,
    )

    result_a = Result(
        test_run=test_run,
        run_index=1,
        output="响应 A",
        tokens_used=50,
        latency_ms=100,
    )
    result_b = Result(
        test_run=test_run,
        run_index=2,
        output="响应 B",
        tokens_used=60,
        latency_ms=200,
    )

    db_session.add_all(
        [prompt_class, prompt, prompt_version, test_run, result_a, result_b]
    )
    db_session.commit()
    return test_run


def _create_prompt_test_task_with_results(db_session: Session) -> PromptTestTask:
    prompt_class = PromptClass(name="PromptTest")
    prompt = Prompt(name="PromptTest用例", prompt_class=prompt_class)
    prompt_version = PromptVersion(prompt=prompt, version="v1", content="测试内容")

    task = PromptTestTask(
        name="PromptTestTask",
        status=PromptTestTaskStatus.COMPLETED,
        prompt_version=prompt_version,
        config=None,
    )

    unit = PromptTestUnit(
        task=task,
        name="单元1",
        model_name="gpt-mini",
        llm_provider_id=None,
        temperature=0.2,
        top_p=0.9,
        rounds=2,
    )

    experiment = PromptTestExperiment(
        unit=unit,
        sequence=1,
        status=PromptTestExperimentStatus.COMPLETED,
        outputs=[
            {
                "run_index": 1,
                "latency_ms": 120,
                "total_tokens": 80,
            },
            {
                "run_index": 2,
                "latency_ms": 180,
                "total_tokens": 100,
            },
        ],
    )

    db_session.add_all([prompt_class, prompt, prompt_version, task, unit, experiment])
    db_session.commit()
    return task


def test_list_analysis_modules(client):
    response = client.get("/api/v1/analysis/modules")
    assert response.status_code == 200
    modules = response.json()
    module_ids = {item["module_id"] for item in modules}
    assert "latency_tokens_summary" in module_ids


def test_execute_latency_tokens_module(client, db_session: Session):
    test_run = _create_test_run_with_results(db_session)
    payload = {
        "module_id": "latency_tokens_summary",
        "task_id": str(test_run.id),
        "target_type": "test_run",
        "parameters": {},
    }

    response = client.post("/api/v1/analysis/modules/execute", json=payload)
    assert response.status_code == 200

    payload = response.json()
    assert payload["module_id"] == "latency_tokens_summary"
    assert payload["protocol_version"] == "v1"
    assert payload["insights"]

    columns_meta = payload["columns_meta"]
    assert any(meta["name"] == "unit_label" for meta in columns_meta)
    latency_meta = next(
        meta for meta in columns_meta if meta["name"] == "avg_latency_ms"
    )
    assert "bar" in latency_meta["visualizable"]

    data_rows = payload["data"]
    assert len(data_rows) == 1

    row = data_rows[0]
    assert row["unit_label"] == "单元1"
    assert row["unit_name"] == "总体"
    assert row["sample_count"] == 2
    assert row["avg_latency_ms"] == pytest.approx(150.0)
    assert row["p95_latency_ms"] == pytest.approx(195.0)
    assert row["avg_tokens"] == pytest.approx(55.0)
    assert row["p95_tokens"] == pytest.approx(59.5)
    assert row["avg_throughput_tokens_per_s"] == pytest.approx(400.0)

    extra = payload["extra"]
    assert extra is not None
    charts = extra.get("charts") or []
    assert charts
    assert charts[0]["meta"]["unit_labels"][0] == "单元1"
    unit_links = extra.get("unit_links") or []
    assert unit_links and unit_links[0]["label"] == "单元1"
    insight_details = extra.get("insight_details") or []
    assert any(detail["type"] == "latency_comparison" for detail in insight_details)


def test_execute_with_unknown_module_returns_404(client, db_session: Session):
    test_run = _create_test_run_with_results(db_session)
    response = client.post(
        "/api/v1/analysis/modules/execute",
        json={
            "module_id": "unknown_module",
            "task_id": str(test_run.id),
            "target_type": "test_run",
            "parameters": {},
        },
    )
    assert response.status_code == 404


def test_execute_prompt_test_task_analysis(client, db_session: Session):
    task = _create_prompt_test_task_with_results(db_session)
    response = client.post(
        "/api/v1/analysis/modules/execute",
        json={
            "module_id": "latency_tokens_summary",
            "task_id": str(task.id),
            "target_type": "prompt_test_task",
            "parameters": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["module_id"] == "latency_tokens_summary"
    assert len(payload["data"]) == 1
    row = payload["data"][0]
    assert row["unit_label"] == "单元1"
    assert row["sample_count"] == 2
    assert row["avg_latency_ms"] == pytest.approx(150.0)
    assert row["avg_tokens"] == pytest.approx(90.0)
    assert row["avg_throughput_tokens_per_s"] == pytest.approx(611.11, rel=1e-3)

    extra = payload["extra"]
    assert extra is not None
    charts = extra.get("charts") or []
    assert charts
    assert charts[0]["meta"]["unit_labels"][0] == "单元1"
    unit_links = extra.get("unit_links") or []
    assert unit_links and unit_links[0]["label"] == "单元1"
    insight_details = extra.get("insight_details") or []
    assert insight_details
