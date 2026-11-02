# 贡献指南

欢迎通过 Issue 报告问题，通过 Pull Request 提交改进。请先阅读 README 的功能边界。

1. Fork 仓库并创建分支；安装 `.[dev]` 和前端依赖。
2. 说明复现步骤、预期/实际行为与必要截图，删掉密钥、账号和私有图片。
3. 改动前后运行 `python -m pytest -q` 和前端构建。
4. 涉及状态、回退或像素保护时增加隔离集成测试，不使用真实用户数据库。
5. 新的模型接口必须明确参数能力，不以占位图、虚假审核或静默降级掩盖失败。
6. 固定上游文件受 SHA 校验；不要直接修改其字节。修改原创 skill 或提交经审阅的新来源及许可。

提交内容需允许按本项目许可分发；第三方内容应同时提供来源和原许可。请勿提交 `.env`、数据库、回填会话或生成服务密钥。

## 可以从哪里开始 / Where to start

- Improve a confusing setup step after trying a clean install; include OS and exact commands.
- Submit a redacted provider compatibility report using the Issue form.
- Propose English UI localization for one screen, keeping existing Chinese labels intact.
- Suggest a reproducible six-panel consistency benchmark with explicit scoring criteria.

请先看 [路线图](docs/ROADMAP.md)，为较大的改动开一个有验收标准的提案。以上是贡献方向，不代表维护者已经创建或认领了对应 Issue。提交截图与作品需有公开展示权；我们不会自动公开用户漫画。
