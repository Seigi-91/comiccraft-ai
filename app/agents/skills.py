from functools import lru_cache
import hashlib
import json
from app.core.paths import ROOT

ROLES = {
    "story_planner": "剧情策划师",
    "storyboard_artist": "分镜师",
    "dialogue_master": "台词大师",
    "panel_designer": "画面设计师",
    "style_reviewer": "风格审核官",
    "layout_artist": "排版与特效师",
}


@lru_cache
def sources():
    manifest = json.loads((ROOT / "skills/SOURCES.json").read_text(encoding="utf-8"))
    return manifest.get("skills", [])


@lru_cache
def instructions(role):
    if role not in ROLES:
        raise ValueError(f"Unknown comic agent: {role}")
    prompt = (ROOT / "app" / "prompts" / f"{role}.md").read_text(encoding="utf-8")
    skill = (ROOT / "skills" / role.replace("_", "-") / "SKILL.md").read_text(encoding="utf-8")
    upstream = []
    for entry in sources():
        if entry["role"] != role:
            continue
        original = ROOT / entry["installed_path"]
        runtime = ROOT / entry["runtime_path"]
        if hashlib.sha256(original.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(
                f"Upstream skill changed: {entry['name']}; review and regenerate manifest"
            )
        if hashlib.sha256(runtime.read_bytes()).hexdigest() != entry["runtime_sha256"]:
            raise ValueError(f"Runtime adaptation changed without review: {entry['name']}")
        upstream.append(runtime.read_text(encoding="utf-8"))
    if role == "layout_artist":
        upstream.append((ROOT / "skills/bubble-placement/SKILL.md").read_text(encoding="utf-8"))
    return "\n\n".join([prompt, skill, *upstream])


def catalog():
    return [
        {
            "id": key,
            "name": name,
            "instructions": instructions(key),
            "skill": f"skills/{key.replace('_', '-')}/SKILL.md",
            "upstream_skills": [entry for entry in sources() if entry["role"] == key],
        }
        for key, name in ROLES.items()
    ]
