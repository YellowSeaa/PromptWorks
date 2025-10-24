## 1. 背景与目标

- **统一性**：为不同测试类型（对话、问答、结构化生成、工具调用等）提供一致的结果分析协议，避免任务专属逻辑写死在分析层。
- **可追溯**：输入侧完整保留测试任务的原始输出、上下文与基准答案，输出侧提供明确的维度评分、聚合结果与证据引用。
- **可扩展**：为后续的可插拔维度分析、稳健聚合策略、可视化展示等模块提供稳定的数据基础。

## 2. 核心概念统一

- **任务（TestTask）**：一次测试执行的抽象，可能包含多个 Prompt 版本、模型、数据集组合。
- **用例（TestCase）**：单个上下文实例，可对应若干轮回测（Round）。
- **回合（RoundRun）**：对同一用例和 Prompt 的一次实际请求返回，包含原始响应、解析结果和资源消耗。
- **基准（Baseline）**：与用例绑定的参考答案或评估脚本，可来源于人工标注或黄金模型。
- **维度（Dimension）**：某种评价视角，如准确性、一致性、毒性、稳定性等。
- **证据（Evidence）**：支撑维度打分的原始片段，便于前端展示和人工稽核。

## 3. 输入数据契约

### 3.1 顶层结构 `AnalysisInput`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task` | `TestTaskMeta` | 任务级元信息，包含业务标签、环境、触发方式等 |
| `cases` | `list[TestCaseBundle]` | 用例集合，含用例描述、回合记录与基准 |
| `dimensions` | `list[DimensionConfig]` | 计划评估的维度及其权重、参数 |
| `extras` | `dict[str, Any]` | 任务自定义扩展信息，保留原始结构 |

### 3.2 任务元信息 `TestTaskMeta`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | `str` | 任务唯一标识，可采用 `test_run_id` 等 |
| `title` | `str` | 任务名称，便于展示 |
| `prompt_version` | `str` | Prompt 版本或实验分支标识 |
| `model` | `str` | 执行模型（含供应商标识） |
| `triggered_by` | `str` | 发起方式，如 `manual`、`ci`、`schedule` |
| `env` | `dict[str, str]` | 环境信息，例如地区、部署集群 |
| `created_at` | `datetime` | 任务创建时间 |

### 3.3 用例捆绑 `TestCaseBundle`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `case_id` | `str` | 用例唯一标识 |
| `context` | `dict[str, Any]` | 用例上下文变量（用户信息、输入等） |
| `rounds` | `list[RoundRun]` | 针对该用例的所有模型响应 |
| `baselines` | `list[BaselineSpec]` | 关联的基准答案、脚本或评估说明 |
| `tags` | `list[str]` | 可选标签，例如行业、意图、风险等级 |

### 3.4 回合记录 `RoundRun`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `round_id` | `str` | 回合标识（如 `"{case_id}-{run_index}"`） |
| `run_index` | `int` | 序号，从 1 开始 |
| `raw_output` | `str` | 模型原始输出 |
| `parsed_output` | `dict[str, Any]` \| `None` | 判定后的结构化结果 |
| `input_tokens` | `int` \| `None` | 输入 Token 数 |
| `output_tokens` | `int` \| `None` | 输出 Token 数 |
| `latency_ms` | `int` \| `None` | 响应时延 |
| `metadata` | `dict[str, Any]` | 附加信息，如请求参数、错误码 |
| `executed_at` | `datetime` | 实际请求完成时间 |

### 3.5 基准描述 `BaselineSpec`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `baseline_id` | `str` | 基准标识 |
| `type` | `Literal["golden_answer", "rules", "script", "manual_note"]` | 基准类型 |
| `payload` | `dict[str, Any]` | 基准内容（如参考答案、规则表达式、脚本路径） |
| `owner` | `str` | 维护者或来源 |
| `confidence` | `float` \| `None` | 基准置信水平（0-1），可用于聚合时加权 |

### 3.6 维度配置 `DimensionConfig`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `dimension_id` | `str` | 维度唯一标识 |
| `name` | `str` | 中文名称 |
| `weight` | `float` | 默认权重，0-1 |
| `target` | `dict[str, Any]` | 维度目标或期望值（如阈值、上限） |
| `parameters` | `dict[str, Any]` | 插件所需额外参数（如关键字列表、正则等） |
| `scoring_mode` | `Literal["higher_better", "lower_better", "range"]` | 指定评分方向 |

## 4. 输出数据契约

### 4.1 顶层结构 `AnalysisResult`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task` | `TestTaskMeta` | 原样回传任务信息 |
| `summary` | `ResultSummary` | 总体评分、结论、告警 |
| `dimensions` | `list[DimensionResult]` | 各维度明细 |
| `case_results` | `list[CaseResult]` | 用例级细粒度结果（可选按需裁剪） |
| `generated_at` | `datetime` | 分析生成时间 |
| `version` | `str` | 分析内核版本号 |
| `extras` | `dict[str, Any]` | 补充说明、调试信息 |

