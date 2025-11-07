![PromptWorks 标志](docs/logo.jpg)

中文 | [English](docs/README_en.md) | [更新记录](docs/UPDATES.md)

# PromptWorks 项目总览

PromptWorks 是一个聚焦 Prompt 资产管理与大模型运营的全栈解决方案，仓库内包含 FastAPI 后端与 Vue + Element Plus 前端。平台支持 Prompt 全生命周期管理、模型配置、版本对比与评估实验，为团队提供统一的提示词协作与测试工作台。

![](docs/frontend.png)

## ✨ 核心能力
- **Prompt 管理**：支持提示词的创建、版本迭代与标签归类，保留完整审计信息。
- **版本对比**：提供差异视图，快速识别提示词更新带来的内容变化。
- **模型运营**：集中管理可用大模型服务与调用配额，为 A/B 实验提供能力。
- **评估测试**：后端暴露实验执行、指标记录能力，前端已预置测试面板待接入。

## 🧱 技术栈
- **后端**：Python 3.10+、FastAPI、SQLAlchemy、Alembic、Redis、Celery。
- **前端**：Vite、Vue 3（TypeScript）、Vue Router、Element Plus。
- **工具链**：uv 进行依赖与任务管理，PoeThePoet 统一开发命令，pytest + coverage 保证质量。

## 🏗️ 系统架构
- **后端服务**：位于 `app/` 目录，采用 FastAPI + SQLAlchemy 分层结构，业务逻辑集中在 `services/`。
- **数据库与消息组件**：默认使用 PostgreSQL 与 Redis，可按需扩展 Celery 任务队列能力。
- **前端应用**：`frontend/` 目录基于 Vite 构建，提供 Prompt 管理与测试的交互界面。
- **统一配置**：通过根目录 `.env` 与前端 `VITE_` 前缀环境变量解耦各环境差异。

## 🚀 快速开始
### 0. 环境准备
- Python 3.10+
- Node.js 18+
- PostgreSQL、Redis（生产环境推荐）；本地可参考 `.env.example` 使用默认参数快速启动。

### 1. 后端环境初始化
```bash
# 同步后端依赖（包含开发工具）
uv sync --extra dev

# 初始化环境变量
cp .env.example .env

# 首次运行请先创建数据库与账号（以本地 postgres 超级用户为例）
createuser promptworks -P            # 若已存在同名用户可跳过
createdb promptworks -O promptworks
# 或执行以下 SQL：
# psql -U postgres -c "CREATE USER promptworks WITH PASSWORD 'promptworks';"
# psql -U postgres -c "CREATE DATABASE promptworks OWNER promptworks;"

# 同步数据库结构
uv run alembic upgrade head
```

### 2. 前端依赖安装
```bash
cd frontend
npm install
```

### 3. 启动服务
```bash
# 后端 FastAPI 调试服务
uv run poe server

# 在新终端中启动前端开发服务器
cd frontend
npm run dev -- --host
## 或者
uv run poe frontend
```
后端默认运行在 `http://127.0.0.1:8000`（API 文档访问 `/docs`），前端默认运行在 `http://127.0.0.1:5173`。

### 4. 常用质量校验
```bash
uv run poe format      # 统一代码风格
uv run poe lint        # 静态类型检查
uv run poe test        # 单元与集成测试
uv run poe test-all    # 顺序执行上述三项

# 在 frontend 目录执行构建生产包
npm run build
```

## 🧪 测试任务消息约定
- 若测试任务的 Schema 未显式提供 `system` 消息，平台会把当前 Prompt 快照以 `user` 角色注入消息列表，兼容仅识别用户输入的模型。
- Schema 中若包含 `system` 消息，则保持原有顺序，不会重复注入快照内容。
- 仍会保证测试输入（`inputs`/`test_inputs`）中的问题作为后续 `user` 消息发送，支持多轮回放。

## 🐳 Docker 一键部署
- **环境准备**：确保本机已安装 Docker 与 Docker Compose（Docker Desktop 或 NerdCTL 均可）。
- **启动命令**：
```bash
docker compose up -d --build
```
- **访问入口**：前端服务默认暴露在 `http://localhost:18080`，后端 API 为 `http://localhost:8000/api/v1`，数据库与 Redis 对应端口分别为 `15432` 与 `6379`。
- **停止/清理**：
```bash
docker compose down            # 停止容器
docker compose down -v         # 停止并删除数据卷
```

