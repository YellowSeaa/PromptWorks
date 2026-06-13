# AI 优化目标版本设计

## 背景

Prompt 测试任务允许同一个 Prompt 下的多个版本进入同一任务，用于横向对比。当前 AI 优化建议按任务聚合生成，缺少明确的目标版本，导致多个版本同时参与测试时，生成的 `prompt_revision` 不知道应该基于哪个版本迭代。

本设计采用“任务级测试、版本级优化”的边界：多版本任务仍用于对比，AI 优化必须绑定一个目标 Prompt 版本。

## 目标

- 当测试任务包含多个 Prompt 版本时，用户进入优化前先选择目标版本。
- 优化页支持切换目标版本，但切换只更新查看上下文，不自动触发 LLM 生成。
- 每条优化记录绑定目标版本，并展示版本、生成时间、负责优化的 LLM。
- AI 优化建议中的“温度建议”改为“参数建议”，覆盖温度、top_p、max_tokens、response_format 等参数。
- 保持旧优化记录可读，前端兼容 `temperature_advice`。

## 非目标

- 不在第一版中为所有版本自动批量生成优化建议。
- 不改变测试任务允许多版本对比的能力。
- 不自动把分数最高版本保存为新版本。

## 用户流程

### 结果页入口

用户点击测试结果页的“AI 优化”按钮时：

1. 统计当前任务中实际引用的 Prompt 版本。
2. 如果只有一个版本，直接跳转优化页并携带该版本 ID。
3. 如果有多个版本，弹出目标版本选择框。
4. 弹窗按版本平均分从高到低排列，最高分靠左并显示“推荐”。
5. 用户选择版本后进入优化页。

版本卡片建议显示：

- Prompt 版本号。
- 平均分和有效评分数量。
- 主要短板维度。
- 最近测试时间或最近输出时间。

无有效评分时仍可选择版本，但排序放在有评分版本之后。

### 优化页

优化页以 `promptVersionId` 作为目标版本上下文：

- 顶部显示当前目标版本，并提供版本切换控件。
- 左侧当前 Prompt 只显示目标版本内容。
- 分数概览、问题原因、样例输出只聚合目标版本相关单元。
- 历史优化记录默认展示当前目标版本，也可切换查看全部记录。
- 切换版本后只刷新页面数据和历史，不自动生成新建议。
- 点击“生成/重新生成”时，才调用 LLM 生成当前目标版本的优化建议。

## 后端设计

### 数据模型

`prompt_test_optimization_recommendations` 增加字段：

- `prompt_version_id`: 目标 Prompt 版本 ID，外键指向 `prompts_versions.id`，删除版本时建议 `SET NULL`。

历史记录继续保留任务级归属，新增版本级归属后，同一任务可以拥有多个版本的优化记录。

### API

生成优化建议：

- `POST /api/v1/prompt-test/tasks/{task_id}/optimization-recommendations`
- 请求体新增 `prompt_version_id`。
- 后端校验该版本属于当前任务引用的同一个 Prompt，并且当前任务至少有一个单元使用该版本。

读取最近建议：

- `GET /api/v1/prompt-test/tasks/{task_id}/optimization-recommendations/latest?prompt_version_id=...`
- 传入版本 ID 时只返回该版本最近记录。
- 未传入时保留兼容行为，返回任务最近记录。

读取历史建议：

- 新增 `GET /api/v1/prompt-test/tasks/{task_id}/optimization-recommendations`
- 支持可选 `prompt_version_id`。
- 返回按 `created_at desc` 排序的优化记录列表。

### 生成逻辑

生成建议时只纳入目标版本相关数据：

- 只选择 `PromptTestUnit.prompt_version_id == prompt_version_id` 的单元。
- 只聚合这些单元对应的评分、输出和参数。
- 推荐 prompt 中明确给出目标版本内容。
- 其他版本可作为对照摘要加入上下文，但不参与 `prompt_revision` 的基准文本。

LLM 返回字段改为：

- `overall_advice`
- `parameter_advice`
- `model_advice`
- `prompt_revision`
- `validation_plan`

为兼容旧数据，读历史时不迁移旧 content；前端展示时使用 `parameter_advice ?? temperature_advice`。

## 前端设计

### 结果页弹窗

新增目标版本选择弹窗，复用结果页已有的单元、评分摘要和 Prompt 版本信息计算版本卡片。

排序规则：

1. 有有效平均分的版本排前。
2. 平均分高的排前。
3. 分数相同按最近测试时间倒序。
4. 没有评分的版本排后。

选择后跳转：

```text
prompt-test-optimization/:taskId?promptVersionId=<version_id>
```

### 优化页

优化页读取路由中的 `promptVersionId`：

- 若缺失且任务只有一个版本，自动补齐该版本。
- 若缺失且任务有多个版本，显示版本选择提示，不生成建议。
- 切换目标版本时更新 URL query，并重新加载该版本最近建议与历史。

历史记录列表显示字段：

- 目标版本。
- 生成时间。
- 优化 LLM。
- 状态。

点击历史记录后，将该记录内容填充到建议区域和改写草稿。

### 文案调整

- “温度建议”改为“参数建议”。
- 英文文案从 “Temperature Advice” 改为 “Parameter Advice”。

## 错误处理

- 目标版本不属于当前任务：返回 422，并提示“目标 Prompt 版本不属于当前测试任务”。
- 目标版本没有有效评分：返回 422，并提示“当前版本没有有效评分，无法生成优化建议”。
- 目标版本被删除或无法加载：优化页展示不可用提示，禁用生成按钮。
- 历史记录为空：展示空状态，不影响用户生成新建议。

## 测试计划

后端测试：

- 多版本任务生成建议时必须传目标版本。
- 只聚合目标版本的单元和评分。
- 不同版本生成的优化记录互不覆盖。
- latest 接口按 `prompt_version_id` 返回对应最近记录。
- `parameter_advice` prompt 要求存在，并兼容旧 `temperature_advice` 内容。

前端测试或手动验收：

- 单版本任务直接进入优化页。
- 多版本任务点击优化按钮弹出选择框，最高分版本显示推荐。
- 选择版本后优化页只显示该版本 Prompt 和评分。
- 切换版本不会自动调用生成接口。
- 历史记录显示版本、时间、优化 LLM，并可回填建议内容。
