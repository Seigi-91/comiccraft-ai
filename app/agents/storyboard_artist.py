import json
from app.agents.base import TextAgent
from app.agents.skills import instructions
from app.models.schemas import StoryboardSchema


class StoryboardArtistAgent(TextAgent):
    async def generate_storyboard(self, outline, style_ref_urls=None):
        prompt = (
            instructions("storyboard_artist")
            + "\n输出 JSON Schema："
            + json.dumps(StoryboardSchema.model_json_schema(), ensure_ascii=False)
            + "\n输入："
            + json.dumps(outline, ensure_ascii=False)
        )
        result = StoryboardSchema.model_validate(await self.generate_json(prompt)).model_dump()
        if not result["panels"] or len(result["panels"]) > 24:
            raise ValueError("分镜数量必须为 1–24")
        if [p["index"] for p in result["panels"]] != list(range(len(result["panels"]))):
            raise ValueError("分镜 index 必须从 0 连续递增")
        return result

    async def execute(self, **kwargs):
        return await self.generate_storyboard(**kwargs)
