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
        scenes = {scene["id"]: scene for scene in storyboard.get("scenes", [])}
        from app.services.comic_plan import PAGE_SIZE
        slots = {region["panel_index"]: {**region, "page_height": page.get("height", PAGE_SIZE[1])}
                 for page in storyboard.get("pages") or [] for region in page["regions"]}
        for panel in storyboard["panels"]:
            index = panel["index"]
            if index in previous and reviews.get(index, {}).get("passed"):
                results.append(previous[index])
                continue
            anchors = (visual_reference_bindings or {}).get(str(index), [])
            positions = panel.get("character_positions") or []
            visible = {p.get("character") for p in positions if isinstance(p, dict) and p.get("character")}
            cast = [c for c in characters or [] if not visible or c["name"] in visible]
            scene = scenes.get(panel.get("scene_id"))
            preceding = [
                item for item in results
                if (item.get("shot") or {}).get("scene_id") == panel.get("scene_id")
            ]
            previous_shot = preceding[-1] if results and preceding and preceding[-1] == results[-1] else None
            slot = slots.get(index)
            aspect = round(slot["width"] * PAGE_SIZE[0] / (slot["height"] * slot["page_height"]), 3) if slot else None
            insets = [
                {key: round((other[key] - slot[key] if key in ("x", "y") else other[key])
                            * 100 / slot["width" if key in ("x", "width") else "height"], 2)
                 for key in ("x", "y", "width", "height")}
                for other in slots.values() if slot and other.get("inset_of") == index
            ]
            composition = panel.get("composition") or {}
            from app.services.subshots import subshot_directive
            multishot = subshot_directive(composition) if composition.get("subshot_strategy") else None
            # Include retry round in prompt to prevent replaying rejected cached art.
            data = {
                "panel": panel,
                **({"subshot_directive": multishot} if multishot else {}),
                "characters": cast,
                "scene_memory": scene,
                "current_scene_state": panel.get("scene_state"),
                "page_aspect_ratio": aspect,
                "inset_keep_clear": insets,
                "page_framing": "按目标宽高构图，主体、子镜头与对白留白均须完整入镜。inset_keep_clear 是主格内需留空的百分比区域。" if slot else None,
                "visual_references": anchors,
                "reference_precedence": "角色参考锁定身份，场景参考锁定空间与结构，道具参考锁定外形。本格剧本决定动作、时间、天气、服装版本和道具状态；参考图的旧状态不得覆盖本格。" if anchors else None,
                "lettering_space": (dialogue_positions or {}).get(index, []),
                "style_refs": style_ref_urls or [],
                "review": reviews.get(index),
                "previous_image": previous.get(index, {}).get("image_url") if reviews.get(index) else None,
                "continuity": {
                    "previous_shot": previous_shot.get("shot") if previous_shot else None,
                    "previous_image": previous_shot["image_url"] if previous_shot else None,
                    "instruction": "角色表锁定身份；前一格用于场景和动作衔接。明确要求固定机位或动作对照时沿用机位、画幅和地标，只更新本格剧情变化；其余镜头按当前构图绘制。保持道具、服装、天气和行动方向的连续性。",
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
            continuity = [preceding[0], previous_shot] if previous_shot else []
            references.extend(item["image_url"] for item in continuity)
            references = list(dict.fromkeys(references))[:5]
            dependencies = sorted({item["index"] for item in continuity if item["image_url"] in references})
            from app.core.config import settings
            width = height = 1024
            if aspect and (settings.image_provider == "codex_cli" or (settings.IMAGE_PROVIDER and settings.IMAGE_API_MODEL.startswith("gpt-image"))):
                if aspect > 1.2:
                    width = 1536
                elif aspect < 0.83:
                    height = 1536
            from app.api.routes.compatibility import fingerprint
            signature=hashlib.sha256(json.dumps({"prompt":prompt,"size":[width,height],"references":[[u,asset_hash(u)] for u in references],"provider":fingerprint('image')},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            candidate=previous.get(index,{})
            if not reviews.get(index) and candidate.get("status")=="generated" and candidate.get("request_signature")==signature and asset_hash(candidate.get("image_url")):
                results.append({**candidate,"reused_on_resume":True})
                from app.services.phase_progress import panel_progress
                if panel_progress.get():await panel_progress.get()(deepcopy(results))
                continue
            token = stage_context.set(f"panel_designer:{index}")
            try:
                image_url = await self.image_gen.generate_image(prompt, width=width, height=height, reference_images=references, generation_context=data)
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
                    "continuity_source_indices": dependencies,
                    "visual_references": anchors,
                    "shot": panel,
                }
            )
            from app.services.phase_progress import panel_progress
            if panel_progress.get():await panel_progress.get()(deepcopy(results))
        return results

    async def execute(self, **kwargs):
        return {"panels": await self.generate_panels(**kwargs)}
