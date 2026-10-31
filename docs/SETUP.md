# 安装、配置与故障排查

## 环境

- Python 3.11+（CI 使用 3.11/3.12）；Node.js 20+；Git。
- 核心模式使用 SQLite，不要求 GPU、Redis、ChromaDB、MinIO、ComfyUI 或 SD。
- 使用 ChatGPT 协作需要你能够自行使用 ChatGPT。本网站不包含账号、额度或桌面自动化。
- 中文排版当前优先读取 Windows 微软雅黑/黑体。Linux/macOS 请配置下面的字体路径。

## Windows

运行根目录 `start.ps1`，或：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

已有 `.env` 时不要覆盖它。

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
npm --prefix frontend ci
npm --prefix frontend run build
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

将支持中文的字体路径写入 `.env` 的 `COMIC_FONT_PATH`，例如自己安装的 Noto Sans CJK 字体。不要直接使用不含中文字形的 DejaVu 来导出中文。

## 配置项

| 配置 | 用途 |
|---|---|
| `AI_PROVIDER=chatgpt_desktop` | 默认人工交接，不需要模型密钥 |
| `AI_PROVIDER=local_http` | 使用实际支持相关能力的 OpenAI 兼容 HTTP 服务 |
| `LOCAL_GPT_BASE_URL` / `LOCAL_GPT_API_KEY` | 文字、视觉、生图服务地址与可选密钥 |
| `DEFAULT_TEXT_MODEL` / `DEFAULT_VISION_MODEL` / `DEFAULT_IMAGE_MODEL` | 必须填写服务实际提供的模型名 |
| `IMAGE_EDIT_PROVIDER=chatgpt_desktop` | 蒙版精修原图/蒙版交接 |
| `IMAGE_EDIT_PROVIDER=openai` | multipart 图像编辑接口 |
| `IMAGE_EDIT_BASE_URL` / `IMAGE_EDIT_API_KEY` / `IMAGE_EDIT_MODEL` | 独立编辑服务，地址到 `/v1` 层；代码追加 `/images/edits` |
| `POSTGRES_URL` | 可选 PostgreSQL；留空用根目录 SQLite |
| `GPT_TIMEOUT` | 模型 HTTP 超时秒数 |
| `COMIC_FONT_PATH` | 支持中文的本机字体绝对路径 |

图像编辑接口必须支持 PNG 原图和蒙版，透明部分可改，返回 `data[0].b64_json`。接口异常会显示失败，不会返回伪造图片。默认不自动调整结果尺寸；同宽高比结果可在人工精修上传时明确允许对齐。

## 开发与测试

后端启动如上；另一终端：

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

前端开发地址为 `http://127.0.0.1:5173`。接口文档在后端 `/docs`，健康检查 `/health`。`pytest -q` 使用独立临时目录，不修改真实项目数据库。

浏览器脚本默认依赖作者机器的 Playwright/Edge 路径。其他机器使用自己的 Playwright 安装，并设置 `PLAYWRIGHT_MODULE`；端口和隔离数据库准备方式见脚本头部。不要直接对自己的真实作品运行会采用候选的测试脚本。

## 故障排查

- **8000 被占用**：检查已有实例，或使用 `--port 8002`；不要启动多个 worker 共享单进程调度状态。
- **页面打不开/只有提示 JSON**：先构建 `frontend/dist`，确认工作目录为仓库根目录。
- **等待协作**：这是默认模式，复制任务并附图、回填结果后才继续，不是服务卡住。
- **HTTP 401/403**：检查你自己的密钥、权限与模型；ChatGPT 订阅不等于 API 额度。
- **参考图编辑不支持**：现有 HTTP 生图适配器明确拒绝该能力；用协作模式，或另行开发支持参考图的适配器。
- **返回 JSON 不合法**：完整复制 Schema 和任务，粘贴完整 JSON；不会自动伪造补全。
- **中文方块**：安装 CJK 字体并设置 `COMIC_FONT_PATH` 后重启。
- **skill 校验失败**：不要手动修改固定上游文件；检查 `.gitattributes` 是否保留原始字节，或恢复文件。原创规则可单独修改。
- **服务重启后任务失败/批次暂停**：进入章节继续任务；批次确认后继续，失败项可重试。

## 备份

停机后一起备份 `comic_agent.db`、`data/media/` 和 `data/chatgpt_jobs/`。同时保存 `.env` 到自己的安全位置，不上传 Git。示例成稿不是数据库备份，不能恢复作者电脑中的项目。


## Docker（可选）

仓库提供单服务 Dockerfile/Compose，不启动旧版 Redis/Chroma/MinIO 栈。安装 Docker 后，先从 `.env.example` 复制 `.env`，再执行 `docker compose up --build`。数据保存在挂载的 `data/`，默认仅将端口发布到主机 `127.0.0.1`。容器内 `127.0.0.1` 不是宿主机；连接主机模型服务时需自行配置适用地址。该配置已静态检查，当前发布环境未运行 Docker 构建，使用前请按自身平台验证。
