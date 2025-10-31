from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping

import httpx
import pytest
from sqlalchemy import select

from app.models.llm_provider import LLMModel, LLMProvider
from app.models.prompt import Prompt, PromptClass, PromptVersion
from app.models.system_setting import SystemSetting
from app.models.test_run import TestRun, TestRunStatus
from app.models.usage import LLMUsageLog
from app.services import test_run as test_run_service
from app.services.system_settings import DEFAULT_TEST_TASK_TIMEOUT


def _create_prompt_version(db_session) -> PromptVersion:
    prompt_class = PromptClass(name="聊天类")
    prompt = Prompt(name="对话助手", prompt_class=prompt_class)
    version = PromptVersion(prompt=prompt, version="v1", content="你是一位助手。")
    prompt.current_version = version
    db_session.add_all([prompt_class, prompt, version])
    db_session.commit()
    return version


def _create_provider_with_model(
    db_session, *, base_url: str | None = "https://llm.example/api"
) -> LLMModel:
    provider = LLMProvider(
        provider_name="Internal",
        provider_key=None,
        api_key="secret-key",
        is_custom=True,
        base_url=base_url,
    )
    model = LLMModel(provider=provider, name="chat-mini")
    db_session.add_all([provider, model])
    db_session.commit()
    return model


class DummyResponse:
    def __init__(self, payload: dict[str, Any], *, elapsed_ms: int | None) -> None:
        self._payload = payload
        self.status_code = 200
        self.elapsed = (
            timedelta(milliseconds=elapsed_ms) if elapsed_ms is not None else None
        )

    def json(self) -> dict[str, Any]:  # noqa: ANN401 - 与 httpx 接口对齐
        return self._payload

    @property
    def text(self) -> str:
        return ""


@pytest.fixture()
def prompt_version(db_session):
    return _create_prompt_version(db_session)


@pytest.fixture()
def provider_model(db_session):
    return _create_provider_with_model(db_session)


