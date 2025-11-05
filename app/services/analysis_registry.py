from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.schemas.analysis_module import (
    AnalysisContext,
    AnalysisModuleDefinition,
    AnalysisParameterSpec,
    AnalysisParameterType,
    AnalysisResult,
    ModuleExecutionRequest,
)

AnalysisCallable = Callable[[pd.DataFrame, dict[str, Any], AnalysisContext], AnalysisResult]
DataFrameLoader = Callable[[], pd.DataFrame]


class AnalysisRegistryError(Exception):
    """分析模块注册或执行的基础异常。"""

    __test__ = False


class UnknownModuleError(AnalysisRegistryError):
    """尝试访问尚未注册的分析模块。"""

    __test__ = False


class ParameterValidationError(AnalysisRegistryError):
    """分析模块参数校验失败。"""

    __test__ = False


class RequirementValidationError(AnalysisRegistryError):
    """分析模块执行前置条件校验失败。"""

    __test__ = False


@dataclass(slots=True)
class RegisteredAnalysisModule:
    """用于保存已注册模块的定义与实现。"""

    definition: AnalysisModuleDefinition
    handler: AnalysisCallable


class AnalysisModuleRegistry:
    """管理分析模块的注册、参数校验与查找。"""

    def __init__(self) -> None:
        self._modules: dict[str, RegisteredAnalysisModule] = {}
        self._lock = threading.RLock()

    def register(
        self, definition: AnalysisModuleDefinition, handler: AnalysisCallable
    ) -> None:
        with self._lock:
            if definition.module_id in self._modules:
                raise AnalysisRegistryError(f"模块 {definition.module_id} 已注册。")
            self._modules[definition.module_id] = RegisteredAnalysisModule(
                definition=definition, handler=handler
            )

    def replace(
        self, definition: AnalysisModuleDefinition, handler: AnalysisCallable
    ) -> None:
        with self._lock:
            self._modules[definition.module_id] = RegisteredAnalysisModule(
                definition=definition, handler=handler
            )

    def unregister(self, module_id: str) -> None:
        with self._lock:
            self._modules.pop(module_id, None)

    def get(self, module_id: str) -> RegisteredAnalysisModule:
        try:
            return self._modules[module_id]
        except KeyError as exc:  # pragma: no cover - 防御性
            raise UnknownModuleError(f"模块 {module_id} 未注册。") from exc

    def list_definitions(self) -> list[AnalysisModuleDefinition]:
        return [item.definition for item in self._modules.values()]

    def validate_parameters(
        self,
        definition: AnalysisModuleDefinition,
        raw_params: dict[str, Any],
    ) -> dict[str, Any]:
        validated: dict[str, Any] = {}
        param_map = raw_params or {}

        spec_by_key = {item.key: item for item in definition.parameters}
        for key, spec in spec_by_key.items():
            value = param_map.get(key, None)
            if value is None:
                if spec.required and spec.default is None:
                    raise ParameterValidationError(f"参数 {key} 为必填项。")
                if spec.default is not None:
                    validated[key] = spec.default
                continue
            validated[key] = self._coerce_parameter(spec, value)

        # 余留的参数可直接透传，便于向前兼容。
        for key, value in param_map.items():
            if key not in validated:
                validated[key] = value

        return validated

    def ensure_requirements(
        self, definition: AnalysisModuleDefinition, data_frame: pd.DataFrame
    ) -> None:
        if not definition.required_columns:
            return
        missing = [
            column for column in definition.required_columns if column not in data_frame.columns
        ]
        if missing:
            formatted = ", ".join(missing)
            raise RequirementValidationError(f"缺少执行模块所需字段：{formatted}")

    @staticmethod
    def _coerce_parameter(spec: AnalysisParameterSpec, value: Any) -> Any:
        if spec.type == AnalysisParameterType.NUMBER:
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str) and value.strip():
                try:
                    return float(value)
                except ValueError as exc:  # pragma: no cover - 防御性
                    raise ParameterValidationError(f"参数 {spec.key} 需要数字类型。") from exc
            raise ParameterValidationError(f"参数 {spec.key} 需要数字类型。")
        if spec.type == AnalysisParameterType.REGEX and not isinstance(value, str):
            raise ParameterValidationError(f"参数 {spec.key} 需要提供正则表达式字符串。")
        if spec.type == AnalysisParameterType.SELECT and spec.options:
            if value not in spec.options:
                raise ParameterValidationError(
                    f"参数 {spec.key} 的值必须在 {spec.options} 中。"
                )
        if spec.type == AnalysisParameterType.TEXT and not isinstance(value, str):
            raise ParameterValidationError(f"参数 {spec.key} 需要字符串类型。")
        return value


class AnalysisExecutionService:
    """提供分析模块的调度执行能力。"""

    def __init__(self, registry: AnalysisModuleRegistry, max_workers: int = 4) -> None:
        self._registry = registry
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def execute_now(
        self,
        data_frame: pd.DataFrame,
        context: AnalysisContext,
        execution_request: ModuleExecutionRequest,
    ) -> AnalysisResult:
        registered = self._registry.get(execution_request.module_id)
        params = self._registry.validate_parameters(
            registered.definition, execution_request.parameters
        )
        self._registry.ensure_requirements(registered.definition, data_frame)
        return registered.handler(data_frame, params, context)

    def schedule(
        self,
        data_loader: DataFrameLoader,
        context: AnalysisContext,
        execution_request: ModuleExecutionRequest,
    ) -> Future[AnalysisResult]:
        def _runner() -> AnalysisResult:
            data_frame = data_loader()
            return self.execute_now(data_frame, context, execution_request)

        return self._executor.submit(_runner)

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


_REGISTRY_SINGLETON = AnalysisModuleRegistry()
_EXECUTION_SERVICE_SINGLETON = AnalysisExecutionService(_REGISTRY_SINGLETON)


def get_analysis_registry() -> AnalysisModuleRegistry:
    """获取全局分析模块注册表实例。"""

    return _REGISTRY_SINGLETON


def get_analysis_execution_service() -> AnalysisExecutionService:
    """获取全局分析执行服务实例。"""

    return _EXECUTION_SERVICE_SINGLETON


def initialize_builtin_modules() -> None:
    """注册平台内置的分析模块。"""

    from app.services.analysis_modules import register_builtin_modules

    register_builtin_modules(_REGISTRY_SINGLETON)


initialize_builtin_modules()
