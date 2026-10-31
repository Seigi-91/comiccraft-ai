def review_decision(state):
    if state.get("review_history") and state["review_history"][-1].get("passed"):
        return "final_layout"
    if state.get("human_intervene") or state.get("retry_count", 0) >= 3:
        return "human_intervention"
    return "generate_panels"


def phase_transition(state):
    return {
        "planning": "storyboarding",
        "storyboarding": "dialogue",
        "dialogue": "panel_generation",
        "panel_generation": "review",
        "review": "layout",
        "layout": "completed",
    }.get(state.get("phase"), "planning")
