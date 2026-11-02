# 项目发布文案草稿（待维护者自行审阅发布）

以下不是已发布内容。先确认平台允许推广，注明作者身份；补充实际版本与已验证的模型服务，不夸大自动化能力。

## 中文短介绍

我开源了 ComicCraft AI，一个让漫画生成结果继续可编辑的本机创作工作室。

它把大纲、角色、分镜、台词与排版串起来：可以拖动气泡和尾尖避开人物，圈选失真的手部做局部修复，对比后采用，也可以回退章节版本。文字与图片能分别配置自己的 API，或使用 ChatGPT 人工回填。

我做了一个无需安装的气泡编辑体验，打开就能改台词、移动位置并导出 PNG：
https://seigi-91.github.io/comiccraft-ai/demo.html

源码和本机运行说明：https://github.com/Seigi-91/comiccraft-ai

目前最需要反馈的是：首次安装是否顺利、中文排版是否好用、你使用的模型服务能否接通。项目仍早期，角色一致性需要人工检查；完整后端目前不是公网多人服务。体验页不调用 AI，完整创作需要你自己的 ChatGPT 或有效的模型服务。

如果这个流程对你有帮助，欢迎 Star 或提具体问题。也欢迎指出缺陷。

## English introduction

I built ComicCraft AI, a local comic workspace where generated panels remain editable.

You can revise scripts, move speech bubbles and tail tips, mask a damaged area for repair, compare candidates and restore chapter versions. Text/vision and image providers are configured independently. Bring your own OpenAI-compatible services, or use a manual ChatGPT handoff.

Try a small no-install bubble editor: https://seigi-91.github.io/comiccraft-ai/demo.html
Source and setup: https://github.com/Seigi-91/comiccraft-ai

The browser demo uses pre-generated artwork and makes no AI calls. The full app runs locally and needs your own models or ChatGPT access. It is early software, not a hosted multi-tenant service, and character consistency still needs human review.

I'd especially appreciate installation feedback and reproducible provider compatibility reports. If the workflow is useful, a Star is welcome.

## 录屏分镜（约 30 秒）

1. 0–5 秒：展示《雨夜留灯》成稿，字幕“从初稿到可修改的成稿”。
2. 5–13 秒：拖气泡和尾尖、改一句台词，展示导出前后。
3. 13–22 秒：在完整本机应用中圈手、输入修复要求、比较候选并采用；明确所用服务和是否回填。不得用静态体验页冒充精修演示。
4. 22–27 秒：显示文字/图片独立 API 设置，录屏前清除真实密钥。
5. 27–30 秒：显示体验页与仓库地址，邀请反馈。

本轮未重新制作或上传上述新视频；旧演示仍可在 Release 下载。发布时不要将旧演示说成包含最新 API 面板。
