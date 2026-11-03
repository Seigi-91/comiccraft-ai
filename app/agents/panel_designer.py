import json
import hashlib
from copy import deepcopy
from app.agents.base import TextAgent
from app.agents.skills import instructions
from app.tools.image_gen import ImageGeneratorClient


class PanelDesignerAgent(TextAgent):
    def __init__(self, model=None, image_model=None, character_repo=None):
        super().__init__(model=model)
        self.image_gen = ImageGeneratorClient(image_model)
        self.character_repo = character_repo

    async def generate_panels(
        self,
        storyboard,
        style_ref_urls=None,
        characters=None,
        character_ids=None,
        previous=None,
        feedback=None,
        visual_reference_bindings=None,
        dialogue_positions=None,
    ):
        from app.tools.desktop_bridge import stage_context

        previous = {p["index"]: p for p in previous or []}
        reviews = {r["panel_index"]: r for r in (feedback or {}).get("panel_reviews", [])}
        results = []
        for panel in storyboard["panels"]:
            index = panel["index"]
            if index in previous and reviews.get(index, {}).get("passed"):
                results.append(previous[index])
                continue
            anchors = (visual_reference_bindings or {}).get(str(index), [])
            positions = panel.get("character_positions") or []
            visible = {p.get("character") for p in positions if isinstance(p, dict) and p.get("character")}
            cast = [c for c in characters or [] if not visible or c["name"] in visible]
            # Include retry round in prompt to prevent replaying rejected cached art.
            data = {
                "panel": panel,
                "characters": cast,
                "visual_references": anchors,
                "reference_precedence": "角色参考锁定身份，场景参考锁定空间与结构，道具参考锁定外形。本格剧本决定动作、时间、天气、服装版本和道具状态；参考图的旧状态不得覆盖本格。" if anchors else None,
                "lettering_space": (dialogue_positions or {}).get(index, []),
                "style_refs": style_ref_urls or [],
                "review": reviews.get(index),
                "previous_image": previous.get(index, {}).get("image_url") if reviews.get(index) else None,
                "continuity": {
                    "previous_shot": results[-1].get("shot") if results else None,
                    "previous_image": results[-1]["image_url"] if results else None,
                    "instruction": "角色表锁定身份；前一格用于场景和动作衔接，不复制构图。保持道具、服装、天气和行动方向。",
                },
            }
            prompt = (
                instructions("panel_designer", json.dumps(data, ensure_ascii=False)) + "\n输入：" + json.dumps(data, ensure_ascii=False)
            )
            from app.services.production_records import asset_hash
            if any(asset_hash(anchor["image_url"]) != anchor["sha256"] for anchor in anchors):
                raise ValueError("已锁定的参考图已变化或无法读取，请重新选择参考版本")
            references = [anchor["image_url"] for anchor in anchors]
            references.extend(c["reference_image_url"] for c in cast if c.get("reference_image_url"))
            if results:
                references.extend([results[0]["image_url"], results[-1]["image_url"]])
            references = list(dict.fromkeys(references))[:5]
            from app.api.routes.compatibility import fingerprint
            signature=hashlib.sha256(json.dumps({"prompt":prompt,"references":[[u,asset_hash(u)] for u in references],"provider":fingerprint('image')},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            candidate=previous.get(index,{})
            if not reviews.get(index) and candidate.get("status")=="generated" and candidate.get("request_signature")==signature and asset_hash(candidate.get("image_url")):
                results.append({**candidate,"reused_on_resume":True})
                from app.services.phase_progress import panel_progress
                if panel_progress.get():await panel_progress.get()(deepcopy(results))
                continue
            token = stage_context.set(f"panel_designer:{index}")
            try:
                image_url = await self.image_gen.generate_image(prompt, reference_images=references, generation_context=data)
            finally:
                stage_context.reset(token)
            results.append(
                {
                    "index": index,
                    "request_signature": signature,
                    "reused_on_resume": False,
                    "image_url": image_url,
                    "prompt": prompt,
                    "status": "generated",
                    "reference_images": references,
                    "visual_references": anchors,
                    "shot": panel,
                }
            )
            from app.services.phase_progress import panel_progress
            if panel_progress.get():await panel_progress.get()(deepcopy(results))
        return results

    async def execute(self, **kwargs):
        return {"panels": await self.generate_panels(**kwargs)}
