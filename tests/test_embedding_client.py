from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.services.embedding_client import (
    EmbeddingClient,
    EmbeddingClientError,
    EmbeddingRequest,
)


def _provider(
    *,
    base_url: str | None = "https://embedding.example/v1/",
    api_key: str | None = "test-key",
):
    return SimpleNamespace(
        id=1,
        provider_key=None,
        provider_name="测试 Embedding 提供方",
        base_url=base_url,
        api_key=api_key,
    )


def _model(
    *,
    dimensions: int | None = None,
    batch_size: int | None = None,
):
    return SimpleNamespace(
        id=2,
        provider_id=1,
        name="text-embedding-test",
        embedding_api_style="openai_compatible",
        embedding_dimensions=dimensions,
        embedding_batch_size=batch_size,
    )


def _client_with_handler(handler):
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    return http_client


def test_embed_texts_posts_openai_compatible_embeddings_request():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = request.read()
        return httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [0.1, 0.2]},
                    {"embedding": [0.3, 0.4]},
                ]
            },
        )

    http_client = _client_with_handler(handler)
    client = EmbeddingClient(
        provider=_provider(),
        model=_model(dimensions=2),
        http_client=http_client,
    )

    result = client.embed_texts(
        EmbeddingRequest(provider_id=1, model_id=2, texts=["第一段", "第二段"])
    )

    assert captured["url"] == "https://embedding.example/v1/embeddings"
    assert captured["headers"]["authorization"] == "Bearer test-key"
    assert captured["payload"] == (
        b'{"model":"text-embedding-test","input":["\xe7\xac\xac\xe4\xb8\x80\xe6\xae\xb5",'
        b'"\xe7\xac\xac\xe4\xba\x8c\xe6\xae\xb5"],"dimensions":2}'
    )
    assert result.embeddings == [[0.1, 0.2], [0.3, 0.4]]


def test_embed_texts_omits_dimensions_when_not_configured():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = request.read()
        return httpx.Response(200, json={"data": [{"embedding": [0.1]}]})

    http_client = _client_with_handler(handler)
    client = EmbeddingClient(
        provider=_provider(),
        model=_model(dimensions=None),
        http_client=http_client,
    )

    client.embed_texts(EmbeddingRequest(provider_id=1, model_id=2, texts=["单条文本"]))

    assert captured["payload"] == (
        b'{"model":"text-embedding-test","input":["\xe5\x8d\x95\xe6\x9d\xa1\xe6\x96\x87\xe6\x9c\xac"]}'
    )


def test_embed_texts_splits_requests_by_model_batch_size():
    captured_inputs: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read().decode("utf-8")
        import json

        inputs = json.loads(payload)["input"]
        captured_inputs.append(inputs)
        start = len(captured_inputs) * 10
        return httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [float(start + index), 0.0]}
                    for index, _ in enumerate(inputs)
                ]
            },
        )

    client = EmbeddingClient(
        provider=_provider(),
        model=_model(batch_size=2),
        http_client=_client_with_handler(handler),
    )

    result = client.embed_texts(
        EmbeddingRequest(
            provider_id=1,
            model_id=2,
            texts=["第一段", "第二段", "第三段", "第四段", "第五段"],
        )
    )

    assert captured_inputs == [["第一段", "第二段"], ["第三段", "第四段"], ["第五段"]]
    assert result.embeddings == [
        [10.0, 0.0],
        [11.0, 0.0],
        [20.0, 0.0],
        [21.0, 0.0],
        [30.0, 0.0],
    ]


def test_embed_texts_requires_provider_base_url():
    client = EmbeddingClient(
        provider=_provider(base_url=None),
        model=_model(),
        http_client=httpx.Client(transport=httpx.MockTransport(lambda request: None)),
    )

    with pytest.raises(EmbeddingClientError, match="基础 URL"):
        client.embed_texts(EmbeddingRequest(provider_id=1, model_id=2, texts=["文本"]))


def test_embed_texts_requires_api_key_for_remote_provider():
    client = EmbeddingClient(
        provider=_provider(api_key=None),
        model=_model(),
        http_client=httpx.Client(transport=httpx.MockTransport(lambda request: None)),
    )

    with pytest.raises(EmbeddingClientError, match="API Key"):
        client.embed_texts(EmbeddingRequest(provider_id=1, model_id=2, texts=["文本"]))


def test_embed_texts_allows_missing_api_key_for_local_provider():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})

    client = EmbeddingClient(
        provider=_provider(base_url="http://localhost:11434/v1", api_key=None),
        model=_model(),
        http_client=_client_with_handler(handler),
    )

    result = client.embed_texts(
        EmbeddingRequest(provider_id=1, model_id=2, texts=["文本"])
    )

    assert result.embeddings == [[0.1, 0.2]]


def test_embed_texts_raises_on_http_error_response():
    client = EmbeddingClient(
        provider=_provider(),
        model=_model(),
        http_client=_client_with_handler(
            lambda request: httpx.Response(429, json={"error": {"message": "限流"}})
        ),
    )

    with pytest.raises(EmbeddingClientError, match="429"):
        client.embed_texts(EmbeddingRequest(provider_id=1, model_id=2, texts=["文本"]))


def test_embed_texts_requires_embedding_in_each_data_item():
    client = EmbeddingClient(
        provider=_provider(),
        model=_model(),
        http_client=_client_with_handler(
            lambda request: httpx.Response(200, json={"data": [{"index": 0}]})
        ),
    )

    with pytest.raises(EmbeddingClientError, match="embedding"):
        client.embed_texts(EmbeddingRequest(provider_id=1, model_id=2, texts=["文本"]))


def test_embed_texts_rejects_inconsistent_embedding_dimensions():
    client = EmbeddingClient(
        provider=_provider(),
        model=_model(),
        http_client=_client_with_handler(
            lambda request: httpx.Response(
                200,
                json={
                    "data": [
                        {"embedding": [0.1, 0.2]},
                        {"embedding": [0.3]},
                    ]
                },
            )
        ),
    )

    with pytest.raises(EmbeddingClientError, match="维度"):
        client.embed_texts(
            EmbeddingRequest(provider_id=1, model_id=2, texts=["第一段", "第二段"])
        )
