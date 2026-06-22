# Embedding 语义一致性与多样性分析实施 TODO

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 PromptWorks 中实现基于 embedding 的语义一致性与多样性分析，并将分析摘要接入 AI 优化。

**Architecture:** 第一阶段采用 OpenAI-compatible embedding 接入，分析时按 `task_id + unit_id + variable_case_hash` 分组计算中性指标，再根据测试单元的 `semantic_objective` 解释为一致性、多样性或平衡目标。MVP 不持久化完整向量，只在分析结果中返回指标、图表和 AI 优化摘要。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、pytest、pandas、Vue 3、Element Plus、TypeScript。

---

## 文件结构规划

### 后端新增文件

- `app/services/embedding_client.py`：统一 embedding client，首批支持 OpenAI-compatible `/v1/embeddings`。
- `app/services/semantic_similarity.py`：纯函数模块，负责变量哈希、向量归一化、余弦相似度、分组指标、目标解释。
- `app/services/analysis_modules/semantic_stability.py`：分析模块注册与处理逻辑。
- `tests/test_semantic_similarity.py`：纯函数单元测试。
- `tests/test_embedding_client.py`：embedding client 请求构造与错误处理测试。
- `tests/test_semantic_stability_analysis.py`：分析模块行为测试。

### 后端修改文件

- `app/models/llm_provider.py`：为模型增加 `model_type`、`embedding_api_style`、`embedding_dimensions`、`embedding_batch_size`、`embedding_max_input_tokens`。
- `app/schemas/llm_provider.py`：同步模型配置字段。
- `app/api/v1/endpoints/llms.py`：模型创建、更新、检测逻辑支持 embedding。
- `app/services/analysis_modules/__init__.py`：注册 semantic stability 分析模块。
- `app/services/analysis_runner.py`：确保 PromptTestTask DataFrame 带上输出文本、变量、单元配置和语义目标。
- `app/services/prompt_test_ai_scoring.py`：AI 优化建议上下文中加入 semantic analysis summary。
- `alembic/versions/*`：新增数据库迁移。

### 前端修改文件

- `frontend/src/types/llm.ts`：补充 embedding 模型配置字段。
- `frontend/src/views/LLMManagementView.vue`：模型用途与 embedding 配置表单。
- `frontend/src/types/analysis.ts`：补充 semantic analysis extra 类型。
- 分析报告相关视图：展示语义目标、分组指标和离群输出。
- `frontend/src/views/PromptTestOptimizationView.vue`：展示 AI 优化使用的语义摘要。
- `frontend/src/i18n/messages.ts`：新增中英文文案。

---

## Task 1: 数据模型与迁移

**Files:**

- Modify: `app/models/llm_provider.py`
- Modify: `app/schemas/llm_provider.py`
- Create: `alembic/versions/<revision>_add_embedding_model_config.py`
- Test: `tests/test_release_config.py`

- [ ] **Step 1: 写迁移健康测试**

检查新增 revision id 长度不超过 32，且 Alembic 仍只有一个 head。

Run:

```bash
uv run pytest tests/test_release_config.py -q
```

Expected: 当前测试通过；新增迁移后仍通过。

- [ ] **Step 2: 扩展 `LLMModel` 字段**

新增字段：

```python
model_type: str = "chat"
embedding_api_style: str | None = None
embedding_dimensions: int | None = None
embedding_batch_size: int | None = None
embedding_max_input_tokens: int | None = None
```

约束建议：

- `model_type`：`chat` / `embedding` / `rerank`
- `embedding_api_style`：MVP 默认 `openai_compatible`
- `embedding_batch_size`：默认 16，范围 1-128

- [ ] **Step 3: 扩展 Pydantic schema**

在 `LLMModelBase`、`LLMModelUpdate`、`LLMModelRead` 中补齐字段和校验。

- [ ] **Step 4: 创建 Alembic 迁移**

字段默认值：

```text
model_type = "chat"
embedding_api_style = null
embedding_dimensions = null
embedding_batch_size = null
embedding_max_input_tokens = null
```

- [ ] **Step 5: 运行迁移相关测试**

Run:

```bash
uv run pytest tests/test_release_config.py -q
```

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add app/models/llm_provider.py app/schemas/llm_provider.py alembic/versions tests/test_release_config.py
git commit -m "feat: 添加embedding模型配置字段"
```

---

## Task 2: Embedding Client

**Files:**

- Create: `app/services/embedding_client.py`
- Test: `tests/test_embedding_client.py`

- [ ] **Step 1: 写 OpenAI-compatible 请求测试**

覆盖：

- URL 为 `{base_url}/embeddings`
- 请求体包含 `model` 和 `input`
- 可选传 `dimensions`
- 支持批量 input

- [ ] **Step 2: 写错误处理测试**

覆盖：

- provider 未配置 base_url
- provider 未配置 api_key 且不是本地服务
- 响应缺少 `data[].embedding`
- 向量维度不一致
- HTTP 非 2xx

- [ ] **Step 3: 实现 `EmbeddingClient`**

建议接口：

```python
@dataclass(frozen=True)
class EmbeddingRequest:
    provider_id: int
    model_id: int
    texts: list[str]

