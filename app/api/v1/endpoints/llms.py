from __future__ import annotations

import json
import time
from typing import Any, Iterator, Mapping, Sequence, cast

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.llm_provider_registry import (
    get_provider_defaults,
    iter_common_providers,
)
from app.core.logging_config import get_logger
from app.db.session import get_db
from app.models.llm_provider import LLMModel, LLMProvider
from app.models.usage import LLMUsageLog
from app.schemas.llm_provider import (
    KnownLLMProvider,
    LLMModelCreate,
    LLMModelUpdate,
    LLMModelRead,
    LLMProviderCreate,
    LLMProviderRead,
    LLMProviderUpdate,
    LLMUsageLogRead,
    LLMUsageMessage,
)
from app.services.llm_usage import list_quick_test_usage_logs

router = APIRouter()

logger = get_logger("promptworks.api.llms")
DEFAULT_INVOKE_TIMEOUT = 30.0


class ChatMessage(BaseModel):
    role: str = Field(..., description="聊天消息的角色，例如 system、user、assistant")
    content: Any = Field(..., description="遵循 OpenAI 聊天格式的消息内容")


class LLMInvocationRequest(BaseModel):
    messages: list[ChatMessage]
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="额外的 OpenAI 兼容参数"
    )
    model: str | None = Field(default=None, description="覆盖使用的模型名称")
    model_id: int | None = Field(default=None, description="指定已配置模型的 ID")
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="对话生成温度，范围 0~2",
    )
    prompt_id: int | None = Field(
        default=None, description="可选的 Prompt ID，便于溯源"
    )
    prompt_version_id: int | None = Field(
        default=None, description="可选的 Prompt 版本 ID"
    )
    persist_usage: bool = Field(
        default=False, description="是否将本次调用记录到用量日志"
    )


class LLMStreamInvocationRequest(LLMInvocationRequest):
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="对话生成温度，范围 0~2",
    )


def _normalize_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    return base_url.rstrip("/")


def _mask_api_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 6:
        return "*" * len(api_key)
    prefix = api_key[:4]
    suffix = api_key[-2:]
    return f"{prefix}{'*' * (len(api_key) - 6)}{suffix}"


def _serialize_provider(provider: LLMProvider) -> LLMProviderRead:
    models = [
        LLMModelRead.model_validate(model, from_attributes=True)
        for model in sorted(provider.models, key=lambda item: item.created_at)
    ]
    defaults = get_provider_defaults(provider.provider_key)
    resolved_base_url = provider.base_url or (defaults.base_url if defaults else None)
    resolved_logo_url = provider.logo_url or (defaults.logo_url if defaults else None)
    resolved_logo_emoji = provider.logo_emoji
    if resolved_logo_emoji is None and defaults:
        resolved_logo_emoji = defaults.logo_emoji
    return LLMProviderRead(
        id=provider.id,
        provider_key=provider.provider_key,
        provider_name=provider.provider_name,
        base_url=resolved_base_url,
        logo_emoji=resolved_logo_emoji,
        logo_url=resolved_logo_url,
        is_custom=provider.is_custom,
        is_archived=provider.is_archived,
        default_model_name=provider.default_model_name,
        masked_api_key=_mask_api_key(provider.api_key),
        models=models,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def _resolve_base_url_or_400(provider: LLMProvider) -> str:
    base_url = provider.base_url or (
        defaults.base_url
        if (defaults := get_provider_defaults(provider.provider_key))
        else None
    )
    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该提供者未配置基础 URL。",
        )
    return cast(str, _normalize_base_url(base_url))


def _get_provider_or_404(
    db: Session, provider_id: int, *, include_archived: bool = False
) -> LLMProvider:
    provider = db.get(LLMProvider, provider_id)
    if not provider or (provider.is_archived and not include_archived):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="未找到指定的提供者"
        )
    return provider


