from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    provider_id: int
    model_id: int
    texts: list[str]


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    provider_id: int
    model_id: int
    model_name: str
    embeddings: list[list[float]]


class EmbeddingClientError(RuntimeError):
    """统一 embedding 调用失败时抛出的业务异常。"""


class EmbeddingClient:
    def __init__(
        self,
        *,
        provider: Any,
        model: Any,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._http_client = http_client or httpx.Client()

    def embed_texts(self, request: EmbeddingRequest) -> EmbeddingResult:
        base_url = self._resolve_base_url()
        self._ensure_api_key_if_needed(base_url)

        payload: dict[str, Any] = {
            "model": self._resolve_model_name(),
            "input": list(request.texts),
        }
        dimensions = getattr(self._model, "embedding_dimensions", None)
        if isinstance(dimensions, int) and dimensions > 0:
            payload["dimensions"] = dimensions

        response = self._http_client.post(
            f"{base_url}/embeddings",
            content=_json_bytes(payload),
            headers=self._build_headers(base_url),
        )

        if response.status_code < 200 or response.status_code >= 300:
            raise EmbeddingClientError(
                f"embedding 请求失败，HTTP {response.status_code}: {response.text}"
            )

        data = _ensure_mapping(response.json()).get("data")
        if not isinstance(data, list) or not data:
            raise EmbeddingClientError("embedding 响应缺少 data。")

        embeddings: list[list[float]] = []
        expected_dimensions: int | None = None
        for item in data:
            embedding = _extract_embedding(item)
            if expected_dimensions is None:
                expected_dimensions = len(embedding)
            elif len(embedding) != expected_dimensions:
                raise EmbeddingClientError("embedding 向量维度不一致。")
            embeddings.append(embedding)

        if len(embeddings) != len(request.texts):
            raise EmbeddingClientError("embedding 响应数量与输入数量不一致。")

        return EmbeddingResult(
            provider_id=request.provider_id,
            model_id=request.model_id,
            model_name=self._resolve_model_name(),
            embeddings=embeddings,
        )

    def _resolve_base_url(self) -> str:
        base_url = getattr(self._provider, "base_url", None)
        if not base_url:
            raise EmbeddingClientError("embedding 提供方缺少基础 URL。")
        return str(base_url).rstrip("/")

    def _resolve_model_name(self) -> str:
        model_name = getattr(self._model, "name", None)
        if not model_name:
            raise EmbeddingClientError("embedding 模型缺少名称。")
        api_style = getattr(self._model, "embedding_api_style", None)
        if api_style in (None, "", "openai_compatible"):
            return str(model_name)
        raise EmbeddingClientError(f"暂不支持的 embedding 接口类型: {api_style}")

    def _build_headers(self, base_url: str) -> dict[str, str]:
        headers = {"content-type": "application/json"}
        api_key = getattr(self._provider, "api_key", None)
        if api_key:
            headers["authorization"] = f"Bearer {api_key}"
        return headers

    def _ensure_api_key_if_needed(self, base_url: str) -> None:
        api_key = getattr(self._provider, "api_key", None)
        if api_key:
            return
        if _is_local_base_url(base_url):
            return
        raise EmbeddingClientError("远程 embedding 提供方缺少 API Key。")


def _ensure_mapping(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return dict(raw)
    raise EmbeddingClientError("embedding 响应格式无效。")


def _extract_embedding(item: Any) -> list[float]:
    if not isinstance(item, Mapping):
        raise EmbeddingClientError("embedding 响应项格式无效。")
    embedding = item.get("embedding")
    if not isinstance(embedding, Sequence) or isinstance(embedding, (str, bytes)):
        raise EmbeddingClientError("embedding 响应缺少 data[].embedding。")

    result: list[float] = []
    for value in embedding:
        if not isinstance(value, (int, float)):
            raise EmbeddingClientError("embedding 向量包含非法值。")
        result.append(float(value))
    return result


def _is_local_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    return host in {"localhost", "127.0.0.1", "::1"}


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    import json

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


__all__ = [
    "EmbeddingClient",
    "EmbeddingClientError",
    "EmbeddingRequest",
    "EmbeddingResult",
]
