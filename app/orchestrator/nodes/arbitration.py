async def arbitrate_conflicts_node(state):
    # Dialogue count does not imply panel count; multiple bubbles may share a panel.
    indices = {p["index"] for p in state["storyboard"]["panels"]}
    for bubble in state["dialogues"]["bubbles"]:
        if bubble["panel_index"] not in indices:
            raise ValueError("台词与分镜索引冲突")
    return {
        "phase": "panel_generation",
        "conflicts_found": False,
        "human_intervene": False,
        "needs_human_intervention": False,
    }
