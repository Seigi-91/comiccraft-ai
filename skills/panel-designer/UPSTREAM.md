# SkillsMP 专业技能适配

上游技能：imagegen
SkillsMP：https://skillsmp.com/creators/openai/skills/skills-system-imagegen
固定源版本：49f948faa9258a0c61caceaf225e179651397431

## 当前 agent 的适用范围

通过当前应用的生图适配器交接提示词及真实参考图片，不能声称应用后台拥有 Codex 内置 image_gen 工具。每格复用角色表，并附前一格作为动作与场景连续性参考。

用户要求与项目任务协议优先。以下为已审阅的方法章节；未列出的上游安装、CLI、向导和服务配置步骤不属于该 agent 的职责。

来源文件 references/prompting.md：
## Structure
- Use a consistent order: scene/backdrop -> subject -> key details -> constraints -> output intent.
- Include intended use (ad, UI mock, infographic) to set the level of polish.
- For complex requests, use short labeled lines instead of one long paragraph.

来源文件 references/prompting.md：
## Constraints and invariants
- State what must not change (`keep background unchanged`).
- For edits, say `change only X; keep Y unchanged` and repeat invariants on every iteration to reduce drift.

来源文件 references/prompting.md：
## Input images and references
- Do not assume that every provided image is an edit target.
- Label each image by index and role (`Image 1: edit target`, `Image 2: style reference`).
- If the user provides images for style, composition, or mood guidance and does not ask to modify them, treat the request as generation with references.
- If the user asks to preserve an existing image while changing specific parts, treat the request as an edit.
- For compositing, describe how the images interact (`place the subject from Image 2 into Image 1`).