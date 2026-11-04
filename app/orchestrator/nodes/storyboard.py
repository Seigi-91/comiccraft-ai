from app.agents.storyboard_artist import StoryboardArtistAgent
from app.services.comic_plan import effective_references


async def generate_storyboard_node(state):
    storyboarder = StoryboardArtistAgent()

    library = state.get("scene_reference_library", [])
    outline = dict(state.get("outline") or {})
    if state.get("novel_adaptation"):
        outline["novel_source"] = state["novel_adaptation"]
    if state.get("previous_novel_context"):
        outline["previous_novel_context"] = state["previous_novel_context"]
    outline["available_reference_names"] = [
        {"kind": kind, "name": name}
        for kind, name in sorted({(asset["kind"], asset["name"]) for asset in library})[:80]
    ]
    result = await storyboarder.generate_storyboard(
        outline=outline,
        style_ref_urls=state.get("style_ref_urls", []),
    )

    return {
        "storyboard": result,
        "visual_reference_bindings": effective_references(
            result, state.get("scene_reference_library", []),
            state.get("visual_reference_overrides", state.get("visual_reference_bindings", {})),
        ),
        "phase": "dialogue",
    }
