# SkillsMP 专业技能适配

上游技能：video-storyboard
SkillsMP：https://skillsmp.com/creators/agentara/skills/skills-aigc-video-storyboard
固定源版本：950e1bfb11e1df67b46df19804ed85ada9012c33

## 当前 agent 的适用范围

采用镜头变化与人物、服装、道具、地理连续性规范。当前输出漫画分镜 JSON，不输出视频秒数、网格时间标签或视频文件。

用户要求与项目任务协议优先。以下为已审阅的方法章节；未列出的上游安装、CLI、向导和服务配置步骤不属于该 agent 的职责。

来源文件 SKILL.md：
Panel variety is critical:

- Avoid creating two panels that are identical, near-identical, or visually redundant.
- Each non-empty panel should advance the action, reveal new information, or change the viewer's perspective.
- Vary shot size, camera angle, character pose, gesture, prop interaction, foreground/background relationship, or motion direction while preserving continuity.
- Do not use repeated close-ups or repeated wide shots unless the repetition is intentional and clearly serves the scene rhythm.

Critical continuity requirements:

- Keep the same character identity across all panels.
- Keep face, age, hairstyle, body type, and skin tone consistent.
- Keep wardrobe consistent unless the scene explicitly includes a costume change.
- Keep key props consistent, including product shape, color, bottle/can design, bag, camera, vehicle, or luggage.
- Keep location geography consistent: doors, windows, roads, vending machines, classrooms, landmarks, field direction, and light direction should not jump randomly.
- Keep the time of day and weather consistent unless the scene explicitly transitions.