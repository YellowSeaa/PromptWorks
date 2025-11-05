from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.prompt import Prompt, PromptClass, PromptVersion
from app.models.result import Result
from app.models.test_run import TestRun, TestRunStatus


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
        "parameters": {},
    }

    response = client.post("/api/v1/analysis/modules/execute", json=payload)
    assert response.status_code == 200

    payload = response.json()
    assert payload["module_id"] == "latency_tokens_summary"
    assert payload["protocol_version"] == "v1"
    assert payload["insights"]

    data_rows = payload["data"]
    assert len(data_rows) >= 1

    metrics = {row["metric"]: row for row in data_rows}
    assert metrics["样本数"]["value"] == 2
    assert metrics["平均耗时"]["value"] == pytest.approx(150.0)
    assert metrics["P95 耗时"]["value"] == pytest.approx(195.0)
    assert metrics["平均 tokens"]["value"] == pytest.approx(55.0)
    assert metrics["平均吞吐量"]["value"] == pytest.approx(400.0)


def test_execute_with_unknown_module_returns_404(client, db_session: Session):
    test_run = _create_test_run_with_results(db_session)
    response = client.post(
        "/api/v1/analysis/modules/execute",
        json={
            "module_id": "unknown_module",
            "task_id": str(test_run.id),
            "parameters": {},
        },
    )
    assert response.status_code == 404
