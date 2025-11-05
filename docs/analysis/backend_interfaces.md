# 分析模块后端接口与数据模型说明

## 1. 概述
- 目标：定义分析模块的运行时上下文与返回结果结构，并提供模块注册、参数校验、执行调度的统一骨架。
- 适用范围：后端开发者在实现新的分析模块、扩展执行能力时需要遵循的接口协议。

## 2. Pydantic 数据模型

### 2.1 参数类型与声明
- `AnalysisParameterType`：参数类型枚举，当前支持 `text`、`number`、`select`、`regex`。
- `AnalysisParameterSpec` 字段：
  - `key`：参数键名，模块实现使用。
  - `label`：中文展示名称。
  - `type`：参数类型，驱动前端生成对应控件。
  - `required`：是否必填。
  - `default`：默认值。
  - `options`：可选值列表（适用于 `select`）。
  - `help_text`：辅助说明。
  - `regex_pattern`：当类型为 `regex` 时的预置表达式，便于给出模板。

### 2.2 列元信息
- `AnalysisColumnMeta`：描述分析结果 `DataFrame` 中每列的展示需求。
  - `name`：与数据列一致的字段名。
  - `label`：中文名称。
  - `description`：补充说明。
  - `visualizable`：可绘制的图表类型，如 `["bar", "line"]`。
  - `extra`：前端渲染的附加配置。

### 2.3 运行上下文
- `AnalysisContext` 字段：
  - `task_id`：当前测试任务 ID。
  - `user_id`：发起分析的用户 ID（可空）。
  - `llm_client`：平台注入的 LLM 客户端实例，类型不固定，允许为空。
  - `metadata`：任务相关的补充信息字典。
  - `logger`：可选日志记录器。
- 模型允许任意类型字段（`arbitrary_types_allowed=True`），以便注入真实 LLM 客户端对象。

### 2.4 分析结果
- `AnalysisResult` 字段：
  - `data_frame`：分析输出的 `pd.DataFrame`。
  - `columns_meta`：列元信息，用于驱动前端渲染。
  - `insights`：文字洞察列表。
  - `llm_usage`：LLM 资源消耗统计。
  - `protocol_version`：协议版本，默认 `v1`。
  - `extra`：扩展字段，用于模块自定义。

### 2.5 模块定义与执行请求
- `AnalysisModuleDefinition`：注册模块时提交的元数据，包含 `module_id`、`name`、`description`、`parameters`、`required_columns`、`tags`、`protocol_version`、`allow_llm`。
- `ModuleExecutionRequest`：用户发起执行时的请求载体，包含 `module_id`、`task_id`、`parameters`。
- `AnalysisResultPayload`：API 层返回给前端的结构化结果，字段包括 `module_id`、`data`（列表化的数据记录）、`columns_meta`、`insights`、`llm_usage`、`protocol_version` 与 `extra`。

## 3. 注册与执行骨架

### 3.1 `AnalysisModuleRegistry`
- 职责：
  1. 管理模块注册、更新和删除。
  2. 持有 `module_id → RegisteredAnalysisModule` 的映射。
  3. 校验参数、检查依赖字段。
- 关键方法：
  - `register(definition, handler)`：注册新模块，防止重复。
  - `replace(definition, handler)`：更新模块定义或实现。
  - `unregister(module_id)`：移除模块。
  - `validate_parameters(definition, raw_params)`：根据参数声明执行校验与类型转换。
  - `ensure_requirements(definition, data_frame)`：检查数据列是否满足模块要求。
- 异常：
  - `AnalysisRegistryError`：基础异常。
  - `UnknownModuleError`：模块未注册。
  - `ParameterValidationError`：参数校验失败。
  - `RequirementValidationError`：缺少必要字段。

### 3.2 参数校验策略
- 数字参数支持字符串→浮点数自动转换。
- `select` 类型在声明了 `options` 时严格校验取值范围。
- `regex` 类型要求字符串输入。
- 允许附加参数透传，便于协议向前兼容。

### 3.3 `AnalysisExecutionService`
- 作用：封装执行逻辑与线程池调度。
- 关键方法：
  - `execute_now(data_frame, context, execution_request)`：同步执行模块。
  - `schedule(data_loader, context, execution_request)`：通过 `ThreadPoolExecutor` 异步执行，`data_loader` 用于延迟加载数据。
  - `shutdown(wait=True)`：释放线程池资源。
- 调度流程：
  1. 根据 `module_id` 获取已注册模块。
  2. 参数校验 + 字段校验。
  3. 调用模块处理函数 `handler(data_frame, params, context)`。
  4. 返回 `AnalysisResult`。
- 目前已内置 `latency_tokens_summary` 模块，提供耗时与 tokens 汇总分析，可作为实现自定义模块的参考。

### 3.4 `analysis_runner`
- 职责：负责解析任务 ID、加载测试结果 `DataFrame`、构造 `AnalysisContext` 并调用执行服务。
- 核心方法：
  - `execute_module_for_test_run(db, request, user_id=None)`：面向测试任务的统一入口，返回 `AnalysisResult`。
  - `serialize_analysis_result(module_id, result)`：将内部结果转换为 `AnalysisResultPayload`，处理空值与类型。
- 错误类型：
  - `AnalysisTaskNotFoundError`：指定任务不存在。
  - `AnalysisDataLoadError`：任务 ID 无效或结果数据缺失。

## 4. FastAPI 接口
- `GET /api/v1/analysis/modules`：列出 `AnalysisModuleDefinition` 列表，供前端渲染模块目录。
- `POST /api/v1/analysis/modules/execute`：接收 `ModuleExecutionRequest`，返回 `AnalysisResultPayload`；统一处理参数错误、字段缺失、任务不存在等异常并转换为 HTTP 状态码。

## 5. 后续工作指引
1. 扩展更多内置模块（例如成功率、响应分类等），丰富模块目录。
2. 将 LLM 客户端注入 `AnalysisContext`，并提供调用限额与日志记录。
3. 引入任务级缓存/异步调度，优化大型数据集的分析性能。
4. 细化用户文档与示例仓库，指导自定义模块的编写与调试。

文档版本：2025-11-06
