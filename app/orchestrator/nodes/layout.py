from app.agents.layout_artist import LayoutArtistAgent


async def final_layout_node(state):
    layout_artist = LayoutArtistAgent()

    final_comic = await layout_artist.compose_final(
        panels=state.get("panels", []),
        dialogues=state.get("dialogues", {}),
        effects=state.get("effects", {}),
    )

    return {
        "final_comic": final_comic,
        "phase": "completed",
    }