class EmbeddingClient:
    def embed_texts(self, request: EmbeddingRequest) -> EmbeddingResult:
        ...
```

MVP 只实现 `openai_compatible`。

- [ ] **Step 4: 运行测试**

Run:

```bash
uv run pytest tests/test_embedding_client.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add app/services/embedding_client.py tests/test_embedding_client.py
git commit -m "feat: 添加embedding统一调用客户端"
```

---

## Task 3: 语义指标纯函数

**Files:**

- Create: `app/services/semantic_similarity.py`
- Test: `tests/test_semantic_similarity.py`

- [ ] **Step 1: 写变量哈希测试**

覆盖：

- key 顺序不同，hash 相同
- 值类型不同，hash 不同
- 空变量返回稳定值

- [ ] **Step 2: 写分组测试**

输入同一 unit 下不同变量组合，期望生成不同 `comparable_group`。

- [ ] **Step 3: 写指标计算测试**

覆盖：

- 两个完全相同向量，相似度为 1
- 正交向量，相似度接近 0
- 样本数不足时返回 `insufficient_samples`
- 离群输出能被识别

- [ ] **Step 4: 写目标解释测试**

覆盖：

- `consistency` 下低相似度给出“语义漂移”
- `diversity` 下高相似度给出“过度收敛”
- `balanced` 下区间外给出对应提示

- [ ] **Step 5: 实现纯函数**

核心函数建议：

```python
def build_variable_case_hash(variables: Mapping[str, Any] | None) -> str: ...
def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float: ...
def calculate_group_metrics(outputs: list[SemanticOutput]) -> SemanticGroupMetrics: ...
def interpret_metrics(metrics: SemanticGroupMetrics, objective: str) -> SemanticInterpretation: ...
```

- [ ] **Step 6: 运行测试**

Run:

```bash
uv run pytest tests/test_semantic_similarity.py -q
```

Expected: PASS。

- [ ] **Step 7: 提交**

```bash
git add app/services/semantic_similarity.py tests/test_semantic_similarity.py
git commit -m "feat: 添加语义一致性指标计算"
```

---

## Task 4: 分析数据加载增强

**Files:**

- Modify: `app/services/analysis_runner.py`
- Test: `tests/test_analysis_runner.py` 或新增相关测试

- [ ] **Step 1: 写 DataFrame 字段测试**

PromptTestTask 分析 DataFrame 应包含：

- `output_text`
- `variables`
- `variable_case_hash`
- `semantic_objective`
- `unit_id`
- `unit_name`
- `run_index`

- [ ] **Step 2: 修改 `_build_prompt_test_dataframe`**

从 experiment outputs 中提取：

- 输出文本
- 变量上下文
- run index
- unit extra/config 中的 semantic objective

- [ ] **Step 3: 样本不足不要报错**

只负责加载数据，样本数判断留给分析模块。

- [ ] **Step 4: 运行测试**

Run:

```bash
uv run pytest tests/test_analysis_runner.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add app/services/analysis_runner.py tests
git commit -m "feat: 扩展分析数据加载字段"
```

---

## Task 5: Semantic Stability 分析模块

**Files:**

- Create: `app/services/analysis_modules/semantic_stability.py`
- Modify: `app/services/analysis_modules/__init__.py`
- Test: `tests/test_semantic_stability_analysis.py`

- [ ] **Step 1: 写模块注册测试**

`GET /analysis/modules` 应包含：

```text
semantic_consistency_diversity
```

- [ ] **Step 2: 写无 embedding 模型配置测试**

执行模块时如果缺少 embedding 模型参数，应返回清晰错误。

- [ ] **Step 3: 写分组计算测试**

同一 unit 不同变量组合不互相比较。

- [ ] **Step 4: 写目标解释测试**

同样的相似度，在 `consistency` 与 `diversity` 下应生成不同判断。

- [ ] **Step 5: 实现分析模块**

模块参数建议：

```text
embedding_provider_id
embedding_model_id
objective_override 可选
outlier_threshold 可选
```

返回内容：

- `data_frame`：每个 comparable group 一行
- `columns_meta`：表格展示元数据
- `insights`：目标相关洞察
- `extra.charts`：图表配置
- `extra.semantic_summary`：供 AI 优化复用

- [ ] **Step 6: 运行测试**

Run:

```bash
uv run pytest tests/test_semantic_stability_analysis.py -q
```

Expected: PASS。

- [ ] **Step 7: 提交**

```bash
git add app/services/analysis_modules/semantic_stability.py app/services/analysis_modules/__init__.py tests/test_semantic_stability_analysis.py
git commit -m "feat: 添加语义一致性分析模块"
```

---

## Task 6: 模型管理页支持 Embedding 配置

**Files:**

- Modify: `frontend/src/types/llm.ts`
- Modify: `frontend/src/views/LLMManagementView.vue`
- Modify: `frontend/src/i18n/messages.ts`

- [ ] **Step 1: 扩展前端类型**

补齐：

```ts
model_type: 'chat' | 'embedding' | 'rerank'
embedding_api_style?: 'openai_compatible' | 'gemini' | 'ollama' | 'custom_http' | null
embedding_dimensions?: number | null
embedding_batch_size?: number | null
embedding_max_input_tokens?: number | null
```

- [ ] **Step 2: 更新模型表单**

添加“模型用途”选择。

当 `model_type = embedding` 时显示：

- API 风格
- 向量维度
- 批量大小
- 最大输入 tokens

- [ ] **Step 3: 更新模型表格**

增加模型用途标签，embedding 模型显示向量配置摘要。

- [ ] **Step 4: 更新文案**

中文和英文文案都写入 `frontend/src/i18n/messages.ts`。

- [ ] **Step 5: 构建验证**

Run:

```bash
npm --prefix frontend run build
```

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/types/llm.ts frontend/src/views/LLMManagementView.vue frontend/src/i18n/messages.ts
git commit -m "feat: 支持配置embedding模型"
```