def _determine_model_for_invocation(
    db: Session, provider: LLMProvider, payload: LLMInvocationRequest
) -> tuple[str, LLMModel | None]:
    model_name: str | None = None
    target_model: LLMModel | None = None

    if payload.model_id is not None:
        stmt = select(LLMModel).where(
            LLMModel.id == payload.model_id, LLMModel.provider_id == provider.id
        )
        target_model = db.scalar(stmt)
        if not target_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定的模型不存在",
            )
    elif payload.model:
        stmt = select(LLMModel).where(
            LLMModel.provider_id == provider.id, LLMModel.name == payload.model
        )
        target_model = db.scalar(stmt)
        if not target_model:
            model_name = payload.model

    if target_model:
        model_name = target_model.name

    if not model_name:
        if provider.default_model_name:
            model_name = provider.default_model_name
        else:
            fallback_model = next(iter(provider.models), None)
            if fallback_model:
                model_name = fallback_model.name

    if not model_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未能确定调用模型，请在请求中指定 model 或先配置默认模型。",
        )

    return model_name, target_model


def _resolve_provider_defaults_for_create(
    data: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    normalized_key = _normalize_key(data.get("provider_key"))
    normalized_name = _normalize_key(data.get("provider_name"))
    provider_key = normalized_key or normalized_name
    defaults = get_provider_defaults(provider_key)

    resolved_base_url = _normalize_base_url(
        data.get("base_url") or (defaults.base_url if defaults else None)
    )

    resolved_is_custom = data.get("is_custom")
    if resolved_is_custom is None:
        resolved_is_custom = defaults is None

    if resolved_is_custom and not resolved_base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自定义提供者必须配置基础 URL。",
        )
    if not resolved_is_custom and not resolved_base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该提供者需要配置基础 URL。",
        )

    provider_name = data.get("provider_name") or (defaults.name if defaults else None)
    if not provider_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供提供者名称。",
        )

    data.update(
        {
            "provider_key": defaults.key if defaults else provider_key,
            "provider_name": provider_name,
            "base_url": resolved_base_url,
            "logo_emoji": data.get("logo_emoji")
            or (defaults.logo_emoji if defaults else None),
            "logo_url": data.get("logo_url")
            or (defaults.logo_url if defaults else None),
            "is_custom": resolved_is_custom,
        }
    )
    return data, provider_key


@router.get("/common", response_model=list[KnownLLMProvider])
def list_common_providers() -> list[KnownLLMProvider]:
    """返回预置的常用提供方信息。"""

    items = [
        KnownLLMProvider(
            key=provider.key,
            name=provider.name,
            description=provider.description,
            base_url=provider.base_url,
            logo_emoji=provider.logo_emoji,
            logo_url=provider.logo_url,
        )
        for provider in iter_common_providers()
    ]
    return items


@router.get("/quick-test/history", response_model=list[LLMUsageLogRead])
def list_quick_test_history(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="返回的历史记录数量"),
    offset: int = Query(0, ge=0, description="跳过的历史记录数量"),
) -> list[LLMUsageLogRead]:
    """返回快速测试产生的最近调用记录。"""

    logs = list_quick_test_usage_logs(db, limit=limit, offset=offset)
    history: list[LLMUsageLogRead] = []
    for log in logs:
        provider = log.provider
        message_items: list[LLMUsageMessage] = []
        if isinstance(log.messages, list):
            for item in log.messages:
                if not isinstance(item, dict):
                    continue
                try:
                    message_items.append(LLMUsageMessage.model_validate(item))
                except ValidationError:
                    role = str(item.get("role", "user"))
                    message_items.append(
                        LLMUsageMessage(role=role, content=item.get("content"))
                    )

        history.append(
            LLMUsageLogRead(
                id=log.id,
                provider_id=log.provider_id,
                provider_name=provider.provider_name if provider else None,
                provider_logo_emoji=provider.logo_emoji if provider else None,
                provider_logo_url=provider.logo_url if provider else None,
                model_id=log.model_id,
                model_name=log.model_name,
                response_text=log.response_text,
                messages=message_items,
                temperature=log.temperature,
                latency_ms=log.latency_ms,
                prompt_tokens=log.prompt_tokens,
                completion_tokens=log.completion_tokens,
                total_tokens=log.total_tokens,
                prompt_id=log.prompt_id,
                prompt_version_id=log.prompt_version_id,
                created_at=log.created_at,
            )
        )

    return history


