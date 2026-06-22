from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

LLM_MODEL_TYPES = {"chat", "embedding", "rerank"}
EMBEDDING_API_STYLES = {"openai_compatible"}


class LLMCostTier(BaseModel):
    up_to_context_tokens: int = Field(
        ..., ge=1, le=2_000_000, description="该价格阶梯适用的最大上下文长度"
    )
    input_per_unit: float | None = Field(
        default=None, ge=0, description="该阶梯每计价单位输入 tokens 成本"
    )
    output_per_unit: float | None = Field(
        default=None, ge=0, description="该阶梯每计价单位输出 tokens 成本"
    )


class LLMModelBase(BaseModel):
    name: str = Field(..., description="模型唯一名称")
    model_type: str = Field(
        default="chat",
        description="模型用途类型，可选 chat、embedding、rerank",
    )
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
    cost_currency: str = Field(default="USD", max_length=12, description="模型计价币种")
    cost_display_currency: str = Field(
        default="CNY", max_length=12, description="折算后的展示币种"
    )
    cost_exchange_rate: float = Field(
        default=7.2, gt=0, description="从计价币种折算到展示币种的汇率"
    )
    cost_pricing_unit: int = Field(
        default=1_000_000, ge=1, le=1_000_000_000, description="计价 tokens 单位"
    )
    cost_input_per_unit: float | None = Field(
        default=None, ge=0, description="默认每计价单位输入 tokens 成本"
    )
    cost_output_per_unit: float | None = Field(
        default=None, ge=0, description="默认每计价单位输出 tokens 成本"
    )
    cost_tiers: list[LLMCostTier] | None = Field(
        default=None, description="按上下文长度匹配的阶梯价格"
    )
    embedding_api_style: str | None = Field(
        default=None, max_length=50, description="embedding 调用协议风格"
    )
    embedding_dimensions: int | None = Field(
        default=None, ge=1, le=100_000, description="embedding 向量维度"
    )
    embedding_batch_size: int | None = Field(
        default=None, ge=1, le=128, description="embedding 单次请求最大批量"
    )
    embedding_max_input_tokens: int | None = Field(
        default=None, ge=1, le=2_000_000, description="embedding 单条输入最大 token 数"
    )

    @field_validator("model_type")
    @classmethod
    def normalize_model_type(cls, value: str) -> str:
        text = value.strip().lower()
        if text not in LLM_MODEL_TYPES:
            raise ValueError("model_type 仅支持 chat、embedding、rerank")
        return text

    @field_validator("embedding_api_style")
    @classmethod
    def normalize_embedding_api_style(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip().lower()
        if not text:
            return None
        if text not in EMBEDDING_API_STYLES:
            raise ValueError("embedding_api_style 当前仅支持 openai_compatible")
        return text

    @field_validator("cost_currency", "cost_display_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        text = value.strip().upper()
        return text or "CNY"

    @field_validator("cost_tiers")
    @classmethod
    def sort_cost_tiers(
        cls, value: list[LLMCostTier] | None
    ) -> list[LLMCostTier] | None:
        if value is None:
            return None
        return sorted(value, key=lambda item: item.up_to_context_tokens)


class LLMModelCreate(LLMModelBase):
    pass


class LLMModelUpdate(BaseModel):
    model_type: str | None = Field(
        default=None, description="模型用途类型，可选 chat、embedding、rerank"
    )
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
    cost_currency: str | None = Field(default=None, max_length=12)
    cost_display_currency: str | None = Field(default=None, max_length=12)
    cost_exchange_rate: float | None = Field(default=None, gt=0)
    cost_pricing_unit: int | None = Field(default=None, ge=1, le=1_000_000_000)
    cost_input_per_unit: float | None = Field(default=None, ge=0)
    cost_output_per_unit: float | None = Field(default=None, ge=0)
    cost_tiers: list[LLMCostTier] | None = None
    embedding_api_style: str | None = Field(default=None, max_length=50)
    embedding_dimensions: int | None = Field(default=None, ge=1, le=100_000)
    embedding_batch_size: int | None = Field(default=None, ge=1, le=128)
    embedding_max_input_tokens: int | None = Field(default=None, ge=1, le=2_000_000)

    @field_validator("model_type")
    @classmethod
    def normalize_optional_model_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip().lower()
        if text not in LLM_MODEL_TYPES:
            raise ValueError("model_type 仅支持 chat、embedding、rerank")
        return text

    @field_validator("embedding_api_style")
    @classmethod
    def normalize_optional_embedding_api_style(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip().lower()
        if not text:
            return None
        if text not in EMBEDDING_API_STYLES:
            raise ValueError("embedding_api_style 当前仅支持 openai_compatible")
        return text

    @field_validator("cost_currency", "cost_display_currency")
    @classmethod
    def normalize_optional_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper() or None

    @field_validator("cost_tiers")
    @classmethod
    def sort_optional_cost_tiers(
        cls, value: list[LLMCostTier] | None
    ) -> list[LLMCostTier] | None:
        if value is None:
            return None
        return sorted(value, key=lambda item: item.up_to_context_tokens)


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
    input_cost: float | None = None
    output_cost: float | None = None
    total_cost: float | None = None
    cost_currency: str | None = None
    cost_pricing_snapshot: dict[str, Any] | None = None
    prompt_id: int | None
    prompt_version_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
