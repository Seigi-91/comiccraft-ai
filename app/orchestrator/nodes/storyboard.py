from app.agents.storyboard_artist import StoryboardArtistAgent


async def generate_storyboard_node(state):
    storyboarder = StoryboardArtistAgent()

    result = await storyboarder.generate_storyboard(
        outline=state.get("outline", {}),
        style_ref_urls=state.get("style_ref_urls", []),
    )

    return {
        "storyboard": result,
        "phase": "dialogue",
    }
