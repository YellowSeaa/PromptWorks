# Embedding 语义一致性与多样性分析整体方案

日期：2026-06-17  
项目：PromptWorks  
状态：设计方案  
上游报告：`docs/embedding_stability_feasibility_report.md`

## 1. 方案结论

建议将原先“基于 embedding 的输出稳定性评估”升级为“语义一致性与多样性分析”。原因是 embedding 相似度本身只是语义距离信号，不天然等价于好坏。对于确定性任务，输出越一致通常越好；对于创意性任务，输出过于一致反而可能说明 Prompt 生成空间太窄。

因此本功能的核心设计原则是：

1. 只在“可比输出集合”内计算 embedding 指标。
2. 指标解释必须结合任务目标，不默认“相似度越高越好”。
3. 分析报告展示中性指标，AI 优化根据目标方向生成建议。

## 2. 核心概念

### 2.1 可比输出集合

Embedding 指标不能简单按“最小测试单元”汇总，而要继续细分到变量组合。

可比输出集合定义为：

```text
comparable_group = task_id + unit_id + variable_case_hash
```

含义：

- `task_id`：测试任务
- `unit_id`：最小测试单元
- `variable_case_hash`：变量组合稳定哈希

只有属于同一个 `comparable_group` 的输出，才可以直接计算语义一致性、多样性和离群值。

### 2.2 变量处理规则

| 场景 | 是否可直接比较 | 处理方式 |
|---|---:|---|
| 无变量，多轮运行 | 是 | `variable_case_hash = no_variables` |
| 同一变量组合，多轮运行 | 是 | 按该变量组合分组计算 |
| 不同变量组合 | 否 | 分组计算后再汇总，不做两两相似度 |
| 不同 Prompt 版本，同一变量组合 | 是 | 可计算版本间语义保持度 |
| 不同 Prompt 版本，不同变量组合 | 否 | 只做分组级聚合，不做直接比较 |

变量哈希应基于规范化 JSON 生成：

```text
variable_case_hash = sha256(canonical_json(variables))
```

规范化要求：

- key 排序
- 去掉无意义空白
- 保留值类型差异
- 空变量统一为 `{}` 或 `no_variables`

### 2.3 任务语义目标

每个测试单元需要有一个语义目标，用于解释 embedding 指标。

建议枚举：

| 目标 | 说明 | 指标方向 |
|---|---|---|
| `consistency` | 追求语义一致 | 相似度越高越好 |
| `diversity` | 追求语义多样 | 相似度过高是问题 |
| `balanced` | 追求稳定且不过度收敛 | 落在目标区间最好 |

推荐默认值：

```text
semantic_objective = consistency
```

原因是 PromptWorks 当前更偏 Prompt 资产管理、测试与运营后台，大多数测试任务天然偏确定性质量验证。创意任务由用户在测试单元或任务配置里显式切换。

## 3. 指标体系

### 3.1 底层中性指标

底层指标不直接表达好坏，只表达语义关系。

| 指标 | 计算方式 | 含义 |
|---|---|---|
| `mean_pairwise_similarity` | 同组输出两两余弦相似度均值 | 整体语义一致程度 |
| `min_pairwise_similarity` | 同组输出两两余弦相似度最小值 | 最大语义漂移 |
| `centroid_similarity_mean` | 输出向量与中心向量相似度均值 | 围绕中心语义的集中程度 |
| `semantic_dispersion` | `1 - centroid_similarity_mean` | 语义离散度 |
| `outlier_count` | 与中心相似度低于阈值的输出数 | 离群输出数量 |
| `sample_count` | 同组成功输出数 | 指标可信度基础 |

### 3.2 目标解释指标

在展示和 AI 优化中，应把底层指标解释成目标相关结论。

#### consistency

用于分类、抽取、标准回复、合规检查、格式化输出等任务。

判断逻辑：

```text
如果 mean_pairwise_similarity 高，outlier_count 低，则表现好。
如果 mean_pairwise_similarity 低，outlier_count 高，则需要增强约束。
```

建议文案：

```text
该测试单元追求语义一致性。当前多轮输出语义差异偏大，建议收紧任务边界、明确输出字段和判断标准。
```

#### diversity

用于创意文案、标题生成、广告语、头脑风暴、多方案改写等任务。

判断逻辑：

```text
如果 mean_pairwise_similarity 过高，则输出过度收敛。
如果 mean_pairwise_similarity 适中，且离群输出仍围绕主题，则表现好。
如果 mean_pairwise_similarity 过低，则可能偏题。
```

建议文案：

```text
该测试单元追求语义多样性。当前输出过于接近，建议增加角度、风格、受众或候选差异约束。
```

#### balanced

用于既要求主题不偏离，又希望表达有变化的任务。

判断逻辑：

```text
相似度落在目标区间最好，例如 0.75-0.90。
低于下限表示漂移，高于上限表示过度收敛。
```

建议文案：

```text
该测试单元追求一致性与多样性的平衡。当前输出已偏离目标区间，建议调整 Prompt 对变化范围的描述。
```

### 3.3 默认阈值

第一版可以使用保守默认值，并允许后续配置。

| 目标 | 理想区间 | 风险提示 |
|---|---|---|
| `consistency` | `mean_pairwise_similarity >= 0.85` | 低于 0.80 强提示 |
| `diversity` | `0.60 <= mean_pairwise_similarity <= 0.82` | 高于 0.90 过度收敛，低于 0.55 可能偏题 |
| `balanced` | `0.75 <= mean_pairwise_similarity <= 0.90` | 区间外提示 |

