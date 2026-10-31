import json
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
            # Include retry round in prompt to prevent replaying rejected cached art.
            data = {
                "panel": panel,
                "characters": characters or [],
                "style_refs": style_ref_urls or [],
                "review": reviews.get(index),
                "previous_image": previous.get(index, {}).get("image_url"),
                "continuity": {
                    "previous_shot": results[-1].get("shot") if results else None,
                    "previous_image": results[-1]["image_url"] if results else None,
                    "instruction": "角色表锁定身份；前一格用于场景和动作衔接，不复制构图。保持道具、服装、天气和行动方向。",
                },
            }
            prompt = (
                instructions("panel_designer") + "\n输入：" + json.dumps(data, ensure_ascii=False)
            )
            references = [
                c["reference_image_url"] for c in characters or [] if c.get("reference_image_url")
            ]
            if results:
                references.extend([results[0]["image_url"], results[-1]["image_url"]])
            references = list(dict.fromkeys(references))[:5]
            token = stage_context.set(f"panel_designer:{index}")
            try:
                image_url = await self.image_gen.generate_image(prompt, reference_images=references, generation_context=data)
            finally:
                stage_context.reset(token)
            results.append(
                {
                    "index": index,
                    "image_url": image_url,
                    "prompt": prompt,
                    "status": "generated",
                    "reference_images": references,
                    "shot": panel,
                }
            )
        return results

    async def execute(self, **kwargs):
        return {"panels": await self.generate_panels(**kwargs)}
