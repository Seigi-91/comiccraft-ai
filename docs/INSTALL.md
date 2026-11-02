# 一键安装与首次体验

## Windows：下载、解压、双击

下载 [ComicCraft-AI-Windows-Installer.zip](https://github.com/Seigi-91/comiccraft-ai/releases/download/v2.3.0/ComicCraft-AI-Windows-Installer.zip)，先解压到本机文件夹，再双击 `Install-ComicCraft.cmd`。

安装器会：

1. 从本仓库固定的 `v2.3.0` 标签下载源码，不需要 Git。优先使用 Windows 系统 curl 流式下载，带连接与总时长上限；没有 curl 时使用有超时的 PowerShell 备用方式。
2. 将源码放入 `%LOCALAPPDATA%\ComicCraft-AI\source`。
3. 检查 Python 3.11+ 和 Node.js 20+；缺失时使用 Windows 自带的 winget 下载 Python 3.12 与 Node.js LTS。该步骤会接受对应安装器/源协议，可能出现系统权限提示。没有 winget 时会给出手动安装提示，不绕过系统安全设置。
4. 创建项目独立 `.venv`，安装 Python/前端依赖，首次构建网页。
5. 在 `127.0.0.1` 启动，默认端口 8000；占用时尝试后续 20 个端口，控制台显示实际地址。服务就绪后打开浏览器。
6. 首页点击「导入 / 打开可编辑示例」，即可进入《雨夜留灯》，不发起模型请求。

首次安装需要网络，速度取决于 GitHub、Python/npm 包源和机器性能，不承诺一分钟完成。网站本身不捆绑模型、账号或免费额度。

已有安装再次执行会启动原目录，**不会覆盖 `.env`、数据库或漫画**。这不是自动升级器：升级前备份 `.env`、`comic_agent.db` 和 `data/`，阅读新版本说明，再在新的目录验证。默认不删除任何旧安装文件。

可手动指定位置：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -InstallPrerequisites -InstallDirectory D:\ComicCraft
```

只下载源码、不安装依赖或启动：`-NoStart`。已有源码直接运行 `start.ps1`；开发验证可使用 `start.ps1 -Port 8032 -NoBrowser`。窗口需保持打开，`Ctrl+C` 停止网站。安装 ZIP 和源码 ZIP 不同：前者是小型启动器，首次运行仍需下载源码与依赖。

## macOS / Linux：一个启动脚本

安装 Python 3.11+、Node.js 20+ 与中文字体后，在源码根目录运行：

```bash
bash start.sh
```

脚本创建 `.venv`、保留已有 `.env`、安装依赖、构建网页并启动。本轮没有制作 macOS 签名 App 或 Linux 桌面安装包，也不会擅自通过 sudo 修改系统。缺少中文字体时，安装 Noto Sans CJK 并配置 `COMIC_FONT_PATH`。

## 环境诊断与模型配置

首页「检查本机环境」检查 Python、Node、写入权限、字体文件、构建和端口，不发送模型请求。自定义字体是否包含中文字形仍需用成稿检查。命令行也可运行：

```bash
python -m app.services.diagnostics
```

进入「创作团队与设置」分别配置文字/视觉和图片。保存不产生费用；「服务验证」需要再次勾选确认，才向当前服务发送一次可能付费的请求。没有有效 Key 或服务地址时不会伪造“已验证”。

## 验证边界

维护者使用自动化测试验证导入、回退、接口格式、知识接入、请求限制和任务租约；使用浏览器检查实际界面。PowerShell 安装/启动脚本执行语法检查；本机实际创建新的项目虚拟环境、安装依赖、构建并启动了网站，并提供干净源码下载验证。依赖全部缺失时的 winget 安装、系统权限弹窗和不同网络代理不能仅靠当前机器上的检查保证，需要用户真实安装反馈；容器和多系统支持以各自验证记录为准。