### 容器编排说明
| 服务 | 说明 | 端口 | 额外信息 |
| --- | --- | --- | --- |
| `postgres` | PostgreSQL 数据库 | 15432 | 默认账户、密码、库名均为 `promptworks` |
| `redis` | Redis 缓存/消息队列 | 6379 | 已启用 AOF，适合作为开发环境使用 |
| `backend` | FastAPI 后端 | 8000 | 启动前自动执行 `alembic upgrade head` 同步结构 |
| `frontend` | Nginx 托管的前端静态文件 | 18080 | 构建时可通过 `VITE_API_BASE_URL` 定制后端地址 |

> 提示：如需自定义端口或数据库密码，可在 `docker-compose.yml` 中调整对应环境变量与端口映射（当前示例采用 `15432`、`18080`），然后重新执行 `docker compose up -d --build`。

## ⚙️ 环境变量说明
| 名称 | 是否必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `APP_ENV` | 否 | `development` | 控制当前运行环境，用于日志等差异化配置。 |
| `APP_TEST_MODE` | 否 | `false` | 启用后输出 DEBUG 级别日志，建议仅在本地调试使用。 |
| `API_V1_STR` | 否 | `/api/v1` | 后端 API 的版本前缀。 |
| `PROJECT_NAME` | 否 | `PromptWorks` | 系统显示名称。 |
| `DATABASE_URL` | 是 | `postgresql+psycopg://...` | PostgreSQL 连接串，必须保证数据库可访问。 |
| `REDIS_URL` | 否 | `redis://localhost:6379/0` | Redis 连接地址，可用于缓存或异步任务。 |
| `BACKEND_CORS_ORIGINS` | 否 | `http://localhost:5173` | 允许跨域访问的前端地址，可用逗号分隔多个 URL。 |
| `BACKEND_CORS_ALLOW_CREDENTIALS` | 否 | `true` | 控制是否允许携带 Cookie 等认证信息。 |
| `OPENAI_API_KEY` | 否 | 空 | 集成 OpenAI 模型时填写对应密钥。 |
| `ANTHROPIC_API_KEY` | 否 | 空 | 集成 Anthropic 模型时填写对应密钥。 |
| `VITE_API_BASE_URL` | 前端必填 | `http://127.0.0.1:8000/api/v1` | 前端访问后端的基础地址，需写入 `frontend/.env.local`。 |

> 提示：复制 `.env.example` 为 `.env` 后，可在 `frontend/.env.example`（待创建）或 `.env.local` 中设置 `VITE_` 开头的变量，使得构建与运行环境保持一致。

## 🗂️ 项目结构
```
.
├── alembic/                # 数据库迁移脚本
├── app/                    # FastAPI 应用主体
│   ├── api/                # REST 接口定义与依赖注入
│   ├── core/               # 配置、日志、跨域等基础设施
│   ├── db/                 # 数据库会话与初始化
│   ├── models/             # SQLAlchemy 模型
│   ├── schemas/            # Pydantic 序列化模型
│   └── services/           # 业务服务封装
├── frontend/               # Vue 3 前端工程
│   ├── public/
│   ├── src/
│   │   ├── api/            # HTTP 客户端与请求封装
│   │   ├── router/         # 路由配置
│   │   ├── types/          # TypeScript 类型定义
│   │   └── views/          # 页面组件
├── tests/                  # pytest 用例
├── pyproject.toml          # 后端依赖与任务配置
├── README.md               # 项目说明文档
└── .env.example            # 环境变量模板
```

## 📡 API 与前端联动
- 后端提供 `/api/v1/prompts`、`/api/v1/test_prompt` 等接口供前端调用，当前前端示例使用本地 mock 数据，可在后续迭代中替换为真实 API。
- Prompt 详情页已预置版本 diff 组件与测试面板，接入接口后可实现端到端的提示词验证闭环。
- 测试任务列表默认展示新版任务入口，旧版“新建测试任务”按钮已隐藏，新版入口文案统一为“新建测试任务”。

## 🤝 贡献指南
1. 新建功能分支，遵循“格式化 → 类型检查 → 测试”工作流。
2. 开发完成后运行 `uv run poe test-all` 确保质量基线。
3. 提交 Pull Request，并在描述中说明变更范围与验证方式；本地提交信息建议使用简短中文描述。

欢迎提出 Issue 或改进建议，共建 PromptWorks！

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=YellowSeaa/PromptWorks&type=date&legend=top-left)](https://www.star-history.com/#YellowSeaa/PromptWorks&type=date&legend=top-left)
