import asyncio
import hashlib
import json

from app.agents.panel_designer import PanelDesignerAgent
from app.agents.skills import ROLES, catalog, instructions, sources
from app.agents.style_reviewer import StyleReviewerAgent
from app.core.paths import ROOT


def test_each_agent_loads_pinned_skillsmp_source():
    entries = sources()
    assert len(entries) == len(ROLES) == 6
    assert {entry["role"] for entry in entries} == set(ROLES)
    for entry in entries:
        original = ROOT / entry["installed_path"]
        runtime = ROOT / entry["runtime_path"]
        assert original.is_file() and runtime.is_file()
        assert hashlib.sha256(original.read_bytes()).hexdigest() == entry["sha256"]
        assert hashlib.sha256(runtime.read_bytes()).hexdigest() == entry["runtime_sha256"]
        if entry.get("source_kind") == "project-authored":
            assert entry["license"] == "MIT"
        else:
            assert entry["skillsmp_url"].startswith("https://skillsmp.com/")
            assert len(entry["commit"]) == 40
        assert runtime.read_text(encoding="utf-8") in instructions(entry["role"])
        for section in entry["loaded_sections"]:
            path = original.parent / section["path"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == section["sha256"]
    assert all(agent["upstream_skills"] for agent in catalog())


def test_generation_passes_identity_opening_and_previous_frame(monkeypatch):
    agent = PanelDesignerAgent()
    calls = []

    async def image(prompt, reference_images=None, **kwargs):
        calls.append((json.loads(prompt.split("\n输入：")[-1]), reference_images))
        return f"/media/panel-{len(calls)}.png"

    monkeypatch.setattr(agent.image_gen, "generate_image", image)
    panels = asyncio.run(
        agent.generate_panels(
            {"panels": [{"index": i, "action": f"action {i}"} for i in range(3)]},
            characters=[{"name": "小雨", "reference_image_url": "/media/character-sheet.png"}],
        )
    )
    assert calls[0][1] == ["/media/character-sheet.png"]
    assert calls[1][1] == ["/media/character-sheet.png", "/media/panel-1.png"]
    assert calls[2][1] == ["/media/character-sheet.png", "/media/panel-1.png", "/media/panel-2.png"]
    assert calls[2][0]["continuity"]["previous_shot"]["index"] == 1
    assert panels[2]["reference_images"] == calls[2][1]


def test_reviewer_actually_receives_identity_and_adjacent_images(monkeypatch):
    agent = StyleReviewerAgent()
    calls = []

    async def review(images, prompt):
        calls.append(images)
        return {"passed": True, "score": 90, "issues": []}

    monkeypatch.setattr(agent.llm_client, "review_images", review)
    result = asyncio.run(
        agent.review_panels(
            [{"index": i, "image_url": f"/media/p{i}.png"} for i in range(3)],
            characters=[{"reference_image_url": "/media/reference.png"}],
        )
    )
    assert result["passed"]
    assert calls[0] == ["/media/p0.png", "/media/reference.png"]
    assert calls[2] == ["/media/p2.png", "/media/reference.png", "/media/p0.png", "/media/p1.png"]
