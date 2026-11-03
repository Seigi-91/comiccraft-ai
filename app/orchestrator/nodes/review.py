from app.agents.style_reviewer import StyleReviewerAgent


async def review_panels_node(state):
    prior = {}
    for batch in state.get('review_history') or []:
        for review in batch.get('panel_reviews', []):
            if review.get('evidence_signature'):
                prior[review['panel_index']] = review
    result = await StyleReviewerAgent().review_panels(
        state["panels"], state.get("style_ref_urls", []), state.get("characters", []),
        previous_reviews=list(prior.values())
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
    scope = state.get("revision_targets")
    outside_scope = bool(scope and any(not review["passed"] and index not in scope for index, review in reviews.items()))
    return {
        "review_history": [*state.get("review_history", []), result],
        "panels": panels,
        "human_intervene": outside_scope or (not result["passed"] and state.get("retry_count", 0) >= 3),
    }
