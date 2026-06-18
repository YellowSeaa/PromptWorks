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


DEFAULT_EMBEDDING_BATCH_SIZE = 32
MAX_EMBEDDING_BATCH_SIZE = 128
DEFAULT_EMBEDDING_MAX_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


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
        model_name = self._resolve_model_name()
        dimensions = getattr(self._model, "embedding_dimensions", None)
        batch_size = self._resolve_batch_size()

        texts = list(request.texts)
        embeddings: list[list[float]] = []
        expected_dimensions: int | None = None
        for batch_texts in _chunked(texts, batch_size):
            payload: dict[str, Any] = {
                "model": model_name,
                "input": batch_texts,
            }
            if isinstance(dimensions, int) and dimensions > 0:
                payload["dimensions"] = dimensions

            response = self._post_embeddings(
                base_url=base_url,
                payload=payload,
            )

            if response.status_code < 200 or response.status_code >= 300:
                raise EmbeddingClientError(
                    f"embedding 请求失败，HTTP {response.status_code}: {response.text}"
                )

            data = _ensure_mapping(response.json()).get("data")
            if not isinstance(data, list) or not data:
                raise EmbeddingClientError("embedding 响应缺少 data。")

            batch_embeddings: list[list[float]] = []
            for item in data:
                embedding = _extract_embedding(item)
                if expected_dimensions is None:
                    expected_dimensions = len(embedding)
                elif len(embedding) != expected_dimensions:
                    raise EmbeddingClientError("embedding 向量维度不一致。")
                batch_embeddings.append(embedding)

            if len(batch_embeddings) != len(batch_texts):
                raise EmbeddingClientError("embedding 响应数量与输入数量不一致。")
            embeddings.extend(batch_embeddings)

        if len(embeddings) != len(texts):
            raise EmbeddingClientError("embedding 响应数量与输入数量不一致。")

        return EmbeddingResult(
            provider_id=request.provider_id,
            model_id=request.model_id,
            model_name=model_name,
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

    def _resolve_batch_size(self) -> int:
        batch_size = getattr(self._model, "embedding_batch_size", None)
        if not isinstance(batch_size, int) or isinstance(batch_size, bool):
            return DEFAULT_EMBEDDING_BATCH_SIZE
        if batch_size < 1:
            return DEFAULT_EMBEDDING_BATCH_SIZE
        return min(batch_size, MAX_EMBEDDING_BATCH_SIZE)

    def _post_embeddings(
        self,
        *,
        base_url: str,
        payload: dict[str, Any],
    ) -> httpx.Response:
        last_transport_error: httpx.TransportError | None = None
        for attempt in range(1, DEFAULT_EMBEDDING_MAX_ATTEMPTS + 1):
            try:
                response = self._http_client.post(
                    f"{base_url}/embeddings",
                    content=_json_bytes(payload),
                    headers=self._build_headers(base_url),
                )
            except httpx.TransportError as exc:
                last_transport_error = exc
                if attempt < DEFAULT_EMBEDDING_MAX_ATTEMPTS:
                    continue
                raise EmbeddingClientError(
                    f"embedding 请求失败，网络异常: {exc}"
                ) from exc

            if response.status_code < 200 or response.status_code >= 300:
                if (
                    _is_retryable_status_code(response.status_code)
                    and attempt < DEFAULT_EMBEDDING_MAX_ATTEMPTS
                ):
                    continue
                raise EmbeddingClientError(
                    f"embedding 请求失败，HTTP {response.status_code}: {response.text}"
                )

            return response

        if last_transport_error is not None:
            raise EmbeddingClientError(
                f"embedding 请求失败，网络异常: {last_transport_error}"
            ) from last_transport_error
        raise EmbeddingClientError("embedding 请求失败，重试后仍未获得有效响应。")


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


def _is_retryable_status_code(status_code: int) -> bool:
    if status_code in RETRYABLE_STATUS_CODES:
        return True
    return 500 <= status_code <= 599


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    import json

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def _chunked(values: list[str], batch_size: int) -> list[list[str]]:
    return [
        values[index : index + batch_size]
        for index in range(0, len(values), batch_size)
    ]


__all__ = [
    "EmbeddingClient",
    "EmbeddingClientError",
    "EmbeddingRequest",
    "EmbeddingResult",
]
