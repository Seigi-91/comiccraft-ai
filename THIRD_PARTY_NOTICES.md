# 第三方来源与许可

根目录 MIT 仅覆盖本项目原创部分，不覆盖下列第三方资源。

| 内容 | 来源 | 许可/位置 |
|---|---|---|
| plot-structure | danjdewhurst/story-skills，固定提交见清单 | MIT；skills/vendor/plot-structure/UPSTREAM-LICENSE.txt |
| video-storyboard | agentara/skills，固定提交见清单 | MIT；skills/vendor/video-storyboard/UPSTREAM-LICENSE.txt |
| imagegen 方法 | openai/skills | Apache-2.0；skills/vendor/imagegen/LICENSE.txt |
| baoyu-comic | JimLiu/baoyu-skills | MIT；skills/vendor/baoyu-comic/UPSTREAM-LICENSE.txt |
| 视频中文字形 | Noto Sans CJK SC | SIL OFL；videos/ComicCraft-AI-demo-editable/assets/fonts/OFL.txt |
| Dream Culture | Kevin MacLeod / incompetech.com | CC BY 4.0；视频工程 MUSIC-CREDITS.txt 含来源与修改说明 |
| GSAP | GreenSock / GSAP | 保留 assets/lib/gsap.min.js 文件头及其许可链接，不归本项目 MIT |
| HyperFrames 光标组件 | HyperFrames registry | Apache-2.0；视频工程 HYPERFRAMES-LICENSE.txt，保留原始组件及来源说明 |

公开版没有分发此前私有开发中使用、但未核实再分发许可的 dialogue 和 visual-reviewer 包及其摘录；对应能力由本项目重新编写的原创规则提供，见 skills/local/。

AI 漫画样例描述虚构人物。样例不构成对第三方商标、肖像或素材权利的额外授权，也不承诺 AI 输出在所有地区具有独占版权。请自行检查再利用场景涉及的第三方权利。


## 专业知识卡的参考链接

`knowledge/cards.json` 的应用笔记、案例与检索实现为本项目原创，按 MIT 提供；引用不改变外部资料原有权利。来源包括 Yale Film Analysis、Adobe、Open University/OpenLearn、Blambot、TO Comix Press、CELSYS、W3C，以及固定提交的工程先例。没有再分发其完整教材、文学摘录、插图、影片或字体。受限 Pixar 页面与 Blambot 图片索引仅作为补充链接，不支撑知识卡论断。部分公开正文可通过网页阅读器读取，但直接请求可能受限；访问情况不等于永久可用性。

同类项目仅用于代码/文档结构调研，未复制其代码或素材，未宣称已运行其完整系统；固定提交和采纳边界见 [调研记录](docs/UPSTREAM_RESEARCH_2026-11-02.md)。逐来源访问、章节定位和适用边界见 [知识资料台账](knowledge/RESEARCH.md)。链接不代表任何机构参与、授权或认可本项目。


## 可选官方Codex连接器

安装助手按用户操作从官方npm包`@openai/codex@0.166.0`安装CLI，沿用其Apache-2.0许可与服务条款，不改变为本项目MIT。仓库及安装启动器不分发用户登录令牌或会员账户。连接器与官方产品之间的能力和实测边界见 [说明](docs/CODEX_CONNECTION.md)。

## 《我们得谈谈五十五号》漫画演示

[We Need To Talk About Fifty-Five](https://scp-wiki.wikidot.com/we-need-to-talk-about-fifty-five) 由 qntm 创作，发表于 SCP Wiki。演示对开篇作中文节编，重新分镜、绘图和排字。`docs/assets/web-novel-chapter.png`、`docs/assets/web-novel-edit-panel.png` 和 `docs/assets/web-novel-preview.jpg` 按 [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) 提供。项目代码沿用 MIT。
