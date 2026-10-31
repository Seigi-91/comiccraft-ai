# SkillsMP 专业技能适配

上游技能：baoyu-comic
SkillsMP：https://skillsmp.com/creators/jimliu/baoyu-skills/skills-baoyu-comic
固定源版本：1567581c26ec29f4216c6e6835415bf30343b0e3

## 当前 agent 的适用范围

使用条漫上至下阅读、镜头大小变化和留白节奏。排版仍由本机确定性渲染器完成，中文文字按台词百分比坐标绘入画面内漫画气泡，不依赖生图模型绘字，不触发上游完整知识漫画向导。

用户要求与项目任务协议优先。以下为已审阅的方法章节；未列出的上游安装、CLI、向导和服务配置步骤不属于该 agent 的职责。

来源文件 references/layouts/webtoon.md：
# webtoon

Vertical scrolling comic (竖版条漫)

## Panel Structure

- **Panels per page**: 3-5 vertically stacked
- **Structure**: Single column, vertical flow optimized for scrolling
- **Gutters**: Generous vertical spacing (20-40px), panels often bleed horizontally

## Grid Configuration

- Single column, vertical stack
- Panel sizes: Full width, variable height (1:1 to 1:2 aspect)
- Reading flow: Top→bottom continuous scroll

## Special Features

- Panels can extend beyond frame for dramatic effect
- Generous whitespace between beats
- Character close-ups alternate with wide explanation panels
- "Float" effect - elements can exist between panels

## Best For

Ohmsha-style tutorials, mobile reading, step-by-step guides

## Best Style Pairings

ohmsha, vibrant