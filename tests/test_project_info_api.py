from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.llm_provider import LLMModel, LLMProvider
from app.models.prompt import Prompt, PromptClass, PromptVersion
from app.models.prompt_test import (
    PromptTestExperiment,
    PromptTestTask,
    PromptTestUnit,
)


ROOT = Path(__file__).resolve().parents[1]


def _current_version() -> str:
    return json.loads(
        (ROOT / "frontend" / "src" / "version.json").read_text(encoding="utf-8")
    )["version"]


def _seed_project_assets(db_session: Session) -> None:
    provider = LLMProvider(
        provider_name="OpenAI",
        provider_key="openai",
        api_key="sk-test",
    )
    provider.models = [
        LLMModel(name="gpt-4o"),
        LLMModel(name="gpt-4.1-mini"),
    ]
    db_session.add(provider)

    archived_provider = LLMProvider(
        provider_name="Archived",
        provider_key="archived",
        api_key="sk-archived",
        is_archived=True,
    )
    archived_provider.models = [LLMModel(name="old-model")]
    db_session.add(archived_provider)

    prompt_class = PromptClass(name="客服", description="客服 Prompt")
    prompt = Prompt(
        name="欢迎语",
        description="生成欢迎语",
        prompt_class=prompt_class,
    )
    version = PromptVersion(
        prompt=prompt,
        version="v1.0.0",
        content="你好，{name}",
    )
    prompt.current_version = version
    db_session.add(prompt)
    db_session.flush()

    deleted_task = PromptTestTask(
        name="已删除任务",
        prompt_version_id=version.id,
        is_deleted=True,
    )
    task = PromptTestTask(name="欢迎语测试", prompt_version_id=version.id)
    unit = PromptTestUnit(
        task=task,
        prompt_version_id=version.id,
        name="默认单元",
        model_name="gpt-4o",
    )
    experiment = PromptTestExperiment(
        unit=unit,
        sequence=1,
        started_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        finished_at=datetime(2024, 1, 1, 10, 1, tzinfo=UTC),
    )
    db_session.add_all([task, unit, experiment, deleted_task])
    db_session.commit()


def test_project_info_summary_returns_metadata_and_counts(
    client: TestClient, db_session: Session
) -> None:
    _seed_project_assets(db_session)

    response = client.get("/api/v1/project-info/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["name"] == "PromptWorks"
    assert (
        payload["project"]["github_url"] == "https://github.com/YellowSeaa/PromptWorks"
    )
    assert payload["project"]["contact_email"] == "hh81300889@gmail.com"
    assert payload["project"]["tutorial_available"] is False
    assert payload["version"]["current"] == _current_version()
    assert payload["version"]["deployment_type"] in {"source", "docker", "unknown"}
    assert payload["statistics"] == {
        "provider_count": 1,
        "model_count": 2,
        "prompt_count": 1,
        "prompt_version_count": 1,
        "test_task_count": 1,
        "test_unit_count": 1,
        "test_experiment_count": 1,
    }


def test_project_info_check_version_uses_latest_release(
    client: TestClient, monkeypatch
) -> None:
    class DummyResponse:
        status_code = 200

        def json(self) -> dict[str, str]:
            return {
                "tag_name": "v1.2.0",
                "html_url": "https://github.com/YellowSeaa/PromptWorks/releases/tag/v1.2.0",
            }

    def fake_get(url: str, timeout: float, headers: dict[str, str]) -> DummyResponse:
        assert url.endswith("/repos/YellowSeaa/PromptWorks/releases/latest")
        assert timeout == 5.0
        assert headers["Accept"] == "application/vnd.github+json"
        return DummyResponse()

    monkeypatch.setattr("app.services.project_info.httpx.get", fake_get)

    response = client.get("/api/v1/project-info/version/check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current"] == _current_version()
    assert payload["latest"] == "v1.2.0"
    assert payload["has_update"] is True
    assert payload["check_status"] == "update_available"
    assert payload["release_url"].endswith("/v1.2.0")
    assert payload["update_guidance"]["deployment_type"] in {
        "source",
        "docker",
        "unknown",
    }
    assert payload["update_guidance"]["steps"]


def test_project_info_check_version_ignores_older_release(
    client: TestClient, monkeypatch
) -> None:
    class DummyResponse:
        status_code = 200

        def json(self) -> dict[str, str]:
            return {
                "tag_name": "v0.1.0",
                "html_url": "https://github.com/YellowSeaa/PromptWorks/releases/tag/v0.1.0",
            }

    def fake_get(url: str, timeout: float, headers: dict[str, str]) -> DummyResponse:
        return DummyResponse()

    monkeypatch.setattr("app.services.project_info.httpx.get", fake_get)

    response = client.get("/api/v1/project-info/version/check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["latest"] == "v0.1.0"
    assert payload["has_update"] is False
    assert payload["check_status"] == "up_to_date"


def test_project_info_update_commands_match_deployment_type(monkeypatch) -> None:
    from app.services.project_info import get_project_version_info

    monkeypatch.setenv("PROMPTWORKS_VERSION", "v1.0.0")
    monkeypatch.setenv("PROMPTWORKS_DEPLOYMENT_TYPE", "docker")

    docker_info = get_project_version_info(latest="v1.2.0")

    assert docker_info.has_update is True
    assert docker_info.check_status == "update_available"
    assert docker_info.update_guidance.title == "Docker 部署更新命令"
    assert docker_info.update_guidance.commands == [
        "docker compose pull",
        "docker compose up -d",
    ]

    monkeypatch.setenv("PROMPTWORKS_DEPLOYMENT_TYPE", "source")

    source_info = get_project_version_info(latest="v1.2.0")

    assert source_info.update_guidance.title == "源码部署更新命令"
    assert source_info.update_guidance.commands == [
        "git pull --ff-only",
        "uv sync",
        "npm --prefix frontend ci",
        "uv run alembic upgrade head",
    ]


def test_project_info_check_version_degrades_when_github_unavailable(
    client: TestClient, monkeypatch
) -> None:
    def fake_get(url: str, timeout: float, headers: dict[str, str]) -> object:
        raise httpx.ConnectError("network unavailable")

    monkeypatch.setattr("app.services.project_info.httpx.get", fake_get)

    response = client.get("/api/v1/project-info/version/check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current"] == _current_version()
    assert payload["latest"] is None
    assert payload["has_update"] is False
    assert payload["check_status"] == "failed"


def test_project_info_check_version_marks_github_rate_limit_as_failed(
    client: TestClient, monkeypatch
) -> None:
    class DummyResponse:
        status_code = 403

        def json(self) -> dict[str, str]:
            return {"message": "API rate limit exceeded"}

    def fake_get(url: str, timeout: float, headers: dict[str, str]) -> DummyResponse:
        return DummyResponse()

    monkeypatch.setattr("app.services.project_info.httpx.get", fake_get)

    response = client.get("/api/v1/project-info/version/check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current"] == _current_version()
    assert payload["latest"] is None
    assert payload["has_update"] is False
    assert payload["check_status"] == "failed"
