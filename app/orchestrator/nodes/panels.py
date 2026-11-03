from app.agents.panel_designer import PanelDesignerAgent


async def generate_panels_node(state, session=None):
    feedback = (state.get("review_history") or [{}])[-1]
    dialogue_positions = {}
    for bubble in (state.get('dialogues') or {}).get('bubbles', []):
        dialogue_positions.setdefault(bubble['panel_index'], []).append({
            'position': bubble['position'], 'size': bubble.get('size'),
            'speaker': bubble.get('character'), 'instruction': '为后续排字留白，画面内不画文字或气泡',
        })
    panels = await PanelDesignerAgent().generate_panels(
        storyboard=state["storyboard"],
        style_ref_urls=state.get("style_ref_urls", []),
        characters=state.get("characters", []),
        previous=state.get("panels", []),
        feedback=feedback,
        dialogue_positions=dialogue_positions,
        visual_reference_bindings=state.get("visual_reference_bindings", {}),
    )
    return {"panels": panels, "phase": "review", "retry_count": state.get("retry_count", 0) + 1}