@router.get("/", response_model=list[LLMProviderRead])
def list_llm_providers(
    *,
    db: Session = Depends(get_db),
    provider_name: str | None = Query(default=None, alias="provider"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[LLMProviderRead]:
    """返回 LLM 提供者列表，默认排除已归档记录。"""

    logger.info(
        "查询 LLM 提供者列表: provider=%s limit=%s offset=%s",
        provider_name,
        limit,
        offset,
    )

    stmt = (
        select(LLMProvider)
        .where(LLMProvider.is_archived.is_(False))
        .order_by(LLMProvider.updated_at.desc())
        .options(selectinload(LLMProvider.models))
        .offset(offset)
        .limit(limit)
    )
    if provider_name:
        stmt = stmt.where(LLMProvider.provider_name.ilike(f"%{provider_name}%"))

    providers = list(db.scalars(stmt))
    return [_serialize_provider(provider) for provider in providers]


@router.post("/", response_model=LLMProviderRead, status_code=status.HTTP_201_CREATED)
def create_llm_provider(
    *,
    db: Session = Depends(get_db),
    payload: LLMProviderCreate,
) -> LLMProviderRead:
    """创建新的 LLM 提供者卡片，初始模型列表为空。"""

    data = payload.model_dump()
    data, provider_key = _resolve_provider_defaults_for_create(data)

    duplicate_stmt = select(LLMProvider).where(
        LLMProvider.provider_name == data["provider_name"],
        LLMProvider.base_url == data["base_url"],
        LLMProvider.is_archived.is_(False),
    )
    if db.scalar(duplicate_stmt):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已存在相同提供方与基础地址的配置。",
        )

    provider = LLMProvider(**data)
    db.add(provider)
    db.commit()
    db.refresh(provider)

    logger.info(
        "创建 LLM 提供者成功: id=%s provider=%s key=%s",
        provider.id,
        provider.provider_name,
        provider_key,
    )
    return _serialize_provider(provider)


@router.get("/{provider_id}", response_model=LLMProviderRead)
def get_llm_provider(
    *, db: Session = Depends(get_db), provider_id: int
) -> LLMProviderRead:
    """获取单个 LLM 提供者详情。"""

    provider = _get_provider_or_404(db, provider_id, include_archived=True)
    return _serialize_provider(provider)


@router.patch("/{provider_id}", response_model=LLMProviderRead)
def update_llm_provider(
    *,
    db: Session = Depends(get_db),
    provider_id: int,
    payload: LLMProviderUpdate,
) -> LLMProviderRead:
    """更新已有的 LLM 提供者配置。"""

    provider = _get_provider_or_404(db, provider_id)
    update_data = payload.model_dump(exclude_unset=True)

    if "base_url" in update_data:
        update_data["base_url"] = _normalize_base_url(update_data["base_url"])
        if update_data["base_url"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该提供者需要配置基础 URL。",
            )
    if "api_key" in update_data and update_data["api_key"]:
        logger.info("更新 LLM 提供者密钥: provider_id=%s", provider.id)

    for key, value in update_data.items():
        setattr(provider, key, value)

    defaults = get_provider_defaults(provider.provider_key)
    if not provider.is_custom and not provider.base_url and defaults:
        provider.base_url = defaults.base_url

    if provider.is_custom and not provider.base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自定义提供者必须配置基础 URL。",
        )
    if not provider.is_custom and not provider.base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该提供者需要配置基础 URL。",
        )

    db.commit()
    db.refresh(provider)

    logger.info("更新 LLM 提供者成功: id=%s", provider.id)
    return _serialize_provider(provider)


@router.post(
    "/{provider_id}/models",
    response_model=LLMModelRead,
    status_code=status.HTTP_201_CREATED,
)
def create_llm_model(
    *,
    db: Session = Depends(get_db),
    provider_id: int,
    payload: LLMModelCreate,
) -> LLMModelRead:
    """为指定提供者新增模型。"""

    provider = _get_provider_or_404(db, provider_id)
    data = payload.model_dump()

    model = LLMModel(provider_id=provider.id, **data)
    db.add(model)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该模型名称已存在，请勿重复添加。",
        ) from None
    db.refresh(model)

    logger.info("新增模型成功: provider_id=%s model=%s", provider.id, model.name)
    return LLMModelRead.model_validate(model, from_attributes=True)


