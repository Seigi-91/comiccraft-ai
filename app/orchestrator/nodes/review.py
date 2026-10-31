from app.agents.style_reviewer import StyleReviewerAgent


async def review_panels_node(state):
    result = await StyleReviewerAgent().review_panels(
        state["panels"], state.get("style_ref_urls", []), state.get("characters", [])
    )
    reviews = {r["panel_index"]: r for r in result["panel_reviews"]}
    panels = [
        {
            **p,
            "status": "passed" if reviews[p["index"]]["passed"] else "failed",
            "review_result": reviews[p["index"]],
        }
        for p in state["panels"]
    ]
    return {
        "review_history": [*state.get("review_history", []), result],
        "panels": panels,
        "human_intervene": not result["passed"] and state.get("retry_count", 0) >= 3,
    }
