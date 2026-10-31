from app.agents.story_planner import StoryPlannerAgent


async def generate_outline_node(state):
    result = await StoryPlannerAgent().generate_outline(
        inspiration=state.get("inspiration", ""),
        style_ref_urls=state.get("style_ref_urls", []),
        characters=state.get("characters", []),
    )
    existing = {c["name"]: c for c in state.get("characters", [])}
    characters = [{**c, **existing.get(c["name"], {})} for c in result["characters"]]
    result["characters"] = characters
    return {"outline": result, "characters": characters, "phase": "storyboarding"}
