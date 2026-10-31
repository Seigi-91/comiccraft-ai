import json
from app.agents.base import TextAgent
from app.agents.skills import instructions
from app.models.schemas import StorySchema


class StoryPlannerAgent(TextAgent):
    async def generate_outline(self, inspiration, style_ref_urls=None, characters=None):
        prompt = (
            instructions("story_planner")
            + "\n输出 JSON Schema："
            + json.dumps(StorySchema.model_json_schema(), ensure_ascii=False)
            + "\n输入："
            + json.dumps(
                {
                    "inspiration": inspiration,
                    "style_ref_urls": style_ref_urls or [],
                    "characters": characters or [],
                },
                ensure_ascii=False,
            )
        )
        return StorySchema.model_validate(await self.generate_json(prompt)).model_dump()

    async def execute(self, **kwargs):
        return await self.generate_outline(**kwargs)
