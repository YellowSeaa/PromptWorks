# 测试分析模块化方案设计说明

## 1. 背景与目标
- 目标：为测试任务提供可扩展的分析报告模块，支持平台维护者和用户自行扩展分析能力。
- 场景：测试结果默认不分析，用户在任务完成后或任务创建阶段主动选择需要运行的分析模块。
- 期望：形成统一的“分析插件协议”，保证模块之间可插拔、可复用并便于前后端协同。

## 2. 模块能力定位
- 模块输入：平台导出的测试结果数据（CSV 数据源转换后的 `pandas.DataFrame`）+ 用户自定义参数。
- 模块输出：
  - 分析结果 `DataFrame`，用于前端渲染表格与后续图表绘制。
  - 列元信息列表，用于描述每一列的含义、展示形式及是否支持图表。
  - 可选：额外洞察（文字总结）、指标统计、LLM 调用记录等。
- 模块表现：前端以卡片形式展示模块名称、描述、表格以及根据元信息自动生成的预设图表。

## 3. 架构方案比选与结论
| 方案 | 优点 | 风险 | 结论 |
| --- | --- | --- | --- |
| Python Entry Points / 插件包 | 隔离清晰，适合第三方扩展 | 依赖管理复杂、初期成本高 | 当前阶段暂不采用 |
| 仓库内置模块 + 注册中心 | 实现简单，平台可控 | 用户扩展需写代码进入仓库 | 作为平台内置模块基础形态 |
| 前端上传 `.py` + 扩展协议 | 自由度高，可快速添加模块 | 依赖、加载、热更新需额外设计 | 结合标准库白名单策略落地 MVP |

## 4. 依赖策略
- 初期采用“标准库 + 平台预装白名单”模式，限制插件仅使用 `pandas`、`numpy` 等预装依赖，无需额外安装第三方库。
- 上传模块需包含 `module.yaml`（或 JSON）声明元数据：模块名、描述、入口函数、参数需求、依赖策略等。
- 为未来扩展预留方案：
  - 独立虚拟环境池（按需安装依赖）。
  - 插件自带依赖压缩包，通过调整 `sys.path` 挂载。

## 5. 模块协议设想
```python
class AnalysisColumnMeta(BaseModel):
    name: str                  # 列名
    label: str                 # 中文描述
    description: str | None    # 额外说明
    visualizable: list[str]    # 支持的图表类型（如 ["bar", "line"]）
    extra: dict | None         # 其他展示配置

class ParameterSpec(BaseModel):
    key: str
    label: str
    type: Literal["text", "number", "select", "regex"]
    required: bool
    default: Any | None
    options: list[Any] | None
    help_text: str | None

class AnalysisContext:
    llm: LLMClient             # 平台注入，用于访问 LLM 服务
    task_id: str
    logger: Logger | None

def run(data: pd.DataFrame, params: dict[str, Any], context: AnalysisContext) -> AnalysisResult:
    ...
```

- `AnalysisResult` 结构：
  - `data_frame`: `pd.DataFrame`
  - `columns_meta`: `list[AnalysisColumnMeta]`
  - `insights`: `list[str] | None`
  - `llm_usage`: `dict | None`
  - `protocol_version`: `str`
- 模块需声明依赖字段（例如 `requires_columns: ["prompt", "response", "status"]`），平台在执行前做校验并给出友好提示。
- 参数配置由 `ParameterSpec` 描述，前端可根据类型动态渲染表单并提供校验。

## 6. LLM 调用能力
- 通过 `AnalysisContext.llm` 提供统一封装的 LLM 调用接口，例如 `invoke(prompt, model="gpt-4", temperature=0.2)`。
- 平台负责鉴权、限流、超时重试与调用日志；模块只需按接口调用。
- 结果中允许返回 `llm_usage`（token 消耗、响应时间）用于前端展示与费用追踪。

## 7. 前后端协作流程
1. **模块管理**
   - 前端上传模块文件（`.py` 或 `.zip`）+ `module.yaml`。
   - 后端验证文件结构、接口签名、依赖策略，注册到 `ModuleRegistry`，并记录版本号。
2. **分析配置**
   - 任务创建页：多选框选择需要的模块。
   - 任务详情页：提供“开启分析”按钮，可追加或变更选中模块。
   - 参数输入：前端根据 `ParameterSpec` 生成表单，提交时序列化为 JSON。
3. **执行与展示**
   - 后端按模块执行（建议异步队列），读取测试结果 DataFrame。
   - 返回 `AnalysisResult` 序列化后的 JSON，前端卡片展示表格和图表。
   - 执行日志与错误信息持久化，便于用户回查。

## 8. 风险与防护
- **性能**：大数据量分析可能耗时，需支持异步任务与结果缓存。
- **稳定性**：模块更新需处理热加载；可通过版本目录 + 重启加载或子进程执行。
- **数据质量**：CSV 字段变更时提前校验，给出缺字段提示。
- **LLM 成本**：平台侧限制每次执行的 LLM 调用次数/预算，记录调用明细。

## 9. 当前进度与计划
- 已完成：
  - 分析协议与上下文模型定义。
  - 注册表/执行服务骨架与耗时 Tokens 内置模块。
  - 测试任务数据加载与 REST API (`/api/v1/analysis`) 对接。
- 待推进：
  1. 扩充更多内置模块与 LLM 驱动分析示例。
  2. 设计前端分析卡片与图表渲染交互。
  3. 引入执行队列、缓存与监控，完善运行稳定性。
  4. 支持用户上传模块与依赖管理策略。

## 10. 内置模块现状
- `latency_tokens_summary`：统计耗时与 tokens 分布，输出平均/P95/最大最小耗时、总 tokens、平均 tokens、吞吐量等指标，为性能与成本评估提供基础数据。

---

文档版本：2025-11-06
