# ComicCraft AI · 可编辑、可回退的漫画创作工作室

**简体中文** · [English](README.en.md)

[![CI](https://github.com/Seigi-91/comiccraft-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Seigi-91/comiccraft-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)

从创作灵感、角色档案和分镜，到连贯漫画、可编辑气泡与局部精修。基于 **React + FastAPI + LangGraph + SQLite + Pillow**，面向本机创作和可审阅的人机协作。

**公开仓库提供源码、文档和成稿供浏览；完整创作网站需要在本机运行。** 默认使用 ChatGPT 协作回填，不是自动控制桌面客户端，也不是免费代理模型 API。无需 API key 即可启动网站；模型创作需要你已有的 ChatGPT 或实际可用的模型服务。

**[免安装气泡编辑体验](https://seigi-91.github.io/comiccraft-ai/demo.html)** · [在线静态展示](https://seigi-91.github.io/comiccraft-ai/) · [功能与完整操作手册](docs/USER_GUIDE.md) · [Windows 一键安装](docs/INSTALL.md) · [安装与配置](docs/SETUP.md) · [架构与接口](docs/ARCHITECTURE.md) · [演示与下载](https://github.com/Seigi-91/comiccraft-ai/releases)

## 看看成稿

示例《雨夜留灯》：少女在雨夜旧书店发现小猫，带它进门，留下一盏灯。

![六格漫画预览](outputs/rain-night-light/雨夜留灯-气泡避让预览.jpg)

[完整手部精修成稿 PNG](outputs/rain-night-light/雨夜留灯-手部精修成稿.png) · [手部精修前后对比](outputs/rain-night-light/雨夜留灯-手部精修前后对比.jpg)

![创作工作区](docs/images/workspace.png)

## 已实现

| 能力 | 内容 |
|---|---|
| 六个 Agent | 剧情策划、分镜、台词、画面设计、视觉审核、排版；明确职责和结构化输出 |
| 小说改编 | 粘贴/TXT/Markdown、章节分段、忠实/适度/自由改编、来源快照、大纲审阅后继续原有漫画流程 |
| 创作编辑 | 大纲、分镜、台词表单编辑；下游失效提示与阶段继续 |
| 角色档案 | 身份、性格、外貌、背景、关系、语言风格；多个服装方案切换 |
| 人物连续性 | 向生图与审核传递角色表、开场/前格参考；失败格修订 |
| 漫画气泡 | 画面中拖动、缩放、改字、字号、尾尖方向长度、增删、类型切换 |
| 视觉排版 | 查看实际分镜，识别脸、手、道具保护框，检查气泡越界与交叠 |
| 局部精修 | 圈选多块蒙版、ChatGPT 回填或编辑 API、对比滑块、确认采用 |
| 像素保护 | 精修候选只采用蒙版内像素，未选原始分镜像素保持不变 |
| 生产工作台 | 每格设定快照与请求记录、章节批次、实验候选对比、非破坏特效层 |
| 版本管理 | 修改前备份整个章节，恢复台词、图片、气泡和特效状态 |

![素材生产工作台](docs/images/production.png)

## Windows 一键安装

下载 [Windows 安装启动器 ZIP](https://github.com/Seigi-91/comiccraft-ai/releases/download/v2.5.0/ComicCraft-AI-Windows-Installer.zip)，解压后双击 `Install-ComicCraft-Auto.cmd`，安装官方连接器并完成本人登录；只安装网站可使用 `Install-ComicCraft.cmd`。需要网络；缺少 Python/Node 时通过 winget 安装，有系统权限要求时仍需自行确认。完整流程、升级与验证边界见 [INSTALL](docs/INSTALL.md)。

启动后首页可一键导入《雨夜留灯》完整可编辑示例，**不调用模型**；重复导入会打开旧示例，不覆盖修改。首页还提供环境诊断。

## 5 分钟启动（依赖下载时间另计）

需要 **Python 3.11+、Node.js 20+、Git**，建议先使用 Windows。

```powershell
git clone https://github.com/Seigi-91/comiccraft-ai.git
cd comiccraft-ai
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

浏览器打开 **http://127.0.0.1:8000**。脚本创建虚拟环境、复制 `.env.example`、安装依赖并构建前端。

手动安装及 macOS/Linux 说明见 [SETUP](docs/SETUP.md)。从公开仓库安装后是新数据库；首页可显式导入预生成示例，保留原始来源标记，不恢复作者电脑中的私有项目记录。

## 文字和图片，分别选择自己的模型

在「创作团队与设置」中分别保存「文字与视觉模型连接」和「图片模型连接」。密钥各自独立，留空保留已有值，也可以明确清除；不会在配置读取接口回显。

| 使用方式 | 文字/视觉设置 | 图片设置 |
|---|---|---|
| 官方 Codex 自动连接 | ChatGPT 登录的官方 CLI | 内置生图需实测，或独立选 API / 人工回填 |
| 全程人工协作 | 本机 ChatGPT 回填 | 本机 ChatGPT 回填 |
| 自动生成 | API 地址 + 文字/视觉模型 + Key | API 地址 + 图片模型 + Key |
| 混合创作 | API 或 ChatGPT | 独立选择 API 或 ChatGPT |

文字采用 OpenAI 兼容 `/chat/completions`，视觉模型还须支持图片输入；图片使用 `/images/generations`，有参考图或蒙版时需支持 `/images/edits`。不是每家供应商的私有协议都能直接填入。保存配置不会产生付费测试，也不代表已验证账户额度。

[完整模型连接说明](docs/MODEL_CONNECTIONS.md) · [能力与实际验证状态](docs/PROVIDERS.md)。免安装体验只使用预生成图片，不演示 AI 生成，刷新会重置修改；完整创作仍在本机应用中进行。

## ChatGPT 协作如何工作

1. 创建项目、角色和章节，点击生成。
2. 网站给出当前 Agent 的完整任务，复制到 ChatGPT；**同时附上任务要求的参考图片**。
3. 将文字 JSON 粘回网站，或上传真实生成的图片。
4. 网站验证结果，LangGraph 继续下一阶段；审核未通过时重绘失败格。
5. 全部通过后本机合成 PNG，台词由排版器绘制，不依赖生图模型画字。

本仓库漫画样例由创作会话中的图像工具生成，再通过同一回填流程导入。该工具没有作为网站后台接口开放。生成质量与角色一致性需要实际查看，不能只依据模型评分。

## 自动接口与边界

- 可配置 OpenAI 兼容文字/视觉/生图 HTTP 服务，以及独立 `/images/edits` 图像编辑服务；密钥只放本机 `.env`。
- 图片 API 支持文生图与 multipart 参考图生成；服务须同时支持 `/images/generations` 和 `/images/edits`，不能把纯文字模型当作生图服务。
- ChatGPT 模式中的尺寸和风格是提示词约束，**不是 seed、步数或去噪强度等底层推理参数**。
- 没有完整向量 RAG；当前使用角色资料及最近三章大纲构造上下文。
- 批次是单进程本地调度，暂停/取消不强杀当前项；不提供分布式任务保证。
- 无登录、租户隔离和生产级权限控制。默认只绑定 `127.0.0.1`，不要直接将当前版本开放到公网。
- 气泡保护框依赖视觉判断，可能漏检；手动位置、蒙版接缝和特效遮挡仍需人工检查。

## 官方 ChatGPT 自动连接（Codex App Server）

新用户可双击自动连接安装器，安装后完成本人ChatGPT登录，在设置向导中验证并启用；之后文字、视觉和图片自动返回网站，无需逐阶段粘贴JSON。API与人工模式保留。[完整步骤与范围](docs/CODEX_CONNECTION.md)

**v2.5本机真实向导：文字、附图识别、生图全部通过。** 修复了v2.4只等待固定图片文件名的问题，改为导入官方结构化生成附件；旧失败记录保留。每个新用户仍需使用自己的账户并验证权限和额度。已有人工待办支持“改用自动连接继续”。

每格生成后立即保存，恢复时仅复用输入匹配的已完成格；审核按实际图片和参考依赖复用。[同类项目/论文调研](docs/AUTOMATION_RESEARCH_2026-11-02.md) · [效率回归与边界](benchmarks/AUTOMATION_EFFICIENCY.md)

## 小说改编入口

打开项目，点击「小说改编 · 导入原著」：预览并保存小说，选择片段、改编方式、1–24格篇幅与保留事实，创建漫画章。点击生成后先审阅可编辑改编方案，再继续现有分镜、台词和绘画。原著独立保存，不替换旧稿；普通灵感创作、气泡、精修和版本回退继续可用。导入/建章不调用模型，生成时使用你已有的ChatGPT或API。

支持单次30万字符、2MB文本文件，长章分为最多8000字符的片段。当前按片段逐章改编，尚非整本长篇一键自动制作。[完整小说改编说明](docs/NOVEL_ADAPTATION.md)

## v2.2：可追溯知识与 ChatGPT 对照实验

六角色共 24 张知识卡：16 张有定位到章节的教学/从业者原则依据、2 张有同类项目工程先例、6 张明确属于项目规则。每张卡都有适用条件、局限、原创正反例、检查项与审阅状态。资料只支撑所列原则，不代表机构认可或生成效果已证实。

- [资料调研与排除记录](knowledge/RESEARCH.md) · [完整知识卡目录](knowledge/CARD_CATALOG.md)
- 检索按角色硬过滤、保留核心卡，再按中英关键词加权匹配专项卡；无关查询不凑满条目。每次生成冻结完整知识快照，同一任务恢复时沿用原快照。
- [离线检索对照](benchmarks/KNOWLEDGE_EVALUATION.md)：维护者编写的 24 个相关查询，前三项命中率从 87.5% 到 100%；6 个无关查询不再填入无关专项卡。小样本、同团队编写，只是回归证据。
- 设置页各 Agent 下可创建有/无额外知识的成对任务：冻结提示词与差异，复制到本机 ChatGPT 的两个新对话，回填真实 JSON，再逐项观察评分、完整后揭盲。[操作与盲评限制](benchmarks/CHATGPT_AB_PROTOCOL.md)。不自动调用 API；实验比较文字建议，漫画画质提升仍待实测。
- 一致性评测的已知分数须附逐项观察，并绑定最终成稿指纹。历史无观察评分不再视为完整通过。
- [同类项目代码调研与实际采纳边界](docs/UPSTREAM_RESEARCH_2026-11-02.md)：参考 OpenManga 的规则版本/差异、TT_AutoManga 的单项可审阅流程、comicsol 的证据化视觉检查；没有移植其完整运行系统。

## 专业知识与可控生产

六个 Agent 各有 4 张[专业知识卡](knowledge/README.md)，本地按角色与任务检索后接入实际提示词。分镜师可使用导演式叙事任务、景别、轴线/正反打、动作衔接和格间时间知识。它是原创应用笔记与来源链接，不是教材转载或模型微调；生成状态保存知识卡指纹。

角色可审批锁定，解锁后的草稿不改变正在使用的审批版，重新审批后才用于新生成。生产工作台提供六维人工一致性评测，绑定图片及台词/特效状态。设置页可显式验证五类模型能力，并设置每任务 API 请求预留上限；调用记录保留服务返回的数值 usage，未知金额显示未知。批次仍是单实例调度，新增数据库租约与心跳用于防重复进入，不宣称跨系统恰好一次计费。

[知识库](knowledge/README.md) · [质量、预算与恢复](docs/PRODUCTION_SAFETY.md) · [一致性基准](benchmarks/consistency-cases.json)

## 测试

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
```

当前包含 62 项后端测试；GitHub Actions 分别运行 Python 测试及前端构建。测试使用隔离数据库、确定性回填与模拟 HTTP，不声称验证了真实付费模型的质量。

## 目录与文档

- `app/`：API、Agent、LangGraph、模型适配、排版和数据持久化。
- `frontend/`：React 编辑器、角色档案、精修与生产工作台。
- `skills/`：项目原创规则及保留许可、固定版本的上游方法。
- `tests/`：流程、版本、像素保护、批次和特效测试。
- `outputs/rain-night-light/`：示例漫画与修订对比。
- `videos/ComicCraft-AI-demo-editable/`：HyperFrames 可编辑视频工程。

详见 [用户手册](docs/USER_GUIDE.md)、[安装配置](docs/SETUP.md)、[架构](docs/ARCHITECTURE.md)、[贡献指南](CONTRIBUTING.md)、[安全说明](SECURITY.md)、[第三方许可](THIRD_PARTY_NOTICES.md)。

## 许可

项目原创代码与文档采用 [MIT](LICENSE)。上游技能、字体、音乐、JavaScript 等第三方资源保留各自许可，**不因根目录 MIT 而改换许可**。示例漫画为 AI 生成的虚构人物作品，仅作为效果示例提供；第三方素材详见 [许可清单](THIRD_PARTY_NOTICES.md)。

## 继续参与

如果编辑流程对你有帮助，欢迎点 Star 留作收藏。安装反馈、脱敏的服务兼容报告和文档改进同样有价值。

[同类项目调研与优缺点](docs/COMPETITIVE_ANALYSIS.md) · [下一步路线图](docs/ROADMAP.md) · [服务兼容证据](docs/PROVIDERS.md) · [问题与需求反馈](https://github.com/Seigi-91/comiccraft-ai/issues/new/choose)
