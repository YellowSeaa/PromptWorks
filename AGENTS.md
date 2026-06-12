# 项目说明

PromptWorks 是一个聚焦 Prompt 资产管理与大模型运营的全栈解决方案，代码仓库包含 FastAPI 后端与 Vue + Element Plus 前端。平台支持 Prompt 全生命周期管理、模型调用、版本对比与指标跟踪，为团队提供统一展示与协同的智能运营后台。

# 开发规范

1. 本项目后端是python+fastapi开发，使用uv管理环境，使用poe配置任务，使用pytest测试
2. 后端开发完成后需要写对应的测试用例，并且通过uv run poe test-all测试
3. 项目前端使用Vue3+Element Plus开发，代码在./frontend中
4. 后端的api文件夹内文件仅实现接口定义、类型定义与检测、对应业务逻辑函数调用，具体业务逻辑写在services文件夹中
5. 每次开发任务完成并测试无误之后，将代码commit到本地git中（禁止：上传到云端和合并到dev或main），需要有简短的中文提交信息
6. 若要求更新README.md，需要同步修改英文版的docs/README_en.md
7. 编码统一要求utf-8
8. 若要求git commit，需要带中文信息，提交信息需遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：
   - `feat: 功能描述` — 新功能，触发 minor 版本升级
   - `fix: 修复描述` — Bug 修复，触发 patch 版本升级
   - `docs: 文档变更描述` — 仅文档变更，不触发版本升级
   - `chore: 杂项描述` — 构建、依赖等杂项，不触发版本升级
   - `refactor:` / `test:` / `style:` / `perf:` / `ci:` 等类型同样支持
   - 重大变更请在 commit body 中标注 `BREAKING CHANGE:`，触发 major 版本升级
9. 版本号由 [semantic-release](https://semantic-release.gitbook.io/) 自动管理，无需手动更新版本号或 CHANGELOG.md
10. 每次开发之前，若当前分支为`dev`或`main`，先切换为`dev`分支并拉取最新代码，然后创建新的开发分支
11. 若用户要求 AI 更新 `main` 分支或协助完成正式版发布，在完成 `main` 更新后，必须询问用户是否需要同步更新 `dev` 分支；同步方式优先建议从 `main` 到 `dev` 发起同步 PR，避免自动合并绕过冲突检查或分支保护。
