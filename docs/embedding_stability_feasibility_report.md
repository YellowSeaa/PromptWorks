# 基于 Embedding 的输出稳定性评估功能可行性报告

日期：2026-06-17  
项目：PromptWorks  
结论级别：建议进入 MVP 设计与小范围实现

## 1. 结论摘要

基于 embedding 模型评估 Prompt 输出稳定性是可行且有用的，尤其适合 PromptWorks 这类已经具备多轮测试、AI 评分、分析报告和 AI 优化闭环的平台。

建议把该能力定位为“语义稳定性 / 语义漂移检测”，而不是替代现有 AI 评分。它擅长回答：

- 同一个 Prompt 在多轮运行中，语义是否保持一致
- 同一个测试单元下，输出是否出现语义离群样本
- 不同 Prompt 版本之间，语义变化是收敛、漂移还是发散
- AI 优化后，是否牺牲了原有语义意图

接口层面，embedding 的抽象比 chat completion 更容易统一。主流接口都可以抽象为：

```text
输入文本或文本数组 -> embedding 向量数组 -> 相似度 / 聚类 / 离群分析
```

但“接口完全统一”不成立。更准确的判断是：可以在 PromptWorks 内部建立统一 EmbeddingProvider 抽象，并优先支持 OpenAI-compatible `/v1/embeddings`，再为 Google Gemini、部分国内厂商原生接口和本地服务做薄适配。

## 2. 对 PromptWorks 的业务价值

### 2.1 在分析报告中的价值

当前 PromptWorks 已经有耗时、tokens、成本和 AI 评分等分析能力。Embedding 稳定性可以补上一个重要维度：输出内容的语义一致性。

建议在分析报告中新增“输出稳定性”模块，核心指标包括：

| 指标 | 含义 | 报告价值 |
|---|---|---|
| 平均语义相似度 | 同一测试单元多轮输出两两相似度平均值 | 判断输出整体是否稳定 |
| 最低相似度 | 最相异两次输出之间的相似度 | 暴露最严重漂移 |
| 语义方差 / 离散度 | 输出向量围绕中心向量的分散程度 | 判断模型是否容易发散 |
| 离群输出数 | 与中心语义距离过大的输出数量 | 帮用户快速定位异常样本 |
| 版本间语义保持度 | 优化前后或版本间输出的相似度 | 判断优化是否偏离原意 |

这些指标适合与现有 AI 评分组合使用：

- AI 评分低 + 稳定性低：Prompt 本身约束不足，优先优化指令结构与输出格式
- AI 评分低 + 稳定性高：Prompt 稳定地产生低质量结果，优先修改目标、评价标准或上下文
- AI 评分高 + 稳定性低：单次看起来好，但批量输出风险高，需要增强约束
- AI 评分高 + 稳定性高：可作为优秀版本候选

### 2.2 给 AI 优化功能提供数据

Embedding 稳定性可以为 AI 优化提供更结构化的上下文，而不是只把一批原始输出塞给优化模型。

可提供的数据包括：

- 哪个测试单元最不稳定
- 哪些输出是离群样本
- 离群样本与中心输出的语义差异摘要
- 当前版本与历史版本的语义保持度
- 优化目标：提高稳定性、降低离群率、保持原语义不漂移

这会让 AI 优化建议更有方向。例如：

```text
请优化 Prompt，使其在保持核心语义不变的前提下，降低多轮输出之间的语义离散度；重点处理这些离群输出暴露的问题：……
```

## 3. 技术可行性

### 3.1 评估方法可行

推荐的基础算法很成熟：

1. 对同一测试单元下每次成功输出生成 embedding
2. 对向量做归一化
3. 计算余弦相似度
4. 用中心向量、两两相似度、离群阈值计算稳定性指标
5. 将指标写入分析模块结果，并将关键异常样本传给 AI 优化

推荐第一版采用简单、可解释的规则：

```text
stability_score = 平均余弦相似度 * 100
```

辅助指标：

```text
semantic_drift = 1 - 与中心向量的相似度
outlier = 与中心向量相似度 < 0.80
```

阈值建议作为可配置项，不要写死为产品真理。不同任务类型差异很大：

