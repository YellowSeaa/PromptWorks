from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.types import JSONBCompat
from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover - 类型检查辅助
    from app.models.llm_provider import LLMProvider


class LLMUsageLog(Base):
    """记录每次 LLM 调用的用量与上下文，供后续统计分析。"""

    __tablename__ = "llm_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("llm_providers.id", ondelete="SET NULL"), nullable=True
    )
    model_id: Mapped[int | None] = mapped_column(
        ForeignKey("llm_models.id", ondelete="SET NULL"), nullable=True
    )
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="quick_test"
    )
    prompt_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True
    )
    prompt_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompts_versions.id", ondelete="SET NULL"), nullable=True
    )
    messages: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONBCompat, nullable=True
    )
    parameters: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat, nullable=True
    )
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_currency: Mapped[str | None] = mapped_column(String(12), nullable=True)
    cost_pricing_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    provider: Mapped["LLMProvider"] = relationship(
        "LLMProvider", back_populates="usage_logs", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return (
            "LLMUsageLog(id={id}, provider_id={provider_id}, model={model}, tokens={tokens})"
        ).format(
            id=self.id,
            provider_id=self.provider_id,
            model=self.model_name,
            tokens=self.total_tokens,
        )


__all__ = ["LLMUsageLog"]
