from langgraph.graph import END, START, StateGraph
from app.orchestrator.nodes import (
    arbitrate_conflicts_node,
    final_layout_node,
    generate_dialogue_node,
    generate_outline_node,
    generate_panels_node,
    generate_storyboard_node,
    human_intervention_node,
    review_panels_node,
)
from app.orchestrator.routing import review_decision
from app.orchestrator.state import ComicState
from app.tools.desktop_bridge import stage_context


def create_comic_graph(session=None):
    from app.agents.bubble_placement import place_bubbles
    workflow = StateGraph(ComicState)
    nodes = {
        "auto_place_bubbles": place_bubbles,
        "generate_outline": generate_outline_node,
        "generate_storyboard": generate_storyboard_node,
        "generate_dialogue": generate_dialogue_node,
        "arbitrate_conflicts": arbitrate_conflicts_node,
        "generate_panels": generate_panels_node,
        "review_panels": review_panels_node,
        "final_layout": final_layout_node,
        "human_intervention": human_intervention_node,
    }
    sequence = {
        "auto_place_bubbles": "final_layout",
        "generate_outline": "generate_storyboard",
        "generate_storyboard": "generate_dialogue",
        "generate_dialogue": "arbitrate_conflicts",
        "arbitrate_conflicts": "generate_panels",
        "generate_panels": "review_panels",
        "final_layout": "done",
        "human_intervention": "done",
    }

    def wrap(name, operation):
        async def run(state):
            token = stage_context.set(name)
            try:
                update = await operation(state)
                merged = {**state, **update}
                update["next_node"] = (
                    review_decision(merged) if name == "review_panels" else sequence[name]
                )
                update["events"] = [*state.get("events", []), {"node": name, "status": "completed"}]
                return update
            finally:
                stage_context.reset(token)

        return run

    for name, operation in nodes.items():
        workflow.add_node(name, wrap(name, operation))
    workflow.add_conditional_edges(
        START,
        lambda state: state.get("next_node", "generate_outline"),
        {name: name for name in nodes},
    )
    for name in nodes:
        workflow.add_conditional_edges(
            name, lambda state: state["next_node"], {**{n: n for n in nodes}, "done": END}
        )
    return workflow.compile()