- 分类、结构化抽取、摘要：稳定性阈值可以较高
- 创意写作、开放式回答：稳定性阈值应较低
- 多变量测试：要按变量组合分别比较，避免把本来不同的输入混在一起

### 3.2 与现有架构匹配

PromptWorks 当前已有几个天然接入点：

- 模型管理页已有 provider/model/base_url/api_key/default_model_name 等配置基础
- `LLMModel.capability` 可以扩展为区分 chat、embedding、rerank 等模型能力
- 分析模块协议已有 `data_frame`、`columns_meta`、`insights`、`extra`，可以承载稳定性指标和图表
- AI 优化页已经有模型选择与评分摘要，适合追加“稳定性摘要”和“离群输出”

因此不需要推倒重来。更合理的实现方式是：

1. 在模型管理中允许配置 embedding 模型
2. 后端新增统一 embedding 调用服务
3. 分析模块读取测试输出并计算稳定性
4. AI 优化服务读取稳定性摘要作为辅助上下文

### 3.3 需要注意的局限

Embedding 稳定性不是万能指标：

- 相似度高不代表事实正确
- 相似度高不代表格式合规
- 相似度低也不一定是坏事，开放式任务可能本来就需要多样性
- 不同 embedding 模型的向量空间不可直接混算
- 多语言、长文本、代码、JSON 输出对 embedding 模型的要求不同

所以第一版应把它作为“稳定性信号”，而不是一票否决的质量分。

## 4. 市面接口统一性调研

### 4.1 统一抽象是否成立

成立，但要分层。

内部建议统一成：

```python
class EmbeddingClient:
    def embed_texts(self, texts: list[str], model: str) -> list[list[float]]:
        ...
```

配置建议统一成：

| 字段 | 用途 |
|---|---|
| provider_id | 复用模型提供商 |
| model_id / model_name | 指向 embedding 模型 |
| base_url | 支持云端或本地服务 |
| api_key | 云端鉴权，本地可为空或填占位值 |
| api_style | `openai_compatible` / `gemini` / `dashscope_native` / `custom_http` |
| dimensions | 可选，部分模型支持指定维度 |
| max_input_tokens | 输入截断或分片参考 |
| batch_size | 批量 embedding 控制 |
| normalize | 是否归一化向量 |

### 4.2 第三方模型提供商

| 提供商 | Embedding 支持 | 接口统一性 | 接入建议 |
|---|---:|---|---|
| OpenAI | 支持 | `/v1/embeddings` 标准形态 | 第一优先级 |
| Azure OpenAI | 支持 | 与 OpenAI 接近，但 endpoint / deployment / api-version 有差异 | 第一优先级，需单独适配 URL |
| Google Gemini | 支持 | 原生 `embedContent`，不是 OpenAI 风格 | 第二优先级，独立 adapter |
| 阿里云百炼 / DashScope | 支持 | 有 OpenAI 兼容接口，也有原生接口 | 第一优先级走兼容模式 |
| 硅基流动 | 支持 | 文档提供 embeddings 创建接口，OpenAI 风格明显 | 第一优先级 |
| 火山引擎 Ark | 支持 | 有向量化 API，并提供 OpenAI SDK 兼容说明 | 第一优先级，但需按模型名和 endpoint 校验 |
| 智谱 GLM | 支持 | API 形态接近现代 REST，需按官方字段适配 | 第二优先级 |
| 百度千帆 | 支持 | 提供 OpenAI 兼容相关能力，但鉴权和模型命名需确认 | 第二优先级 |
| ModelScope | 谨慎支持 | 有标准化 API-Inference 与 OpenAI-compatible 部署能力，embedding 需按具体模型/部署确认 | 第二优先级，适合开源模型托管 |
| Anthropic | 不适合作为首批 | 官方文档提示没有自家 embedding 模型，建议使用 Voyage AI 等方案 | 不作为内置 embedding provider |
| DeepSeek | 不建议首批默认支持 | 当前调研未确认官方 embedding 端点 | 可保留自定义 OpenAI-compatible |
| Moonshot | 不建议首批默认支持 | 当前调研未确认公开 embedding 端点 | 可保留自定义 OpenAI-compatible |

### 4.3 本地部署方案

本地部署非常可行，尤其适合企业内网或隐私敏感场景。

