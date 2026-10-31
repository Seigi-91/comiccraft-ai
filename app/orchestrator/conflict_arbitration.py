from typing import Any, Dict, List, Optional, Tuple

from app.orchestrator.state import ComicState


class ConflictRule:
    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW = "low"

    def __init__(
        self,
        name: str,
        priority: str,
        condition,
        resolution,
        description: str = "",
    ):
        self.name = name
        self.priority = priority
        self.condition = condition
        self.resolution = resolution
        self.description = description

    async def check(self, state: ComicState) -> bool:
        return await self.condition(state)

    async def resolve(self, state: ComicState) -> ComicState:
        return await self.resolution(state)


class ConflictArbitrator:
    def __init__(self):
        self.rules = self._load_rules()
        self.pending_conflicts: List[Dict[str, Any]] = []

    def _load_rules(self) -> List[ConflictRule]:
        return [
            ConflictRule(
                name="dialogue_priority_over_layout",
                priority=ConflictRule.PRIORITY_HIGH,
                condition=self._check_dialogue_layout_conflict,
                resolution=self._resolve_dialogue_priority,
                description="台词内容优先于画面留白，确保对话气泡有足够空间",
            ),
            ConflictRule(
                name="character_consistency",
                priority=ConflictRule.PRIORITY_HIGH,
                condition=self._check_character_consistency_conflict,
                resolution=self._resolve_character_consistency,
                description="角色外貌必须保持一致，使用参考图和嵌入向量",
            ),
            ConflictRule(
                name="story_logic",
                priority=ConflictRule.PRIORITY_MEDIUM,
                condition=self._check_story_logic_conflict,
                resolution=self._resolve_story_logic,
                description="剧情逻辑冲突时，以大纲为准",
            ),
            ConflictRule(
                name="style_consistency",
                priority=ConflictRule.PRIORITY_MEDIUM,
                condition=self._check_style_conflict,
                resolution=self._resolve_style_consistency,
                description="画风必须保持一致",
            ),
            ConflictRule(
                name="panel_flow",
                priority=ConflictRule.PRIORITY_LOW,
                condition=self._check_panel_flow_conflict,
                resolution=self._resolve_panel_flow,
                description="分镜流程度优先",
            ),
        ]

    async def _check_dialogue_layout_conflict(self, state: ComicState) -> bool:
        dialogues = state.get("dialogues", {})
        storyboard = state.get("storyboard", {})

        if not dialogues or not storyboard:
            return False

        bubbles = dialogues.get("bubbles", [])
        panels = storyboard.get("panels", [])

        if len(bubbles) > len(panels):
            return True

        for bubble in bubbles:
            panel_index = bubble.get("panel_index", 0)
            if panel_index >= len(panels):
                return True

        return False

    async def _resolve_dialogue_priority(self, state: ComicState) -> ComicState:
        dialogues = state.get("dialogues", {})
        storyboard = state.get("storyboard", {})

        bubbles = dialogues.get("bubbles", [])
        panels = storyboard.get("panels", [])

        while len(panels) < len(bubbles):
            panels.append(
                {
                    "index": len(panels),
                    "shot_type": "medium",
                    "position": "center",
                    "action": "dialogue panel",
                    "composition": {"layout": "single"},
                }
            )

        for i, bubble in enumerate(bubbles):
            if i < len(panels):
                panels[i]["has_dialogue"] = True
                panels[i]["dialogue_count"] = panels[i].get("dialogue_count", 0) + 1

        state["storyboard"] = {"panels": panels}
        return state

    async def _check_character_consistency_conflict(self, state: ComicState) -> bool:
        outline = state.get("outline", {})
        storyboard = state.get("storyboard", {})

        outline_chars = {c.get("name") for c in outline.get("characters", [])}
        storyboard_chars = set()

        for panel in storyboard.get("panels", []):
            action = panel.get("action", "")
            for char in outline_chars:
                if char and char.lower() in action.lower():
                    storyboard_chars.add(char)

        return len(outline_chars - storyboard_chars) > 0

    async def _resolve_character_consistency(self, state: ComicState) -> ComicState:
        outline = state.get("outline", {})
        storyboard = state.get("storyboard", {})

        outline_chars = {c.get("name"): c for c in outline.get("characters", [])}
        panels = storyboard.get("panels", [])

        for panel in panels:
            action = panel.get("action", "")
            for char_name, char_info in outline_chars.items():
                if char_name and char_name.lower() in action.lower():
                    panel["character_info"] = char_info

        state["storyboard"] = {"panels": panels}
        return state

    async def _check_story_logic_conflict(self, state: ComicState) -> bool:
        outline = state.get("outline", {})
        dialogues = state.get("dialogues", {})

        if not outline or not dialogues:
            return False

        outline_events = set()
        for scene in outline.get("outline", []):
            if isinstance(scene, dict):
                outline_events.add(scene.get("summary", ""))

        bubble_texts = []
        for bubble in dialogues.get("bubbles", []):
            bubble_texts.append(bubble.get("text", ""))

        combined_text = " ".join(bubble_texts).lower()
        for event in outline_events:
            if event and event.lower() not in combined_text:
                return True

        return False

    async def _resolve_story_logic(self, state: ComicState) -> ComicState:
        outline = state.get("outline", {})
        dialogues = state.get("dialogues", {})

        outline_events = []
        for scene in outline.get("outline", []):
            if isinstance(scene, dict):
                outline_events.append(scene.get("summary", ""))

        bubbles = dialogues.get("bubbles", [])

        if bubbles and outline_events:
            bubbles[-1]["text"] = f"{bubbles[-1].get('text', '')} {outline_events[-1]}"

        state["dialogues"] = {"bubbles": bubbles}
        return state

    async def _check_style_conflict(self, state: ComicState) -> bool:
        style_refs = state.get("style_ref_urls", [])
        storyboard = state.get("storyboard", {})

        if not style_refs:
            return False

        for panel in storyboard.get("panels", []):
            if not panel.get("style_guidance"):
                return True

        return False

    async def _resolve_style_consistency(self, state: ComicState) -> ComicState:
        style_refs = state.get("style_ref_urls", [])
        storyboard = state.get("storyboard", {})

        panels = storyboard.get("panels", [])
        for panel in panels:
            if not panel.get("style_guidance"):
                panel["style_guidance"] = style_refs[:2]

        state["storyboard"] = {"panels": panels}
        return state

    async def _check_panel_flow_conflict(self, state: ComicState) -> bool:
        storyboard = state.get("storyboard", {})
        panels = storyboard.get("panels", [])

        shot_types = []
        for panel in panels:
            shot_types.append(panel.get("shot_type", ""))

        if len(shot_types) >= 3:
            for i in range(len(shot_types) - 2):
                if shot_types[i] == shot_types[i + 1] == shot_types[i + 2]:
                    return True

        return False

    async def _resolve_panel_flow(self, state: ComicState) -> ComicState:
        storyboard = state.get("storyboard", {})
        panels = storyboard.get("panels", [])

        shot_types = ["close-up", "medium", "wide", "medium"]
        for i, panel in enumerate(panels):
            panel["shot_type"] = shot_types[i % len(shot_types)]

        state["storyboard"] = {"panels": panels}
        return state

    async def detect_and_resolve(self, state: ComicState) -> Tuple[ComicState, bool, List[str]]:
        conflicts_found = []
        resolved = False
        state_copy = state.copy()

        for rule in sorted(
            self.rules,
            key=lambda r: {
                ConflictRule.PRIORITY_HIGH: 0,
                ConflictRule.PRIORITY_MEDIUM: 1,
                ConflictRule.PRIORITY_LOW: 2,
            }.get(r.priority, 2),
        ):
            if await rule.check(state_copy):
                conflicts_found.append(rule.name)
                state_copy = await rule.resolve(state_copy)
                resolved = True

        return state_copy, resolved, conflicts_found

    async def generate_two_versions(
        self,
        state: ComicState,
        conflict_type: str,
    ) -> Tuple[ComicState, ComicState, str]:
        version_a = state.copy()
        version_b = state.copy()

        if conflict_type == "dialogue_layout":
            version_a["resolution_strategy"] = "dialogue_priority"
            version_b["resolution_strategy"] = "layout_priority"

            for panel in version_a.get("storyboard", {}).get("panels", []):
                panel["has_dialogue"] = True

            for panel in version_b.get("storyboard", {}).get("panels", []):
                panel["layout_only"] = True

        elif conflict_type == "character_design":
            version_a["resolution_strategy"] = "reference_character"
            version_b["resolution_strategy"] = "new_interpretation"

        elif conflict_type == "story_direction":
            version_a["resolution_strategy"] = "outline_following"
            version_b["resolution_strategy"] = "creative_divergence"

        else:
            version_a["resolution_strategy"] = "option_a"
            version_b["resolution_strategy"] = "option_b"

        explanation = (
            f"检测到{conflict_type}冲突，生成两个版本供您选择：\n"
            f"版本A: {version_a['resolution_strategy']}\n"
            f"版本B: {version_b['resolution_strategy']}"
        )

        return version_a, version_b, explanation

    async def needs_human_intervention(self, state: ComicState) -> Tuple[bool, Optional[str]]:
        _, _, conflicts = await self.detect_and_resolve(state)

        if len(conflicts) >= 3:
            return True, f"检测到{len(conflicts)}个冲突需要人工裁决"

        unresolved_conflicts = []
        for conflict in conflicts:
            if conflict == "character_consistency":
                outline = state.get("outline", {})
                storyboard = state.get("storyboard", {})
                outline_chars = {c.get("name") for c in outline.get("characters", [])}
                storyboard_chars = set()
                for panel in storyboard.get("panels", []):
                    action = panel.get("action", "")
                    for char in outline_chars:
                        if char and char.lower() in action.lower():
                            storyboard_chars.add(char)
                if len(outline_chars - storyboard_chars) == 0:
                    continue
            unresolved_conflicts.append(conflict)

        if len(unresolved_conflicts) >= 2:
            return True, f"检测到{len(unresolved_conflicts)}个冲突需要人工裁决"

        return False, None
