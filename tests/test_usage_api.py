from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.llm_provider import LLMProvider
from app.models.usage import LLMUsageLog


def _seed_usage_logs(db_session: Session) -> tuple[int, int | None]:
    provider = LLMProvider(
        provider_name="OpenAI",
        provider_key="openai",
        api_key="sk-test",
    )
    another = LLMProvider(
        provider_name="Anthropic",
        provider_key="anthropic",
        api_key="sk-test-2",
    )
    db_session.add_all([provider, another])
    db_session.flush()

    logs = [
        LLMUsageLog(
            provider_id=provider.id,
            model_name="gpt-4",
            source="quick_test",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=None,
            created_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        ),
        LLMUsageLog(
            provider_id=provider.id,
            model_name="gpt-4",
            source="quick_test",
            prompt_tokens=5,
            completion_tokens=7,
            total_tokens=13,
            created_at=datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc),
        ),
        LLMUsageLog(
            provider_id=another.id,
            model_name="claude-3",
            source="quick_test",
            prompt_tokens=8,
            completion_tokens=4,
            total_tokens=None,
            created_at=datetime(2024, 1, 3, 9, 0, tzinfo=timezone.utc),
        ),
        LLMUsageLog(
            provider_id=provider.id,
            model_name="gpt-3.5",
            source="quick_test",
            prompt_tokens=6,
            completion_tokens=9,
            total_tokens=None,
            created_at=datetime(2024, 1, 4, 8, 0, tzinfo=timezone.utc),
        ),
        LLMUsageLog(
            provider_id=provider.id,
            model_name="gpt-4",
            source="quick_test",
            prompt_tokens=3,
            completion_tokens=2,
            total_tokens=None,
            created_at=datetime(2023, 12, 20, 8, 0, tzinfo=timezone.utc),
        ),
    ]

    db_session.add_all(logs)
    db_session.commit()
    return provider.id, another.id


def test_usage_overview_and_models(client: TestClient, db_session: Session) -> None:
    provider_id, another_id = _seed_usage_logs(db_session)

    overview_resp = client.get("/api/v1/usage/overview")
    assert overview_resp.status_code == 200
    assert overview_resp.json() == {
        "total_tokens": 75,
        "input_tokens": 32,
        "output_tokens": 42,
        "call_count": 5,
        "total_cost": 0.0,
        "cost_currency": "CNY",
    }

    models_resp = client.get("/api/v1/usage/models")
    assert models_resp.status_code == 200
    payload = models_resp.json()
    assert [item["model_name"] for item in payload] == [
        "gpt-4",
        "gpt-3.5",
        "claude-3",
    ]

    gpt4_summary = payload[0]
    assert gpt4_summary["provider"] == "OpenAI"
    assert gpt4_summary["total_tokens"] == 48
    assert gpt4_summary["input_tokens"] == 18
    assert gpt4_summary["output_tokens"] == 29
    assert gpt4_summary["call_count"] == 3
    assert gpt4_summary["model_key"] == f"{provider_id}::gpt-4"
    assert gpt4_summary["total_cost"] == 0.0
    assert gpt4_summary["cost_currency"] == "CNY"

    claude_summary = payload[2]
    assert claude_summary["model_key"] == f"{another_id}::claude-3"
    assert claude_summary["total_tokens"] == 12


def test_usage_timeseries_and_filters(client: TestClient, db_session: Session) -> None:
    provider_id, _ = _seed_usage_logs(db_session)
    model_key = f"{provider_id}::gpt-4"

    series_resp = client.get(f"/api/v1/usage/models/{model_key}/timeseries")
    assert series_resp.status_code == 200
    series = series_resp.json()
    assert [item["date"] for item in series] == [
        "2023-12-20",
        "2024-01-01",
        "2024-01-02",
    ]
    first_point = series[0]
    assert first_point["input_tokens"] == 3
    assert first_point["output_tokens"] == 2

    range_resp = client.get(
        f"/api/v1/usage/models/{model_key}/timeseries",
        params={
            "start_date": date(2024, 1, 1).isoformat(),
            "end_date": date(2024, 1, 31).isoformat(),
        },
    )
    assert range_resp.status_code == 200
    ranged_series = range_resp.json()
    assert [item["date"] for item in ranged_series] == ["2024-01-01", "2024-01-02"]

    overview_resp = client.get(
        "/api/v1/usage/overview",
        params={
            "start_date": date(2024, 1, 1).isoformat(),
            "end_date": date(2024, 1, 4).isoformat(),
        },
    )
    assert overview_resp.status_code == 200
    assert overview_resp.json() == {
        "total_tokens": 70,
        "input_tokens": 29,
        "output_tokens": 40,
        "call_count": 4,
        "total_cost": 0.0,
        "cost_currency": "CNY",
    }


def test_invalid_queries_return_errors(client: TestClient) -> None:
    invalid_range = client.get(
        "/api/v1/usage/models",
        params={"start_date": "2024-02-01", "end_date": "2024-01-01"},
    )
    assert invalid_range.status_code == 400

    invalid_key = client.get("/api/v1/usage/models/invalid/timeseries")
    assert invalid_key.status_code == 400