| 方案 | 接口形态 | 优点 | 注意点 |
|---|---|---|---|
| vLLM | OpenAI-compatible server，支持 embeddings 任务 | 与云端统一度高，适合 GPU 服务化 | 模型需支持 embedding task |
| llama.cpp server | OpenAI 兼容能力较强，适合轻量本地模型 | 部署轻，CPU/Metal 可用 | 不同版本参数和模型支持需验证 |
| Ollama | 有 `/api/embed`，也提供 OpenAI 兼容能力 | 本机体验简单 | 原生接口与 OpenAI 兼容接口字段不同 |
| Xinference | 支持多种 embedding / rerank 模型服务化 | 模型管理能力较完整 | 需要额外服务运维 |
| TEI / Text Embeddings Inference | 专注 embedding 推理 | 性能和批处理友好 | 更偏专业部署，配置项较多 |
| sentence-transformers 自建 FastAPI | 完全可控 | 最灵活 | 需要自己定义接口、批处理和监控 |

对 PromptWorks 来说，首选策略是：

1. 本地服务优先要求提供 OpenAI-compatible `/v1/embeddings`
2. 对 Ollama 这类用户常见工具提供少量原生 adapter
3. 高级自定义 HTTP 留到后续，不建议第一版就做成万能表单

## 5. 是否能在模型管理页简单配置

可以，但需要对现有模型配置做轻量扩展。

当前模型管理页已经具备：

- provider
- base_url
- api_key
- model name
- capability
- concurrency_limit
- context_length
- cost fields

建议新增或规范化：

| 字段 | 位置 | 是否必需 | 说明 |
|---|---|---:|---|
| model_type | 模型级 | 必需 | `chat` / `embedding` / `rerank`，比自由文本 capability 更可靠 |
| embedding_api_style | 模型或 provider 级 | 必需 | 默认 `openai_compatible` |
| embedding_dimensions | 模型级 | 可选 | OpenAI text-embedding-3 系列等可能支持 |
| embedding_batch_size | 模型级 | 可选 | 控制批量请求 |
| embedding_max_input_tokens | 模型级 | 可选 | 用于截断或分片 |
| health_check_type | 模型级 | 可选 | chat 模型和 embedding 模型检查方式不同 |

前端交互可以保持简单：

- 添加模型时选择“模型用途”：对话 / Embedding
- 选择 Embedding 后隐藏 temperature、上下文生成类提示，显示维度、批量大小、最大输入长度
- “检测模型”按钮对 embedding 模型发送一个短文本，如 `PromptWorks embedding health check`
- 成功后展示向量维度、耗时、是否可批量

## 6. 推荐 MVP 范围

建议第一版控制范围，避免一次性做成复杂评测平台。

### 6.1 MVP 必做

- 支持 OpenAI-compatible embedding provider
- 支持在模型管理页配置 embedding 模型
- 新增统一 embedding client
- 新增分析模块：输出语义稳定性
- 在分析报告中展示稳定性得分、最低相似度、离群输出数
- AI 优化时附带稳定性摘要和离群样本

### 6.2 MVP 不做

- 不跨 embedding 模型比较历史向量
- 不做向量数据库
- 不做长期向量缓存复杂治理
- 不做所有厂商原生接口
- 不把稳定性分数作为唯一质量结论

### 6.3 第二阶段

- 增加 Gemini / Ollama / DashScope native adapter
- 增加版本间语义保持度分析
- 增加稳定性趋势图
- 增加按变量组合、输出格式、Prompt 版本聚合
- 增加缓存策略，避免重复 embedding 成本

## 7. 数据模型与流程建议

### 7.1 最小数据流

```text
Prompt 测试输出
  -> 过滤成功输出
  -> 调用 embedding 模型
  -> 计算相似度矩阵与中心向量
  -> 生成稳定性指标
  -> 写入分析结果 extra
  -> AI 优化读取摘要
```

### 7.2 是否需要持久化向量

MVP 可以不持久化完整向量，只缓存分析结果。原因：

- 向量体积较大
- 不同 embedding 模型结果不可混用
- 第一版主要用于报告和优化上下文，不需要检索

如果后续要支持历史趋势、版本对比、复算节省成本，可以新增表：

