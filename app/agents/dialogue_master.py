import json
from app.agents.base import TextAgent
from app.agents.skills import instructions
from app.models.schemas import DialogueSchema


class DialogueMasterAgent(TextAgent):
    async def generate_dialogues(self, outline, storyboard):
        prompt = (
            instructions("dialogue_master")
            + "\n输出 JSON Schema："
            + json.dumps(DialogueSchema.model_json_schema(), ensure_ascii=False)
            + "\n输入："
            + json.dumps({"outline": outline, "storyboard": storyboard}, ensure_ascii=False)
        )
        result = DialogueSchema.model_validate(await self.generate_json(prompt)).model_dump()
        indices = {p["index"] for p in storyboard["panels"]}
        for bubble in result["bubbles"]:
            if bubble["panel_index"] not in indices:
                raise ValueError("台词引用了不存在的分镜")
            if len(bubble["text"]) > 60:
                raise ValueError("单个气泡超过 60 字，请精简")
        return result

    async def execute(self, **kwargs):
        return await self.generate_dialogues(**kwargs)
