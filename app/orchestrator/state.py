from typing import Any, Dict, List, NotRequired, Optional, TypedDict


class ComicState(TypedDict, total=False):
    project_id: str
    user_id: str
    inspiration: Optional[str]
    style_ref_urls: Optional[List[str]]
    outline: Optional[Dict[str, Any]]
    characters: List[Dict[str, Any]]
    chapters: List[Dict[str, Any]]
    storyboard: Optional[Dict[str, Any]]
    dialogues: Optional[Dict[str, Any]]
    panels: List[Dict[str, Any]]
    current_chapter: Optional[str]
    phase: str
    review_history: List[Dict[str, Any]]
    retry_count: int
    human_intervene: bool
    task_id: Optional[str]
    conflicts_found: bool
    conflict_names: List[str]
    needs_human_intervention: bool
    human_intervention_reason: Optional[str]
    resolution_strategy: Optional[str]

    next_node: str
    events: List[Dict[str, Any]]
    final_comic: Dict[str, Any]

    bubble_placement_report: List[Dict[str, Any]]

    effects: Dict[str, List[Dict[str, Any]]]
