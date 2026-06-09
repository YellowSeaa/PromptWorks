from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LLMModelBase(BaseModel):
    name: str = Field(..., description="模型唯一名称")
    capability: str | None = Field(
        default=None, description="可选的能力标签，例如对话、推理"
    )
    quota: str | None = Field(default=None, description="配额或调用策略说明")
    concurrency_limit: int = Field(
        default=5,
        ge=1,
        le=50,
        description="执行测试任务时的最大并发请求数",
    )
    context_length: int | None = Field(
        default=None,
        ge=1,
        le=2_000_000,
        description="模型上下文长度，按近似 token 数配置；为空表示不截断",
    )


class LLMModelCreate(LLMModelBase):
    pass


class LLMModelUpdate(BaseModel):
    capability: str | None = Field(default=None, description="可选的能力标签")
    quota: str | None = Field(default=None, description="配额或调用策略说明")
    concurrency_limit: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="执行测试任务时的最大并发请求数",
    )
    context_length: int | None = Field(
        default=None,
        ge=1,
        le=2_000_000,
        description="模型上下文长度，按近似 token 数配置；为空表示不截断",
    )


class LLMModelRead(LLMModelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMProviderBase(BaseModel):
    provider_name: str = Field(..., description="展示用名称，例如 OpenAI")
    provider_key: str | None = Field(
        default=None, description="常用提供方标识，用于自动补全默认信息"
    )
    base_url: str | None = Field(default=None, description="调用使用的基础 URL")
    logo_emoji: str | None = Field(
        default=None, max_length=16, description="用于展示的表情符号"
    )
    logo_url: str | None = Field(default=None, description="可选的品牌 Logo URL")
    is_custom: bool | None = Field(
        default=None, description="是否为自定义提供方，未指定时由后端推断"
    )


class LLMProviderCreate(LLMProviderBase):
    api_key: str = Field(..., min_length=1, description="访问该提供方所需的密钥")


class LLMProviderUpdate(BaseModel):
    provider_name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    logo_emoji: str | None = Field(default=None, max_length=16)
    logo_url: str | None = None
    is_custom: bool | None = None
    default_model_name: str | None = None


class LLMProviderRead(BaseModel):
    id: int
    provider_key: str | None
    provider_name: str
    base_url: str | None
    logo_emoji: str | None
    logo_url: str | None
    is_custom: bool
    is_archived: bool
    default_model_name: str | None
    masked_api_key: str
    models: list[LLMModelRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnownLLMProvider(BaseModel):
    key: str
    name: str
    description: str | None = None
    base_url: str | None = None
    logo_emoji: str | None = None
    logo_url: str | None = None


class LLMUsageMessage(BaseModel):
    role: str = Field(..., description="消息角色，例如 user、assistant")
    content: Any = Field(..., description="与 OpenAI 兼容的消息内容")


class LLMUsageLogRead(BaseModel):
    id: int
    provider_id: int | None
    provider_name: str | None
    provider_logo_emoji: str | None
    provider_logo_url: str | None
    model_id: int | None
    model_name: str
    response_text: str | None
    messages: list[LLMUsageMessage] = Field(default_factory=list)
    temperature: float | None
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    prompt_id: int | None
    prompt_version_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
