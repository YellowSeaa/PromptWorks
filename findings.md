# 调研发现

## 初始假设

- 该功能大概率可做，但需要先定义“稳定性”的业务口径，否则 embedding 只能作为辅助信号。
- 供应商接口未必完全统一，但存在足够清晰的抽象层，可在 PromptWorks 中做一层适配。
- 本地部署的 embedding 通常可通过 OpenAI 兼容接口、HTTP 标准接口或各自 SDK 接入，配置粒度可能比第三方更碎。

## 待验证点

- PromptWorks 当前模型管理是否已经抽象出 provider / model / endpoint / api key 这类字段
- 主流 embedding 提供商是否支持统一的 `input -> vector` 模式
- 本地方案是否能用单一配置描述，还是必须按后端类型分支
- 稳定性评估是否能直接服务于分析报告与 AI 优化闭环

## 已确认的仓库现状

- 模型管理页已经有 provider / model 两层结构，且 provider 支持 `base_url`、`api_key`、`default_model_name`，model 支持 `capability`、`context_length`、成本字段。
- 现有分析体系是模块化的，`AnalysisResult` 允许返回 `data_frame`、`columns_meta`、`insights`、`extra`，适合新增稳定性指标模块。
- 前端优化页已经保留了模型选择器，说明项目里并不排斥把“模型能力”暴露到配置和分析环节里。

## 初步外部结论

- OpenAI embeddings 已经是标准化 REST 入口，官方明确提供 `v1/embeddings` 和 `text-embedding-3-small / large`。
- Azure OpenAI 的 embedding 走法与 OpenAI 很接近，核心差异主要在 base_url、资源名和鉴权细节。
- Google Gemini embeddings 是原生 `embedContent` 风格，不是 OpenAI embeddings 形态。
- 阿里云百炼 embedding 有自己的向量化接口，同时也提供 OpenAI 兼容接口，属于“双轨制”。
- 火山引擎方舟、硅基流动、千帆都提供了 OpenAI 兼容入口或适配器，适合在 PromptWorks 里做统一接入层。
- ModelScope 和本地推理框架（vLLM、llama.cpp）都能提供 OpenAI-compatible server，这对本地部署特别友好。
- DeepSeek 官方公开文档强调 OpenAI/Anthropic 兼容，但我在当前调研里没有看到明确的 embeddings 官方参考页，因此不能把它当成默认统一接口。
- Moonshot 公开文档当前更明显的是 Chat Completions 入口；embedding 公开入口在本轮没有查到，暂不建议作为 embedding 统一层的首批重点。

