from __future__ import annotations

from enum import Enum
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class AnalysisParameterType(str, Enum):
    """分析模块参数类型。"""

    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    REGEX = "regex"


class AnalysisParameterSpec(BaseModel):
    """用于描述分析模块需要的用户输入参数。"""

    __test__ = False

    key: str = Field(..., description="参数键名，应与模块实现所需的参数一致。")
    label: str = Field(..., description="展示给用户的中文名称。")
    type: AnalysisParameterType = Field(
        default=AnalysisParameterType.TEXT, description="参数类型，用于生成前端表单。"
    )
    required: bool = Field(default=True, description="是否必填。")
    default: Any | None = Field(
        default=None, description="默认值，前端在初始化表单时使用。"
    )
    options: list[Any] | None = Field(
        default=None,
        description="当类型为 select 时的可选项，或给出示例值列表。",
    )
    help_text: str | None = Field(default=None, description="用户提示信息。")
    regex_pattern: str | None = Field(
        default=None, description="当类型为 regex 时可选的预置正则表达式。"
    )


class AnalysisColumnMeta(BaseModel):
    """分析结果中单列的展示元数据。"""

    __test__ = False

    name: str = Field(..., description="列名，需要与结果 DataFrame 中的列一致。")
    label: str = Field(..., description="列的中文描述，前端用于展示。")
    description: str | None = Field(default=None, description="列的额外说明信息。")
    visualizable: list[str] = Field(
        default_factory=list, description="可用于绘制的图表类型列表，例如 ['bar']。"
    )
    extra: dict[str, Any] | None = Field(
        default=None, description="前端渲染时需要的附加配置。"
    )


class AnalysisContext(BaseModel):
    """运行分析模块时的上下文信息。"""

    __test__ = False

    task_id: str = Field(..., description="当前分析对应的测试任务 ID。")
    user_id: int | None = Field(default=None, description="发起分析的用户 ID。")
    llm_client: Any | None = Field(
        default=None,
        description="平台注入的 LLM 客户端实例，遵循统一接口。",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="与任务相关的补充信息。"
    )
    logger: Any | None = Field(
        default=None, description="可选的日志记录器，用于模块内记录调试信息。"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AnalysisResult(BaseModel):
    """分析模块的执行结果。"""

    __test__ = False

    data_frame: pd.DataFrame = Field(..., description="分析结果数据表。")
    columns_meta: list[AnalysisColumnMeta] = Field(
        default_factory=list, description="列的展示配置列表。"
    )
    insights: list[str] = Field(
        default_factory=list, description="可选的结论或洞察摘要。"
    )
    llm_usage: dict[str, Any] | None = Field(
        default=None, description="LLM 调用的资源消耗信息。"
    )
    protocol_version: str = Field(
        default="v1", description="分析协议版本，用于向前兼容。"
    )
    extra: dict[str, Any] | None = Field(
        default=None, description="附加的模块自定义字段。"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AnalysisModuleDefinition(BaseModel):
    """用于注册分析模块的基础信息。"""

    __test__ = False

    module_id: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$", description="模块唯一 ID。")
    name: str = Field(..., description="模块名称。")
    description: str | None = Field(default=None, description="模块说明。")
    parameters: list[AnalysisParameterSpec] = Field(
        default_factory=list, description="模块需要的参数列表。"
    )
    required_columns: list[str] = Field(
        default_factory=list, description="执行模块必须存在的 CSV 字段。"
    )
    tags: list[str] = Field(
        default_factory=list, description="用于前端筛选或分类的标签。"
    )
    protocol_version: str = Field(
        default="v1", description="模块支持的协议版本，默认 v1。"
    )
    allow_llm: bool = Field(default=False, description="模块是否计划调用平台 LLM。")


class ModuleExecutionRequest(BaseModel):
    """执行分析模块时提交的请求。"""

    __test__ = False

    module_id: str = Field(..., description="目标模块 ID。")
    task_id: str = Field(..., description="关联的测试任务 ID。")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="用户填写的参数内容。"
    )