### 4.2 总结对象 `ResultSummary`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `overall_score` | `float` | 聚合得分，统一归一化到 0-1 或百分制 |
| `grade` | `str` | 等级标签，如 `A/B/C` 或 `pass/fail` |
| `alerts` | `list[AlertItem]` | 告警列表，包含严重度、触发维度、描述 |
| `coverage` | `float` \| `None` | 实际参与分析的回合占比 |

### 4.3 维度结果 `DimensionResult`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `dimension_id` | `str` | 与配置对应 |
| `name` | `str` | 中文名称 |
| `score` | `float` | 归一化得分 |
| `raw_metrics` | `dict[str, Any]` | 原始指标，如 `correct_ratio`、`toxicity_rate` |
| `weight` | `float` | 实际使用的权重 |
| `contributions` | `list[EvidenceLink]` | 关键证据列表，引用用例与回合 |
| `diagnosis` | `str` | 维度结论文字，便于展示 |

### 4.4 用例结果 `CaseResult`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `case_id` | `str` | 用例标识 |
| `dimension_scores` | `dict[str, float]` | 各维度得分，键为 `dimension_id` |
| `aggregated_score` | `float` | 用例级聚合得分 |
| `evidences` | `list[EvidenceLink]` | 具体证据引用 |
| `notes` | `dict[str, Any]` | 额外说明，如失败原因、错误分类 |

### 4.5 证据与告警

- `EvidenceLink`：`{"dimension_id": str, "case_id": str, "round_id": str, "summary": str, "payload": dict[str, Any]}`  
  用于前端定位数据，`payload` 可包含片段、高亮位置、参考答案对比等。
- `AlertItem`：`{"severity": Literal["critical","major","minor","info"], "message": str, "dimension_ids": list[str], "case_ids": list[str]}`。

## 5. 设计约束与扩展点

1. **任务无关性**：所有字段不假设具体 Prompt 类型，复杂任务可通过 `extras` 扩展；运行时策略（如批量/流式）通过 `task.env` 描述。
2. **回放能力**：输入中保留 `raw_output`、`parsed_output`、请求元数据，使维度插件能够重复分析；必要时允许附加原始请求体。
3. **插件对齐**：维度插件以 `DimensionConfig` 和 `TestCaseBundle` 为输入，输出 `DimensionResult`，避免跨插件共享隐式状态。
4. **稳健聚合前置**：在 `DimensionResult.raw_metrics` 中提供与稳健聚合相关的统计量（均值、分位数、样本数）以便后续策略使用。
5. **版本治理**：`AnalysisResult.version` 需随协议调整递增，同时在 `extras` 内记录插件版本与执行参数，便于回滚。

## 6. 示例片段

```json
{
  "task": {
    "task_id": "run-20241024-001",
    "title": "客服问答回归测试",
    "prompt_version": "v3.2",
    "model": "openai/gpt-4o-mini",
    "triggered_by": "ci",
    "env": {"region": "cn-beijing", "dataset": "qa_suite_v2"},
    "created_at": "2024-10-24T12:30:00Z"
  },
  "cases": [
    {
      "case_id": "case-001",
      "context": {"question": "如何重置密码？", "channel": "web"},
      "rounds": [
        {
          "round_id": "case-001-1",
          "run_index": 1,
          "raw_output": "您可以点击账户设置...",
          "parsed_output": {"action": "reset_password", "steps": 3},
          "input_tokens": 320,
          "output_tokens": 180,
          "latency_ms": 842,
          "metadata": {"temperature": 0.2},
          "executed_at": "2024-10-24T12:31:05Z"
        }
      ],
      "baselines": [
        {
          "baseline_id": "golden-001",
          "type": "golden_answer",
          "payload": {"text": "前往设置-安全-重置密码，..."},
          "owner": "ops-team",
          "confidence": 0.9
        }
      ],
      "tags": ["faq", "high_priority"]
    }
  ],
  "dimensions": [
    {
      "dimension_id": "accuracy",
      "name": "准确性",
      "weight": 0.5,
      "target": {"min_score": 0.85},
      "parameters": {"match_rule": "semantic"},
      "scoring_mode": "higher_better"
    },
    {
      "dimension_id": "consistency",
      "name": "一致性",
      "weight": 0.3,
      "target": {"max_variance": 0.1},
      "parameters": {},
      "scoring_mode": "higher_better"
    }
  ],
  "extras": {"notes": "本次回归覆盖高风险 FAQ"}
}
```

上述输入通过分析内核后，会生成包含 `ResultSummary` 和逐维度 `DimensionResult` 的统一输出，为后续的可插拔维度分析与稳健聚合奠定基础。
