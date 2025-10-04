from datetime import timedelta
from types import TracebackType
from typing import Any, Literal

import httpx
import pytest

from app.models.llm_provider import LLMModel, LLMProvider
from app.models.usage import LLMUsageLog


API_PREFIX = "/api/v1/llm-providers"


def create_provider(client, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(API_PREFIX + "/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_model(client, provider_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"{API_PREFIX}/{provider_id}/models", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_list_common_providers(client):
    response = client.get(API_PREFIX + "/common")
    assert response.status_code == 200
    data = response.json()
    keys = {item["key"] for item in data}
    assert {"openai", "anthropic"}.issubset(keys)
    openai = next(item for item in data if item["key"] == "openai")
    assert openai["base_url"] == "https://api.openai.com/v1"


def test_create_known_provider_without_base_url(client):
    payload = {
        "provider_key": "openai",
        "provider_name": "OpenAI",
        "api_key": "sk-test-openai",
    }
    provider = create_provider(client, payload)

    assert provider["provider_key"] == "openai"
    assert provider["base_url"] == "https://api.openai.com/v1"
    assert provider["is_custom"] is False
    assert provider["masked_api_key"].startswith(payload["api_key"][:4])
    assert provider["masked_api_key"].endswith(payload["api_key"][-2:])


def test_create_custom_provider_requires_base_url(client):
    payload = {
        "provider_name": "自建服务",
        "api_key": "secret",
        "is_custom": True,
    }
    response = client.post(API_PREFIX + "/", json=payload)
    assert response.status_code == 400
    assert "基础 URL" in response.text


def test_provider_listing_excludes_archived(client):
    provider = create_provider(
        client,
        {
            "provider_name": "Internal",
            "api_key": "secret",
            "is_custom": True,
            "base_url": "https://llm.internal/api",
            "logo_emoji": "🏢",
        },
    )
    create_model(
        client,
        provider["id"],
        {
            "name": "chat-internal",
            "capability": "对话",
        },
    )

    response = client.get(API_PREFIX + "/")
    assert response.status_code == 200
    items = response.json()
    assert any(item["id"] == provider["id"] for item in items)
    provider_card = next(item for item in items if item["id"] == provider["id"])

    # 删除唯一模型后应归档，列表中不再出现
    model_id = provider_card["models"][0]["id"]
    delete_resp = client.delete(f"{API_PREFIX}/{provider['id']}/models/{model_id}")
    assert delete_resp.status_code == 204

    response_after = client.get(API_PREFIX + "/")
    assert response_after.status_code == 200
    assert all(item["id"] != provider["id"] for item in response_after.json())

    # 详情接口仍可访问，并标记为已归档
    detail = client.get(f"{API_PREFIX}/{provider['id']}")
    assert detail.status_code == 200
    assert detail.json()["is_archived"] is True


def test_create_model_detects_duplicate_name(client):
    provider = create_provider(
        client,
        {
            "provider_name": "Azure OpenAI",
            "provider_key": "azure-openai",
            "api_key": "secret",
            "base_url": "https://demo.openai.azure.com",
        },
    )

    create_model(
        client,
        provider["id"],
        {"name": "gpt-4o", "capability": "对话"},
    )
    response = client.post(
        f"{API_PREFIX}/{provider['id']}/models",
        json={"name": "gpt-4o"},
    )
    assert response.status_code == 400
    assert "已存在" in response.text


def test_update_provider_requires_base_url_when_non_custom(client):
    provider = create_provider(
        client,
        {
            "provider_key": "anthropic",
            "provider_name": "Anthropic",
            "api_key": "anthropic-key",
        },
    )

    response = client.patch(f"{API_PREFIX}/{provider['id']}", json={"base_url": None})
    assert response.status_code == 400
    assert "基础 URL" in response.text


def test_invoke_llm_uses_request_parameters_only(client, monkeypatch):
    provider = create_provider(
        client,
        {
            "provider_name": "Internal",
            "api_key": "invoke-secret",
            "is_custom": True,
            "base_url": "https://llm.internal/api/",
        },
    )
    model = create_model(
        client,
        provider["id"],
        {"name": "chat-mini"},
    )

    captured: dict[str, Any] = {}

    class DummyResponse:
        status_code = 200

        def __init__(self) -> None:
            self.elapsed = timedelta(milliseconds=5)

        def json(self) -> dict[str, Any]:
            return {"choices": []}

        @property
        def text(self) -> str:
            return ""

    def fake_post(
        url: str, headers: dict[str, str], json: dict[str, Any], timeout: float
    ) -> DummyResponse:
        captured.update(
            {"url": url, "headers": headers, "json": json, "timeout": timeout}
        )
        return DummyResponse()

    monkeypatch.setattr("app.api.v1.endpoints.llms.httpx.post", fake_post)

    body = {
        "model_id": model["id"],
        "messages": [
            {"role": "system", "content": "You are a test"},
            {"role": "user", "content": "ping"},
        ],
        "parameters": {"max_tokens": 128},
    }
    response = client.post(f"{API_PREFIX}/{provider['id']}/invoke", json=body)
    assert response.status_code == 200

    assert captured["url"] == "https://llm.internal/api/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer invoke-secret"
    assert captured["json"]["model"] == "chat-mini"
    # 模型不再存储附加参数，仅沿用请求中提供的参数
    assert "temperature" not in captured["json"]
    assert captured["json"]["max_tokens"] == 128
    assert captured["timeout"] == 30.0


def test_invoke_llm_without_models_requires_model_argument(client):
    provider = create_provider(
        client,
        {
            "provider_name": "Empty",
            "api_key": "invoke",
            "is_custom": True,
            "base_url": "https://mock.llm/api",
        },
    )

    body = {
        "messages": [{"role": "user", "content": "hello"}],
    }
    response = client.post(f"{API_PREFIX}/{provider['id']}/invoke", json=body)
    assert response.status_code == 400
    assert "未能确定调用模型" in response.text


def test_invoke_llm_uses_known_base_url_when_missing(client, db_session, monkeypatch):
    provider = LLMProvider(
        provider_name="OpenAI",
        provider_key="openai",
        api_key="known-key",
        is_custom=False,
        base_url=None,
    )
    db_session.add(provider)
    db_session.commit()

    class DummyResponse:
        status_code = 200

        def __init__(self) -> None:
            self.elapsed = timedelta(milliseconds=8)

        def json(self) -> dict[str, Any]:
            return {"choices": []}

        @property
        def text(self) -> str:
            return ""

    captured: dict[str, Any] = {}

    def fake_post(
        url: str, headers: dict[str, str], json: dict[str, Any], timeout: float
    ) -> DummyResponse:
        captured.update(
            {"url": url, "headers": headers, "json": json, "timeout": timeout}
        )
        return DummyResponse()

    monkeypatch.setattr("app.api.v1.endpoints.llms.httpx.post", fake_post)

    body = {
        "messages": [{"role": "user", "content": "Hello"}],
        "model": "gpt-4o",
    }
    response = client.post(f"{API_PREFIX}/{provider.id}/invoke", json=body)
    assert response.status_code == 200

    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer known-key"
    assert captured["json"]["model"] == "gpt-4o"


def test_delete_missing_model_returns_404(client):
    provider = create_provider(
        client,
        {
            "provider_name": "Internal",
            "api_key": "secret",
            "is_custom": True,
            "base_url": "https://inner/api",
        },
    )

    response = client.delete(f"{API_PREFIX}/{provider['id']}/models/999")
    assert response.status_code == 404
    assert "模型" in response.text


def test_delete_provider_cascades_models(client):
    provider = create_provider(
        client,
        {
            "provider_name": "ToBeDeleted",
            "api_key": "secret",
            "is_custom": True,
            "base_url": "https://inner/delete",
        },
    )
    create_model(client, provider["id"], {"name": "demo-a"})
    create_model(client, provider["id"], {"name": "demo-b"})

    response = client.delete(f"{API_PREFIX}/{provider['id']}")
    assert response.status_code == 204

    follow_up = client.get(f"{API_PREFIX}/{provider['id']}")
    assert follow_up.status_code == 404

    listing = client.get(API_PREFIX + "/")
    assert all(item["id"] != provider["id"] for item in listing.json())


def test_update_allows_setting_default_model_name(client):
    provider = create_provider(
        client,
        {
            "provider_name": "Internal",
            "api_key": "secret",
            "is_custom": True,
            "base_url": "https://internal/api",
        },
    )
    model = create_model(
        client,
        provider["id"],
        {"name": "chat-mini"},
    )

    response = client.patch(
        f"{API_PREFIX}/{provider['id']}",
        json={"default_model_name": model["name"]},
    )
    assert response.status_code == 200
    assert response.json()["default_model_name"] == model["name"]


@pytest.mark.parametrize(
    "mask_value, expected",
    [
        ("123456", "******"),
        ("abcd", "****"),
        ("sk-abcdefghi", "sk-a******hi"),
    ],
)
def test_masked_api_key_format(client, mask_value: str, expected: str):
    provider = create_provider(
        client,
        {
            "provider_name": "MaskTest",
            "api_key": mask_value,
            "is_custom": True,
            "base_url": "https://mask/api",
        },
    )
    assert provider["masked_api_key"] == expected


def test_stream_invoke_llm_persists_usage(client, db_session, monkeypatch):
    provider = create_provider(
        client,
        {
            "provider_name": "Stream",
            "api_key": "stream-key",
            "is_custom": True,
            "base_url": "https://stream.llm/api",
        },
    )
    model = create_model(client, provider["id"], {"name": "chat-stream"})

    captured: dict[str, Any] = {}

    class DummyStream:
        status_code = 200

        def __init__(self, lines: list[str]) -> None:
            self._lines = lines

        def __enter__(self) -> "DummyStream":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> Literal[False]:
            return False

        def read(self) -> bytes:
            return b""

        def iter_lines(self):  # noqa: ANN201 - 接口保持与 httpx 一致
            for item in self._lines:
                yield item

    lines = [
        'data: {"id":"chatcmpl-1","choices":[{"delta":{"role":"assistant"}}]}',
        "",
        'data: {"id":"chatcmpl-1","choices":[{"delta":{"content":"你好"}}]}',
        "",
        (
            'data: {"id":"chatcmpl-1","choices":[{"delta":{}}],'
            '"usage":{"prompt_tokens":5,"completion_tokens":7,"total_tokens":12}}'
        ),
        "",
        "data: [DONE]",
        "",
    ]

    def fake_stream(method, url, headers, json, timeout):  # noqa: ANN001 - 与 httpx 接口对齐
        captured.update(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return DummyStream(lines)

    monkeypatch.setattr("app.api.v1.endpoints.llms.httpx.stream", fake_stream)

    body = {
        "model_id": model["id"],
        "messages": [{"role": "user", "content": "请问你好"}],
        "parameters": {"max_tokens": 64},
        "temperature": 0.6,
    }

    with client.stream(
        "POST", f"{API_PREFIX}/{provider['id']}/invoke/stream", json=body
    ) as response:
        assert response.status_code == 200
        chunks = list(response.iter_text())

    aggregated = "".join(chunks)
    assert '"content":"你好"' in aggregated
    assert "[DONE]" in aggregated

    usage_logs = db_session.query(LLMUsageLog).all()
    assert len(usage_logs) == 1
    log_entry = usage_logs[0]
    assert log_entry.provider_id == provider["id"]
    assert log_entry.model_id == model["id"]
    assert log_entry.model_name == model["name"]
    assert log_entry.prompt_tokens == 5
    assert log_entry.completion_tokens == 7
    assert log_entry.total_tokens == 12
    assert log_entry.response_text == "你好"
    assert log_entry.parameters == {"max_tokens": 64}
    assert pytest.approx(log_entry.temperature, rel=1e-6) == 0.6

    assert captured["json"]["stream"] is True
    assert captured["json"]["temperature"] == 0.6
    assert captured["json"]["messages"][0]["content"] == "请问你好"


def test_quick_test_history_endpoint_returns_logs(client, db_session):
    provider = create_provider(
        client,
        {
            "provider_name": "HistoryTest",
            "api_key": "history-key",
            "is_custom": True,
            "base_url": "https://history.llm/api",
        },
    )

    log = LLMUsageLog(
        provider_id=provider["id"],
        model_id=None,
        model_name="chat-history",
        source="quick_test",
        messages=[{"role": "user", "content": "回顾一下"}],
        response_text="历史记录",
        temperature=0.5,
        latency_ms=123,
        prompt_tokens=3,
        completion_tokens=4,
        total_tokens=7,
    )
    db_session.add(log)
    db_session.commit()

    response = client.get("/api/v1/llm-providers/quick-test/history")
    assert response.status_code == 200
    records = response.json()
    assert records, "历史接口应返回至少一条记录"
    matched = next(item for item in records if item["id"] == log.id)
    assert matched["model_name"] == "chat-history"
    assert matched["response_text"] == "历史记录"
    assert matched["messages"][0]["role"] == "user"
    assert matched["messages"][0]["content"] == "回顾一下"
