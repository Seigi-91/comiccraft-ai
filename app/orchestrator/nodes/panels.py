from app.agents.panel_designer import PanelDesignerAgent


async def generate_panels_node(state, session=None):
    feedback = (state.get("review_history") or [{}])[-1]
    panels = await PanelDesignerAgent().generate_panels(
        storyboard=state["storyboard"],
        style_ref_urls=state.get("style_ref_urls", []),
        characters=state.get("characters", []),
        previous=state.get("panels", []),
        feedback=feedback,
    )
    return {"panels": panels, "phase": "review", "retry_count": state.get("retry_count", 0) + 1}