阈值必须在报告中标记为“建议阈值”，不能包装成绝对判断。

## 4. 数据流设计

### 4.1 测试执行阶段

测试执行阶段继续按现有逻辑生成输出，不强制同步计算 embedding。

原因：

- 避免拖慢测试任务主流程
- embedding 模型可能单独限流或不可用
- 用户可能只在需要报告或优化时才触发分析

### 4.2 分析阶段

分析模块执行时：

1. 读取 Prompt 测试成功输出
2. 为每条输出生成 `variable_case_hash`
3. 按 `task_id + unit_id + variable_case_hash` 分组
4. 过滤样本数不足的组
5. 批量调用 embedding 模型
6. 计算中性指标
7. 按 `semantic_objective` 生成解释
8. 返回表格、图表和洞察

### 4.3 AI 优化阶段

AI 优化不直接读取全部向量，只读取分析摘要。

建议输入结构：

```json
{
  "semantic_objective": "consistency",
  "group_summaries": [
    {
      "unit_id": 1,
      "variable_case_hash": "abc123",
      "sample_count": 5,
      "mean_pairwise_similarity": 0.72,
      "semantic_dispersion": 0.28,
      "outlier_count": 2,
      "interpretation": "一致性不足，存在语义漂移",
      "representative_outputs": ["...", "..."],
      "outlier_outputs": ["..."]
    }
  ]
}
```

优化模型根据 `semantic_objective` 决定建议方向：

- consistency：减少语义漂移
- diversity：增加候选差异，但保持主题边界
- balanced：调整到目标区间

## 5. 模型管理方案

### 5.1 配置目标

用户应能在模型管理页简单配置 embedding 模型，不需要理解所有厂商差异。

推荐在模型配置中增加：

| 字段 | 默认值 | 说明 |
|---|---|---|
| `model_type` | `chat` | `chat` / `embedding` / `rerank` |
| `embedding_api_style` | `openai_compatible` | embedding 调用风格 |
| `embedding_dimensions` | 空 | 可选指定输出维度 |
| `embedding_batch_size` | `16` | 批量请求大小 |
| `embedding_max_input_tokens` | 空 | 输入截断参考 |

### 5.2 首批支持范围

MVP 只支持：

- OpenAI-compatible `/v1/embeddings`
- 本地 OpenAI-compatible 服务，例如 vLLM、llama.cpp 兼容服务

暂不在第一版做：

- Gemini 原生接口
- Ollama 原生 `/api/embed`
- DashScope 原生接口
- 任意自定义 HTTP 映射器

这些可以作为 adapter 扩展点预留。

## 6. 分析报告展示方案

报告不应只显示“稳定性分数”，而应显示目标相关解释。

推荐展示结构：

```text
语义目标：一致性 / 多样性 / 平衡
可比输出组数量：N
样本不足组数量：M
整体结论：当前输出在 X 个变量组合中存在语义漂移
```

表格列建议：

| 列 | 说明 |
|---|---|
| 测试单元 | unit 名称 |
| 变量组合 | 变量摘要或 case 编号 |
| 语义目标 | consistency / diversity / balanced |
| 样本数 | 成功输出数 |
| 平均相似度 | 中性指标 |
| 语义离散度 | 中性指标 |
| 离群数 | 风险定位 |
| 判断 | 目标相关解释 |

图表建议：

- 单元级平均相似度柱状图
- 变量 case 分组散点图
- 离群输出列表

## 7. 与 AI 评分的关系

Embedding 指标负责“输出之间像不像”，AI 评分负责“输出质量好不好”。两者应该组合解释。

| AI 评分 | 语义目标 | Embedding 表现 | 优化方向 |
|---|---|---|---|
| 低 | consistency | 低一致性 | 收紧约束，明确标准 |
| 低 | consistency | 高一致性 | 当前稳定地产生低质量输出，修改任务目标或示例 |
| 高 | consistency | 低一致性 | 保留优点，减少漂移 |
| 高 | diversity | 高一致性 | 增加创意维度 |
| 高 | diversity | 低一致性 | 检查是否偏题，保留有效变化 |
| 低 | diversity | 低一致性 | 先保证主题边界，再扩大多样性 |

## 8. 存储策略

MVP 不持久化完整向量，只缓存分析结果。

理由：

- 向量体积大
- embedding 模型不同不可比
- 第一版目标是报告与优化，不是检索系统

需要记录的元信息：

- embedding provider
- embedding model
- embedding dimension
- input hash
- analysis version
- semantic objective
- threshold config

第二阶段再考虑持久化向量，用于历史趋势和复算节省成本。

## 9. 错误处理

| 错误 | 处理方式 |
|---|---|
| 未配置 embedding 模型 | 分析模块返回可读错误，引导去模型管理页配置 |
| 样本数不足 | 该组标记为 `insufficient_samples` |
| 变量组合不同 | 不直接比较，只做分组汇总 |
| embedding 调用失败 | 保留已有分析结果，提示具体 provider/model |
| 输入过长 | 截断并在结果中标记 `input_truncated=true` |
| 维度不一致 | 中止该批次，提示模型配置异常 |

## 10. 推荐落地顺序

1. 补齐配置模型：让系统知道哪些模型是 embedding 模型。
2. 建立 embedding client：先支持 OpenAI-compatible。
3. 建立分组与指标计算纯函数：先不接 API，方便测试。
4. 接入分析模块：生成报告数据和洞察。
5. 接入 AI 优化：把分析摘要加入优化上下文。
6. 前端展示：报告页展示目标、分组、离群输出。
7. 后续扩展 adapter 与缓存策略。

