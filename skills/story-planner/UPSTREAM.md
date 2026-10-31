# SkillsMP 专业技能适配

上游技能：plot-structure
SkillsMP：https://skillsmp.com/creators/danjdewhurst/story-skills/skills-plot-structure
固定源版本：e44c97ce8eee4db3bbc82db05c4f7982e470e2bd

## 当前 agent 的适用范围

把小说结构方法用于六至十二格短篇：只保留建立、触发、选择、结果、回扣。当前系统以 JSON 传递，不创建小说 CLI 工程。

用户要求与项目任务协议优先。以下为已审阅的方法章节；未列出的上游安装、CLI、向导和服务配置步骤不属于该 agent 的职责。

来源文件 SKILL.md：
## Overview

Plan and manage story arcs, plot points, setups and payoffs, and the narrative timeline. Each arc is a markdown file in `plot/arcs/`, and `plot/timeline.md` holds the planned events and backstory in story order. The plot index lists all arcs, their status, and theme coverage.

来源文件 SKILL.md：
## Pacing, Outcomes, and Hooks

Two optional fields make pacing checkable:

- Scene `outcome`: `yes`, `no`, `yes-but`, or `no-and` — whether the POV character got what they wanted in the scene. `yes-but` and `no-and` are the complicating outcomes that drive a plot forward (see the `scene-craft` skill).
- Chapter `hook`: how the chapter ends — `cliffhanger`, `question`, `revelation`, `reversal`, `decision`, `emotional`, or `resolution`.

Plan both in the outline, then run `story pacing .` for a per-chapter dashboard of words, scene and sequel counts, scene outcomes, and hooks. It warns about three or more consecutive `yes` outcomes (no pressure), four or more scene units with no sequel (no breath), chapter length outliers (over twice or under half the median once three chapters have prose), three or more consecutive chapters ending on `resolution`, and drafted chapters with no `hook`. Treat the warnings as prompts to reread, not rules: a quiet `resolution` chapter after the climax is right.