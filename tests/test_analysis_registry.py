from __future__ import annotations

import pandas as pd
import pytest

from app.schemas.analysis_module import (
    AnalysisContext,
    AnalysisModuleDefinition,
    AnalysisParameterSpec,
    AnalysisParameterType,
    AnalysisResult,
    ModuleExecutionRequest,
)
from app.services.analysis_registry import (
    AnalysisExecutionService,
    AnalysisModuleRegistry,
    AnalysisRegistryError,
    ParameterValidationError,
    RequirementValidationError,
    UnknownModuleError,
    get_analysis_execution_service,
    get_analysis_registry,
)


def _definition() -> AnalysisModuleDefinition:
    return AnalysisModuleDefinition(
        module_id="demo_module",
        name="演示模块",
        parameters=[
            AnalysisParameterSpec(
                key="threshold",
                label="阈值",
                type=AnalysisParameterType.NUMBER,
            ),
            AnalysisParameterSpec(
                key="mode",
                label="模式",
                type=AnalysisParameterType.SELECT,
                default="fast",
                options=["fast", "accurate"],
            ),
            AnalysisParameterSpec(
                key="pattern",
                label="模式匹配",
                type=AnalysisParameterType.REGEX,
                required=False,
            ),
            AnalysisParameterSpec(
                key="title",
                label="标题",
                type=AnalysisParameterType.TEXT,
                default="默认标题",
            ),
        ],
        required_columns=["latency_ms"],
    )


def _handler(
    data_frame: pd.DataFrame,
    params: dict,
    context: AnalysisContext,
) -> AnalysisResult:
    return AnalysisResult(
        data_frame=data_frame.assign(
            threshold=params["threshold"],
            task_id=context.task_id,
        ),
        insights=[f"mode={params['mode']}"],
    )


def test_registry_register_list_get_replace_and_unregister():
    registry = AnalysisModuleRegistry()
    definition = _definition()

    registry.register(definition, _handler)

    assert registry.get("demo_module").definition is definition
    assert registry.list_definitions() == [definition]
    with pytest.raises(AnalysisRegistryError, match="已注册"):
        registry.register(definition, _handler)

    replacement = definition.model_copy(update={"name": "替换模块"})
    registry.replace(replacement, _handler)
    assert registry.get("demo_module").definition.name == "替换模块"

    registry.unregister("demo_module")
    assert registry.list_definitions() == []
    with pytest.raises(UnknownModuleError, match="未注册"):
        registry.get("demo_module")


def test_validate_parameters_coerces_defaults_and_keeps_unknown_values():
    registry = AnalysisModuleRegistry()

    params = registry.validate_parameters(
        _definition(),
        {
            "threshold": "2.5",
            "pattern": "^ok",
            "extra_flag": True,
        },
    )

    assert params == {
        "threshold": 2.5,
        "mode": "fast",
        "pattern": "^ok",
        "title": "默认标题",
        "extra_flag": True,
    }


@pytest.mark.parametrize(
    ("raw_params", "message"),
    [
        ({}, "threshold 为必填项"),
        ({"threshold": " "}, "threshold 需要数字类型"),
        ({"threshold": "abc"}, "threshold 需要数字类型"),
        ({"threshold": 1, "pattern": 123}, "pattern 需要提供正则表达式字符串"),
        ({"threshold": 1, "mode": "slow"}, "mode 的值必须在"),
        ({"threshold": 1, "title": 123}, "title 需要字符串类型"),
    ],
)
def test_validate_parameters_reports_invalid_values(raw_params, message):
    registry = AnalysisModuleRegistry()

    with pytest.raises(ParameterValidationError, match=message):
        registry.validate_parameters(_definition(), raw_params)


def test_ensure_requirements_reports_missing_columns():
    registry = AnalysisModuleRegistry()

    with pytest.raises(RequirementValidationError, match="latency_ms"):
        registry.ensure_requirements(_definition(), pd.DataFrame({"tokens": [10]}))

    registry.ensure_requirements(
        _definition().model_copy(update={"required_columns": []}),
        pd.DataFrame(),
    )


def test_execution_service_executes_now_and_schedule():
    registry = AnalysisModuleRegistry()
    registry.register(_definition(), _handler)
    service = AnalysisExecutionService(registry, max_workers=1)
    request = ModuleExecutionRequest(
        module_id="demo_module",
        task_id="task-1",
        parameters={"threshold": 3},
    )
    context = AnalysisContext(task_id="task-1")
    data_frame = pd.DataFrame({"latency_ms": [100]})

    try:
        immediate = service.execute_now(data_frame, context, request)
        scheduled = service.schedule(lambda: data_frame, context, request).result(
            timeout=1
        )
    finally:
        service.shutdown()

    assert immediate.insights == ["mode=fast"]
    assert immediate.data_frame.iloc[0]["threshold"] == 3
    assert immediate.data_frame.iloc[0]["task_id"] == "task-1"
    assert scheduled.data_frame.equals(immediate.data_frame)


def test_global_registry_and_execution_service_are_singletons():
    assert get_analysis_registry() is get_analysis_registry()
    assert get_analysis_execution_service() is get_analysis_execution_service()
