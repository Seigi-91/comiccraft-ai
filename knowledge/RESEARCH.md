# 知识来源调研与排除台账

核对日期：2026-11-02。方法：逐项浏览原始教育/实践资料的指定文字段落，为具体原则建立定位，再编写项目应用、正反例与例外。没有下载或再分发原文、插图、字体或电影片段。没有声称读完教材或接受外部专家评审。

## 来源清单

| 来源 | 类型/发布者 | 实际核对范围 | 状态 |
|---|---|---|---|
| [Yale Film Analysis — Editing](https://filmanalysis.yale.edu/editing/) | primary_educational / Yale University | 核对连续性、视线匹配、动作匹配、交叉剪辑的文字说明；未观看或逐帧分析页面影片。 | `verified_text` |
| [Yale Film Analysis — Cinematography](https://filmanalysis.yale.edu/cinematography/) | primary_educational / Yale University | 核对色彩、反差、焦点及取景/机位的文字说明；未观看或逐帧分析页面影片。 | `verified_text` |
| [Adobe — How to get started on storyboarding](https://www.adobe.com/creativecloud/video/discover/storyboarding.html) | primary_educational / Adobe | 核对何为分镜、分镜如何传达故事/情绪的文字段落；未把访谈当作全部导演的共识。 | `verified_text` |
| [Pixar in a Box — The art of storytelling](https://www.khanacademy.org/computing/pixar/storytelling) | primary_educational / Pixar / Khan Academy | 只核对页面中明确记录的章节，不代表完整课程或书籍已研读。 | `restricted` |
| [Nate Piekos / Blambot — Better Letterer](https://blambot.com/pages/lettering-tips) | primary_educational / Nate Piekos / Blambot | 只核对页面中明确记录的章节，不代表完整课程或书籍已研读。 | `image_index_only` |
| [W3C — Understanding Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | primary_educational / W3C WAI | 核对SC1.4.3及普通/大字条款；适用边界见原文，不将其推广成整个漫画的认证。 | `verified_text` |
| [OpenLearn — 4.2 What is plot?](https://www.open.edu/openlearn/mod/oucontent/view.php?id=20431&section=2) | primary_educational / The Open University | 4.2 What is plot?；因果与时间序列段落 | `verified_text` |
| [OpenLearn — 5.4 Summary of Week 5](https://www.open.edu/openlearn/mod/oucontent/view.php?id=101090&section=_unit5.4) | primary_educational / The Open University | 5.4；人物矛盾与冲突概述 | `verified_text` |
| [Novakovich excerpt — Portraying a character](https://www.open.edu/openlearn/mod/oucontent/view.php?id=20441&section=1.3.1) | primary_educational / The Open University；课程所引 Josip Novakovich 节选 | Summary / Repeated action or habit / Appearance / Scene / Combining techniques；只核对课程节选，不宣称读完原书 | `verified_text` |
| [OpenLearn — 7.3 Questions to ask](https://www.open.edu/openlearn/mod/oucontent/view.php?id=20448&section=3) | primary_educational / The Open University | 7.3；读者投入、人物吸引力与困惑等反馈问题 | `verified_text` |
| [Comic Script Basics](https://blambot.com/pages/comic-script-basics) | primary_practitioner / Nate Piekos / Blambot | 编号5–10及总结；参考链接、排字条目与说话状态 | `verified_text` |
| [Comic Book Grammar & Tradition](https://blambot.com/pages/comic-book-grammar-tradition) | primary_practitioner / Nate Piekos / Blambot | Balloon Tails / Thought Balloons / Tangents；文字段落，不复制插图 | `verified_text` |
| [Lettering Conventions](https://www.tocomix.com/articles/reference/lettering) | primary_practitioner / TO Comix Press | Balloons；安全区、留边与不遮挡人物 | `verified_text` |
| [Perspective Rulers](https://help.clip-studio.com/en-us/manual_en/510_ruler/Perspective_Rulers.htm) | primary_practitioner / CELSYS / Clip Studio Paint | One-point / Two-point / Three-point Perspective；基础透视定义 | `verified_text` |
| [3D Hand Models](https://help.clip-studio.com/en-us/manual_en/660_3d/3D_Hand_Models.htm) | primary_practitioner / CELSYS / Clip Studio Paint | 开头与 Posing the hands；只支持手姿参考工具的存在，不支持AI解剖正确性保证 | `verified_text` |
| [Comic Sol — Visual QA](https://github.com/wenn-id/comicsol/blob/35fcb0237e8b2857decfb9bc3593fc8e049f9608/references/visual-qa.md) | upstream_engineering / wenn-id / Comic Sol | L3–29：按分项记录证据；L50–69：选择性修复与预算。代码/文档阅读，未运行项目 | `verified_text` |

部分教育页面通过公开检索阅读器可读，而直接HTTP请求可能返回403；不据此声称所有链接实时直连可访问。来源核对没有形成机构认证。

`verified_text` 只表示已核对表中指定文字，不表示资料全部阅读或结论经独立验证。`upstream_engineering` 是同行项目的工程做法，不升级为艺术理论或科学效果证据。

## 排除与降级

- Pixar课程入口保留为延伸阅读，正文访问受限，不再支持任何卡片的具体主张。
- Blambot图片索引只核对到导航；改用能读到文字的脚本与排字文章支持具体原则。
- Purdue拟用链接无法访问/404，未作为支持证据。
- NMOER人物对白章节返回403，未根据搜索摘要引用为已研读正文。
- OpenLearn人物节选只核对公开课程中的指定片段，不声称读完Novakovich原书；保留课内作者归属。

## 证据分级与结论边界

1. 大学课程、标准机构正文：支持指定范围的教学概念或条款；不是漫画质量的随机对照试验。
2. 原作者/出版方/工具厂商实践说明：支持其明确阐述的惯例或功能；不等于所有流派的普适规范。
3. 同类项目固定提交的代码/文档：支持“该项目有这个工程做法”，不证明其运行或质量效果。
4. 漫画原始研究。只支持所核对的理论区分、语料观察或特定实验条件中的结果。迁移到 AI 生成、手机条漫和具体版式是项目应用。
5. 项目自定工作规则：明确标记，不借用一个机构主页作权威背书。

## 实施审阅矩阵

| 角色 | 具体已核对原则 | 项目自定部分 |
|---|---|---|
| 剧情 | 因果与时间顺序、人物冲突与场景呈现 | 六格模板、事实表、字段约束 |
| 分镜 | 取景与叙事注意、视点与轴线、动作匹配、交叉剪辑、回忆切换 | 六类子镜头选择、跨节拍独立分格、手机条漫读序和留白 |
| 台词 | 场景中的声音、总结的作用、脚本排字标记 | 60字限制、邻格指代与沉默检查 |
| 画面 | 焦点、透视定义、光色语境、手姿参考工具 | 身份协议、接触检查、连续性约束 |
| 审核 | 读者反馈问题、同行分项证据做法 | 严重度、实验量表、人工覆盖率 |
| 排版 | 出版方安全区/留边、排字惯例、对比度条款 | 保护框算法、类型简化与导出检查 |

详细逐卡映射见 [CARD_CATALOG](CARD_CATALOG.md)，机器可检验数据见 [cards.json](cards.json)。

## 尚未满足的部分

当前完成资料可核查、应用可审阅与评测机制建设。没有真实ChatGPT成对输出与独立评审时，不能将“工程测试通过”改写成“知识提高漫画质量”。需要多人外部评审、更大独立案例、图像级实验和不同创作流派复核，才可扩展效果结论。

## 2026-11-03 增补核查

[Neil Cohn, The architecture of visual narrative comprehension (2014)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4076615/) 的 Key Concepts 2–3 及 *Attentional framing structure* 支持「主格内可嵌入从属画格，以取景聚焦局部线索」，已纳入 `board-intent-e3`。文章并未规定条漫必须使用某种比例、边距或气泡坐标。项目把上述原则应用到不等分版式、嵌入特写和手机宽度检查。跨章状态、参考图优先级和依赖复审是项目应用规则，质量变化仍须用配对案例检验。

## 2026-11-04 子镜头增补核查

| 核对来源 | 可支持的区分 | 证据编号 |
|---|---|---|
| [Foulsham 与 Cohn, Zooming in on visual narrative comprehension (2021)](https://link.springer.com/article/10.3758/s13421-020-01101-w) | 实验 1、2 的理解评分与讨论支持聚焦相关信息。与关注度较低的裁切相比，注视位置裁切更容易理解，完整场景的背景仍提供上下文。 | `board-intent-e4` |
| [Cohn、Hacımusaoğlu 与 Klomberg, The framing of subjectivity (2023 卷期)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10259188/) | 引言用并置和画内线索说明如何辨认严格主观视点，讨论区分了过肩观察等焦点化方法。 | `board-axis-e2` |
| [Klomberg 等, Processing Incongruity for Mental Events in Comics (2025 卷期)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11716651/) | 摘要与总讨论显示，读者能理解主叙事和辅助情境间的切换，切换需要额外更新。在考察角色指代的实验中，画面形态呼应可帮助理解或处理。 | `board-time-e2` |

`reaction` 借用漫画叙事功能与局部聚焦的区分。`action_progression` 和 `parallel` 参考 Yale 的电影剪辑说明，再转成静态画格决策。六类项目字段、构图比例、短回忆标记及拆格阈值是项目规则。相关研究没有评测 ComicCraft 生成的漫画。
