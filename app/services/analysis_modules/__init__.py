from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.analysis_modules.performance_summary import (
    register_latency_and_tokens_module,
)

if TYPE_CHECKING:  # pragma: no cover - 类型提示辅助
    from app.services.analysis_registry import AnalysisModuleRegistry


def register_builtin_modules(registry: "AnalysisModuleRegistry") -> None:
    """注册平台内置的分析模块。"""

    register_latency_and_tokens_module(registry)


__all__ = ["register_builtin_modules"]
