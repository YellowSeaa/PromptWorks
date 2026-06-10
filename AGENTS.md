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
8. 若要求git commit，需要带中文信息，提交信息格式为：feat: 新增功能描述 / fix: 修复描述 / docs: 文档变更描述
9. 每次提交需要更新更新记录，记录在docs/UPDATES.md中