@router.patch(
    "/{provider_id}/models/{model_id}",
    response_model=LLMModelRead,
)
def update_llm_model(
    *,
    db: Session = Depends(get_db),
    provider_id: int,
    model_id: int,
    payload: LLMModelUpdate,
) -> LLMModelRead:
    """更新模型属性，如并发配置。"""

    _ = _get_provider_or_404(db, provider_id)
    stmt = select(LLMModel).where(
        LLMModel.id == model_id, LLMModel.provider_id == provider_id
    )
    model = db.scalar(stmt)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定的模型",
        )

    update_data = payload.model_dump(exclude_unset=True)
    concurrency = update_data.get("concurrency_limit")
    if concurrency is not None:
        model.concurrency_limit = concurrency

    if "capability" in update_data:
        model.capability = update_data["capability"]
    if "quota" in update_data:
        model.quota = update_data["quota"]

    db.commit()
    db.refresh(model)

    logger.info(
        "更新模型成功: provider_id=%s model_id=%s concurrency=%s",
        provider_id,
        model_id,
        model.concurrency_limit,
    )
    return LLMModelRead.model_validate(model, from_attributes=True)


@router.delete(
    "/{provider_id}/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_llm_model(
    *,
    db: Session = Depends(get_db),
    provider_id: int,
    model_id: int,
) -> Response:
    """删除指定模型，若无剩余模型则自动归档提供者。"""

    provider = _get_provider_or_404(db, provider_id, include_archived=True)
    model_stmt = select(LLMModel).where(
        LLMModel.id == model_id, LLMModel.provider_id == provider.id
    )
    model = db.scalar(model_stmt)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定的模型",
        )

    db.delete(model)
    db.flush()

    remaining = db.scalar(
        select(func.count(LLMModel.id)).where(LLMModel.provider_id == provider.id)
    )
    if remaining == 0:
        provider.is_archived = True

    db.commit()

    logger.info(
        "删除模型成功: provider_id=%s model_id=%s remaining=%s",
        provider.id,
        model_id,
        remaining,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_llm_provider(
    *,
    db: Session = Depends(get_db),
    provider_id: int,
) -> Response:
    """删除整个提供方配置，级联清理其下所有模型。"""

    provider = _get_provider_or_404(db, provider_id, include_archived=True)
    db.delete(provider)
    db.commit()

    logger.info("删除 LLM 提供者成功: id=%s", provider_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{provider_id}/invoke")
def invoke_llm(
    *,
    db: Session = Depends(get_db),
    provider_id: int,
    payload: LLMInvocationRequest,
) -> dict[str, Any]:
    """使用兼容 OpenAI Chat Completion 的方式调用目标 LLM。"""

    provider = _get_provider_or_404(db, provider_id)
    model_name, target_model = _determine_model_for_invocation(db, provider, payload)
    base_url = _resolve_base_url_or_400(provider)

    request_payload: dict[str, Any] = dict(payload.parameters)
    if payload.temperature is not None:
        request_payload.setdefault("temperature", payload.temperature)
    request_payload["model"] = model_name
    request_messages = [message.model_dump() for message in payload.messages]
    request_payload["messages"] = request_messages

    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }

    url = f"{base_url}/chat/completions"
    logger.info("调用外部 LLM 接口: provider_id=%s url=%s", provider.id, url)
    logger.debug("LLM 请求参数: %s", request_payload)

    start_time = time.perf_counter()
    try:
        response = httpx.post(
            url,
            headers=headers,
            json=request_payload,
            timeout=DEFAULT_INVOKE_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        logger.error(
            "调用外部 LLM 接口出现网络异常: provider_id=%s 错误=%s",
            provider.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {"message": response.text}
        logger.error(
            "外部 LLM 接口返回错误: provider_id=%s 状态码=%s 响应=%s",
            provider.id,
            response.status_code,
            error_payload,
        )
        raise HTTPException(status_code=response.status_code, detail=error_payload)

    elapsed = getattr(response, "elapsed", None)
    if elapsed is not None:
        latency_ms = int(elapsed.total_seconds() * 1000)
    else:
        latency_ms = int((time.perf_counter() - start_time) * 1000)

    if latency_ms >= 0:
        logger.info(
            "外部 LLM 接口调用成功: provider_id=%s 耗时 %.2fms",
            provider.id,
            max(latency_ms, 0),
        )
    else:
        logger.info("外部 LLM 接口调用成功: provider_id=%s", provider.id)

    try:
        response_payload = response.json()
    except ValueError as exc:
        logger.error(
            "LLM 响应解析失败: provider_id=%s model=%s", provider.id, model_name
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM 响应解析失败。"
        ) from exc

    if payload.persist_usage:
        usage_obj = (
            response_payload.get("usage")
            if isinstance(response_payload.get("usage"), Mapping)
            else {}
        )
        prompt_tokens = (
            int(usage_obj.get("prompt_tokens"))
            if isinstance(usage_obj, Mapping)
            and isinstance(usage_obj.get("prompt_tokens"), (int, float))
            else None
        )
        completion_tokens = (
            int(usage_obj.get("completion_tokens"))
            if isinstance(usage_obj, Mapping)
            and isinstance(usage_obj.get("completion_tokens"), (int, float))
            else None
        )
        total_tokens = (
            int(usage_obj.get("total_tokens"))
            if isinstance(usage_obj, Mapping)
            and isinstance(usage_obj.get("total_tokens"), (int, float))
            else None
        )
        if total_tokens is None and any(
            value is not None for value in (prompt_tokens, completion_tokens)
        ):
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

        choices = response_payload.get("choices")
        generated_chunks: list[str] = []
        if isinstance(choices, Sequence):
            for choice in choices:
                if not isinstance(choice, Mapping):
                    continue
                message_obj = choice.get("message")
                if isinstance(message_obj, Mapping) and isinstance(
                    message_obj.get("content"), str
                ):
                    generated_chunks.append(message_obj["content"])
                    continue
                text_content = choice.get("text")
                if isinstance(text_content, str):
                    generated_chunks.append(text_content)
        response_text = "".join(generated_chunks)

        original_parameters = dict(payload.parameters)
        if payload.temperature is not None:
            original_parameters.setdefault("temperature", payload.temperature)

        log_entry = LLMUsageLog(
            provider_id=provider.id,
            model_id=target_model.id if target_model else None,
            model_name=model_name,
            source="quick_test",
            prompt_id=payload.prompt_id,
            prompt_version_id=payload.prompt_version_id,
            messages=request_messages,
            parameters=original_parameters or None,
            response_text=response_text or None,
            temperature=payload.temperature,
            latency_ms=max(latency_ms, 0),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        try:
            db.add(log_entry)
            db.commit()
            logger.info(
                "非流式调用已记录用量: provider_id=%s model=%s tokens=%s",
                provider.id,
                model_name,
                {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                },
            )
        except Exception:  # pragma: no cover - 防御性回滚
            db.rollback()
            logger.exception(
                "保存 LLM 调用日志失败: provider_id=%s model=%s",
                provider.id,
                model_name,
            )

    return response_payload


@router.post(
    "/{provider_id}/invoke/stream",
    response_class=StreamingResponse,
)
def stream_invoke_llm(
    *,
    db: Session = Depends(get_db),
    provider_id: int,
    payload: LLMStreamInvocationRequest,
) -> StreamingResponse:
    """以流式方式调用目标 LLM，并转发 OpenAI 兼容的事件流。"""

    provider = _get_provider_or_404(db, provider_id)
    model_name, target_model = _determine_model_for_invocation(db, provider, payload)
    base_url = _resolve_base_url_or_400(provider)

    request_payload: dict[str, Any] = dict(payload.parameters)
    request_payload.pop("stream", None)
    request_payload["temperature"] = payload.temperature
    request_payload["model"] = model_name
    request_payload["messages"] = [message.model_dump() for message in payload.messages]
    request_payload["stream"] = True

    stream_options = request_payload.get("stream_options")
    if isinstance(stream_options, dict):
        stream_options.setdefault("include_usage", True)
    else:
        request_payload["stream_options"] = {"include_usage": True}

    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }

    url = f"{base_url}/chat/completions"
    logger.info(
        "启动流式 LLM 调用: provider_id=%s model=%s url=%s",
        provider.id,
        model_name,
        url,
    )
    logger.debug("LLM 流式请求参数: %s", request_payload)

    start_time = time.perf_counter()
    usage_summary: dict[str, int | None] | None = None
    generated_chunks: list[str] = []
    should_persist = True
    request_messages = [message.model_dump() for message in payload.messages]
    original_parameters = dict(payload.parameters)

    def _process_event(lines: list[str]) -> None:
        nonlocal usage_summary
        if not lines:
            return
        data_segments: list[str] = []
        for item in lines:
            if item.startswith(":"):
                continue
            if item.startswith("data:"):
                data_segments.append(item[5:].lstrip())
        if not data_segments:
            return
        data_str = "\n".join(data_segments).strip()
        if not data_str:
            return
        if data_str == "[DONE]":
            return
        try:
            payload_obj = json.loads(data_str)
        except json.JSONDecodeError:
            logger.debug("忽略无法解析的流式分片: %s", data_str)
            return

        usage = payload_obj.get("usage")
        if isinstance(usage, dict):
            usage_summary = {
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            }

        for choice in payload_obj.get("choices", []):
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if content:
                generated_chunks.append(content)
                continue
            message_obj = choice.get("message")
            if isinstance(message_obj, dict):
                content = message_obj.get("content")
                if content:
                    generated_chunks.append(content)

    def _persist_usage() -> None:
        if not should_persist:
            return
        summary = usage_summary or {}
        response_text = "".join(generated_chunks)
        if not response_text and not summary:
            return

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_entry = LLMUsageLog(
            provider_id=provider.id,
            model_id=target_model.id if target_model else None,
            model_name=model_name,
            source="quick_test",
            prompt_id=payload.prompt_id,
            prompt_version_id=payload.prompt_version_id,
            messages=request_messages,
            parameters=original_parameters or None,
            response_text=response_text or None,
            temperature=payload.temperature,
            latency_ms=latency_ms,
            prompt_tokens=summary.get("prompt_tokens"),
            completion_tokens=summary.get("completion_tokens"),
            total_tokens=summary.get("total_tokens"),
        )
        try:
            db.add(log_entry)
            db.commit()
            logger.info(
                "流式调用完成: provider_id=%s model=%s tokens=%s",
                provider.id,
                model_name,
                summary,
            )
        except Exception:  # pragma: no cover - 防御性回滚
            db.rollback()
            logger.exception(
                "保存 LLM 调用日志失败: provider_id=%s model=%s",
                provider.id,
                model_name,
            )

    def _event_stream() -> Iterator[bytes]:
        nonlocal should_persist
        event_lines: list[str] = []
        try:
            with httpx.stream(
                "POST",
                url,
                headers=headers,
                json=request_payload,
                timeout=DEFAULT_INVOKE_TIMEOUT,
            ) as response:
                if response.status_code >= 400:
                    should_persist = False
                    error_body = response.read()
                    decoded = error_body.decode("utf-8", errors="ignore")
                    try:
                        error_payload = json.loads(decoded)
                    except ValueError:
                        error_payload = {"message": decoded}
                    logger.error(
                        "流式调用返回错误: provider_id=%s 状态码=%s 响应=%s",
                        provider.id,
                        response.status_code,
                        error_payload,
                    )
                    raise HTTPException(
                        status_code=response.status_code, detail=error_payload
                    )

                for line in response.iter_lines():
                    if line is None:
                        continue
                    if line == "":
                        _process_event(event_lines)
                        event_lines = []
                        yield b"\n"
                        continue
                    event_lines.append(line)
                    yield (line + "\n").encode("utf-8")

                if event_lines:
                    _process_event(event_lines)

        except httpx.HTTPError as exc:
            should_persist = False
            logger.error(
                "流式调用外部 LLM 出现异常: provider_id=%s 错误=%s",
                provider.id,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
            ) from exc
        finally:
            _persist_usage()

    headers_extra = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        _event_stream(), media_type="text/event-stream", headers=headers_extra
    )