def test_execute_test_run_generates_results_and_usage(
    db_session, prompt_version, provider_model, monkeypatch
):
    provider = provider_model.provider

    response_payloads = {
        1: {
            "choices": [{"message": {"content": "第一次响应"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 5},
        },
        2: {
            "choices": [{"text": "第二次响应"}],
            "usage": {"total_tokens": 9},
        },
    }

    def fake_post(*_, **kwargs):  # noqa: ANN002 - 接口保持与 httpx 一致
        assert kwargs["timeout"] == DEFAULT_TEST_TASK_TIMEOUT
        payload = kwargs.get("json") or {}
        messages = payload.get("messages") or []
        user_content = ""
        if len(messages) > 1 and isinstance(messages[1], Mapping):
            user_content = str(messages[1].get("content", ""))
        run_index = 1 if "第 1" in user_content else 2
        selected = response_payloads[run_index]
        elapsed_ms = 12 if run_index == 1 else None
        return DummyResponse(selected, elapsed_ms=elapsed_ms)

    monkeypatch.setattr("app.services.test_run.httpx.post", fake_post)

    test_run = TestRun(
        prompt_version_id=prompt_version.id,
        model_name=provider_model.name,
        model_version=provider.provider_name,
        temperature=0.2,
        top_p=0.95,
        repetitions=2,
        schema={
            "llm_provider_id": provider.id,
            "llm_model_id": provider_model.id,
            "llm_parameters": {"presence_penalty": 0.1},
            "max_tokens": 64,
            "conversation": [
                {"role": "system", "content": "请保持专业"},
                {"role": "user", "content": "第 {{run_index}} 次提问"},
            ],
        },
    )
    test_run.prompt_version = prompt_version
    db_session.add(test_run)
    db_session.commit()

    executed = test_run_service.execute_test_run(db_session, test_run)
    db_session.commit()

    assert executed.status == TestRunStatus.COMPLETED
    assert executed.schema["prompt_snapshot"] == prompt_version.content
    assert executed.schema["llm_provider_id"] == provider.id
    assert executed.schema["llm_model_id"] == provider_model.id

    results = (
        db_session.scalars(select(TestRun).where(TestRun.id == executed.id))
        .one()
        .results
    )
    assert len(results) == 2
    outputs = [item.output for item in sorted(results, key=lambda r: r.run_index)]
    assert outputs == ["第一次响应", "第二次响应"]

    usage_logs = db_session.scalars(select(LLMUsageLog)).all()
    assert len(usage_logs) == 2
    assert {log.total_tokens for log in usage_logs} == {8, 9}


def test_execute_test_run_skips_completed(
    monkeypatch, db_session, prompt_version, provider_model
):
    called = False

    def fake_post(*args, **kwargs):  # pragma: no cover - 不应被调用
        nonlocal called
        called = True
        raise AssertionError("httpx.post should not be called")

    monkeypatch.setattr("app.services.test_run.httpx.post", fake_post)

    test_run = TestRun(
        prompt_version_id=prompt_version.id,
        model_name=provider_model.name,
        temperature=0.1,
        top_p=1.0,
        repetitions=1,
        status=TestRunStatus.COMPLETED,
    )
    db_session.add(test_run)
    db_session.commit()

    result = test_run_service.execute_test_run(db_session, test_run)
    assert result.status == TestRunStatus.COMPLETED
    assert called is False


def test_execute_test_run_requires_prompt_version(db_session, provider_model):
    test_run = TestRun(
        prompt_version_id=999,
        model_name=provider_model.name,
        temperature=0.1,
        top_p=1.0,
        repetitions=1,
        schema={"llm_provider_id": provider_model.provider_id},
    )
    test_run.prompt_version = None
    test_run.status = TestRunStatus.PENDING
    assert test_run.prompt_version is None
    with pytest.raises(test_run_service.TestRunExecutionError):
        test_run_service.execute_test_run(db_session, test_run)


def test_execute_test_run_respects_custom_timeout(
    db_session, prompt_version, provider_model, monkeypatch
):
    provider = provider_model.provider
    custom_timeout = 120
    db_session.add(
        SystemSetting(
            key="testing_timeout",
            value={
                "quick_test_timeout": 20,
                "test_task_timeout": custom_timeout,
            },
        )
    )
    db_session.commit()

    timeout_values: list[float] = []

    class DummyResponse:
        status_code = 200

        def __init__(self) -> None:
            self.elapsed = timedelta(milliseconds=5)

        def json(self) -> dict[str, Any]:
            return {"choices": []}

        @property
        def text(self) -> str:
            return ""

    def fake_post(*_, **kwargs):
        timeout_values.append(kwargs["timeout"])
        return DummyResponse()

    monkeypatch.setattr("app.services.test_run.httpx.post", fake_post)

    test_run = TestRun(
        prompt_version_id=prompt_version.id,
        model_name=provider_model.name,
        repetitions=1,
        schema={
            "llm_provider_id": provider.id,
            "llm_model_id": provider_model.id,
            "conversation": [
                {"role": "system", "content": "保持专业"},
                {"role": "user", "content": "请测试"},
            ],
        },
    )
    test_run.prompt_version = prompt_version
    db_session.add(test_run)
    db_session.commit()

    result = test_run_service.execute_test_run(db_session, test_run)
    db_session.commit()

    assert result.status == TestRunStatus.COMPLETED
    assert timeout_values and timeout_values[0] == custom_timeout


def test_resolve_provider_with_string_ids(db_session, prompt_version, provider_model):
    test_run = TestRun(
        prompt_version_id=prompt_version.id,
        model_name=provider_model.name,
        temperature=0.3,
        top_p=0.9,
        repetitions=1,
        schema={
            "llm_provider_id": str(provider_model.provider_id),
            "llm_model_id": str(provider_model.id),
        },
    )
    test_run.prompt_version = prompt_version
    provider, model = test_run_service._resolve_provider_and_model(db_session, test_run)
    assert provider.id == provider_model.provider_id
    assert model.id == provider_model.id


def test_resolve_provider_falls_back_to_model_name(db_session, prompt_version):
    model = _create_provider_with_model(db_session)
    test_run = TestRun(
        prompt_version_id=prompt_version.id,
        model_name=model.name,
        temperature=0.2,
        top_p=1.0,
        repetitions=1,
        schema={},
    )
    test_run.prompt_version = prompt_version
    provider, resolved_model = test_run_service._resolve_provider_and_model(
        db_session, test_run
    )
    assert provider.id == model.provider_id
    assert resolved_model.id == model.id


def test_resolve_provider_missing_raises(db_session, prompt_version):
    test_run = TestRun(
        prompt_version_id=prompt_version.id,
        model_name="unknown-model",
        temperature=0.1,
        top_p=1.0,
        repetitions=1,
        schema={},
    )
    test_run.prompt_version = prompt_version
    with pytest.raises(test_run_service.TestRunExecutionError) as exc:
        test_run_service._resolve_provider_and_model(db_session, test_run)
    assert exc.value.status_code == httpx.codes.NOT_FOUND


def test_build_parameters_merges_nested():
    test_run = TestRun(
        prompt_version_id=1,
        model_name="model",
        temperature=0.5,
        top_p=0.8,
        repetitions=1,
    )
    schema = {
        "llm_parameters": {"max_tokens": 128},
        "parameters": {"frequency_penalty": 0.4},
        "metadata": {"trace_id": "x"},
    }
    params = test_run_service._build_parameters(test_run, schema)
    assert params["temperature"] == 0.5
    assert params["top_p"] == 0.8
    assert params["max_tokens"] == 128
    assert params["frequency_penalty"] == 0.4
    assert params["metadata"] == {"trace_id": "x"}


def test_build_messages_with_inputs_and_placeholders(prompt_version):
    schema = {
        "conversation": [
            {"role": "system", "content": "系统指令"},
            {"role": "user", "content": "提问 {{run_index}}"},
            {"content": "忽略无角色"},
        ],
        "inputs": ["备用 {{run_index}}"],
    }
    messages = test_run_service._build_messages(schema, prompt_version.content, 2)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "2" in messages[1]["content"]


def test_build_messages_uses_user_role_for_prompt_snapshot(prompt_version):
    schema = {
        "inputs": ["提问 {{run_index}}"],
    }
    messages = test_run_service._build_messages(schema, prompt_version.content, 1)
    assert len(messages) >= 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == prompt_version.content
    assert messages[1]["role"] == "user"
    assert "1" in messages[1]["content"]


def test_resolve_base_url_requires_value(db_session):
    provider = LLMProvider(
        provider_name="NoBase",
        provider_key=None,
        api_key="key",
        is_custom=True,
        base_url=None,
    )
    db_session.add(provider)
    db_session.commit()

    with pytest.raises(test_run_service.TestRunExecutionError):
        test_run_service._resolve_base_url(provider)


def test_ensure_mapping_handles_non_mapping():
    assert test_run_service._ensure_mapping({"a": 1}) == {"a": 1}
    assert test_run_service._ensure_mapping("invalid") == {}
