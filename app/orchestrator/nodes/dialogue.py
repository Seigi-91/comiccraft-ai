from app.agents.dialogue_master import DialogueMasterAgent


async def generate_dialogue_node(state):
    dialogue_master = DialogueMasterAgent()

    result = await dialogue_master.generate_dialogues(
        outline={**state.get("outline", {}), **({"novel_source": state["novel_adaptation"]} if state.get("novel_adaptation") else {})},
        storyboard=state.get("storyboard", {}),
    )

    return {
        "dialogues": result,
        "phase": "panel_generation",
    }