---

## Task 7: 分析报告前端展示

**Files:**

- Modify: `frontend/src/types/analysis.ts`
- Modify: 分析报告相关视图文件
- Modify: `frontend/src/i18n/messages.ts`

- [ ] **Step 1: 扩展分析类型**

为 `extra.semantic_summary`、group metrics、outlier outputs 增加类型。

- [ ] **Step 2: 增加语义分析展示**

展示：

- 语义目标
- 可比输出组数量
- 样本不足组数量
- 平均相似度
- 语义离散度
- 离群输出数
- 目标相关判断

- [ ] **Step 3: 展示离群输出**

每个 group 最多展示 3 条离群输出，避免页面过长。

- [ ] **Step 4: 构建验证**

Run:

```bash
npm --prefix frontend run build
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/types/analysis.ts frontend/src frontend/src/i18n/messages.ts
git commit -m "feat: 展示语义一致性分析结果"
```

---

## Task 8: AI 优化接入语义摘要

**Files:**

- Modify: `app/services/prompt_test_ai_scoring.py`
- Modify: `frontend/src/views/PromptTestOptimizationView.vue`
- Test: AI 优化相关测试文件

- [ ] **Step 1: 写优化上下文测试**

当存在 semantic summary 时，生成推荐的 prompt 上下文应包含：

- semantic objective
- 不稳定或过度收敛的 group
- 离群输出摘要
- 推荐优化方向

- [ ] **Step 2: 修改优化上下文构造**

根据目标解释：

- `consistency`：要求减少漂移
- `diversity`：要求增加差异但不偏题
- `balanced`：要求回到目标区间

- [ ] **Step 3: 前端展示语义摘要**

在优化页摘要区展示 AI 使用了哪些语义分析信号。

- [ ] **Step 4: 运行测试**

Run:

```bash
uv run pytest tests -q
npm --prefix frontend run build
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add app/services/prompt_test_ai_scoring.py frontend/src/views/PromptTestOptimizationView.vue tests
git commit -m "feat: AI优化接入语义分析摘要"
```

---

## Task 9: 集成验证与文档

**Files:**

- Modify: `README.md`
- Modify: `docs/README_en.md`
- Modify: `docs/analysis/developer_guide.md`
- Modify: `docs/analysis/backend_interfaces.md`

- [ ] **Step 1: 更新中文 README**

增加 embedding 语义一致性与多样性分析说明。

- [ ] **Step 2: 同步英文 README**

按项目规则同步 `docs/README_en.md`。

- [ ] **Step 3: 更新分析模块开发文档**

说明：

- 可比输出集合
- 变量哈希
- 语义目标
- 分析结果 extra 结构

- [ ] **Step 4: 全量验证**

Run:

```bash
uv run poe test-all
npm --prefix frontend run build
```

Expected: PASS。

- [ ] **Step 5: 最终提交**

```bash
git add README.md docs/README_en.md docs/analysis/developer_guide.md docs/analysis/backend_interfaces.md
git commit -m "docs: 补充语义一致性分析文档"
```

---

## MVP 验收清单

- [ ] 模型管理页可以配置 embedding 模型
- [ ] embedding 模型检测逻辑能返回向量维度
- [ ] 同一变量组合多轮输出会计算相似度
- [ ] 不同变量组合不会被直接两两比较
- [ ] `consistency` 下低相似度会被解释为语义漂移
- [ ] `diversity` 下高相似度会被解释为过度收敛
- [ ] `balanced` 下区间外会被解释为偏离目标区间
- [ ] 分析报告能展示 group 级指标
- [ ] AI 优化能读取 semantic summary
- [ ] 后端 `uv run poe test-all` 通过
- [ ] 前端 `npm --prefix frontend run build` 通过