```text
prompt_test_output_embeddings
- id
- task_id
- unit_id
- experiment_id
- run_index
- provider_id
- model_id
- model_name
- embedding_dimension
- embedding_vector
- input_hash
- created_at
```

但这应作为第二阶段，而不是 MVP 前置条件。

## 8. 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| 输出过长导致 embedding 输入超限 | 分析失败或成本过高 | 截断、摘要后 embedding、配置 max_input_tokens |
| 创意任务被误判为不稳定 | 误导用户 | 按任务类型配置阈值，报告中解释适用场景 |
| 不同 embedding 模型不可比 | 历史指标混乱 | 记录 provider/model/dimension，不跨模型比较 |
| 云端 embedding 成本增加 | 用户顾虑 | 提供本地部署和批量缓存选项 |
| 原生接口差异 | 开发复杂度上升 | 第一版只做 OpenAI-compatible，后续 adapter 扩展 |
| 相似度高但事实错误 | 质量误判 | 与 AI 评分、规则校验、人工指标组合 |

## 9. 实施建议

推荐路线：

1. 先做 OpenAI-compatible embedding MVP
2. 模型管理页增加“模型用途 = Embedding”
3. 后端抽象 `EmbeddingClient`
4. 新增 `semantic_stability_summary` 分析模块
5. AI 优化 prompt 增加稳定性摘要输入
6. 用 2-3 个真实 Prompt 测试任务验证指标是否符合直觉

从工程成本看，这是中等规模功能，不是大重构。PromptWorks 已有的 provider/model 管理、分析模块和 AI 优化工作台都能复用。

## 10. 最终判断

该思路可行，且对 PromptWorks 有明确产品价值。

最重要的产品定位是：Embedding 稳定性不是“质量评分”的替代品，而是一个低成本、可解释、可批量计算的语义一致性信号。它能帮助用户发现多轮输出漂移，也能帮助 AI 优化功能从“凭一堆样本提建议”升级为“基于稳定性指标定向优化”。

建议进入下一步设计，优先实现 OpenAI-compatible embedding 接入与报告侧稳定性分析，再逐步扩展 Gemini、本地 Ollama/vLLM、DashScope 原生等适配器。

## 11. 参考资料

- [OpenAI Embeddings guide](https://developers.openai.com/api/docs/guides/embeddings)
- [OpenAI Embeddings API reference](https://developers.openai.com/api/reference/embeddings)
- [Azure OpenAI embeddings documentation](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/embeddings)
- [Google Gemini Embeddings documentation](https://ai.google.dev/gemini-api/docs/embeddings)
- [Anthropic Embeddings documentation](https://platform.claude.com/docs/en/build-with-claude/embeddings)
- [Alibaba Cloud Model Studio OpenAI-compatible embedding interfaces](https://www.alibabacloud.com/help/en/model-studio/embedding-interfaces-compatible-with-openai)
- [SiliconFlow Create Embeddings API](https://docs.siliconflow.com/en/api-reference/embeddings/create-embeddings)
- [Volcengine Ark OpenAI SDK compatibility](https://www.volcengine.com/docs/82379/1330626)
- [Volcengine Ark embedding API](https://www.volcengine.com/docs/82379/1523520)
- [Zhipu AI Embedding-3 documentation](https://docs.bigmodel.cn/cn/guide/models/embedding/embedding-3)
- [Zhipu AI text embedding API reference](https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E6%96%87%E6%9C%AC%E5%B5%8C%E5%85%A5)
- [Baidu Qianfan vector model documentation](https://cloud.baidu.com/doc/qianfan-docs/s/Um8r1tpwy)
- [Baidu Qianfan OpenAI SDK compatibility](https://ai.baidu.com/ai-doc/WENXINWORKSHOP/2m3fihw8s)
- [ModelScope API-Inference introduction](https://www.modelscope.cn/docs/model-service/API-Inference/intro)
- [ModelScope OpenAI-compatible deployment](https://www.modelscope.cn/docs/model-service/deployment/swingdeploy-openai-api-compatible)
- [vLLM OpenAI-compatible server documentation](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
- [Ollama API documentation](https://docs.ollama.com/api)
- [Ollama embeddings documentation](https://docs.ollama.com/capabilities/embeddings)
- [Hugging Face Text Embeddings Inference API](https://huggingface.github.io/text-embeddings-inference/)
- [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
