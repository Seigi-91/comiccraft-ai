import json
import httpx
from app.core.config import settings
from app.tools.desktop_bridge import request_chatgpt


def parse_json(content):
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("模型必须返回 JSON 对象")
    return result


class LLMClient:
    def __init__(self, model=None, temperature=0.7):
        self.model = model or settings.DEFAULT_TEXT_MODEL
        self.temperature = temperature

    async def _request(self, prompt, images=None):
        if settings.AI_PROVIDER == "chatgpt_desktop":
            return request_chatgpt("vision" if images else "text", prompt, images)
        headers = (
            {"Authorization": f"Bearer {settings.LOCAL_GPT_API_KEY}"}
            if settings.LOCAL_GPT_API_KEY
            else {}
        )
        content = [{"type": "text", "text": prompt}]
        for image in images or []:
            from app.tools.media import image_data_url

            content.append({"type": "image_url", "image_url": {"url": image_data_url(image)}})
        async with httpx.AsyncClient(timeout=settings.GPT_TIMEOUT) as client:
            response = await client.post(
                settings.LOCAL_GPT_BASE_URL.rstrip("/") + "/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": content if images else prompt}],
                    "temperature": self.temperature,
                },
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
            if not isinstance(result, str) or not result.strip():
                raise ValueError("本地 GPT 返回空内容")
            return result

    async def generate(self, prompt):
        return await self._request(prompt)

    async def generate_json(self, prompt):
        return parse_json(await self.generate(prompt))

    def supports_vision(self):
        return True


class VisionLLMClient(LLMClient):
    def __init__(self, model=None, temperature=0.3):
        super().__init__(model or settings.DEFAULT_VISION_MODEL, temperature)

    async def review_image(self, image_url, prompt):
        return parse_json(await self._request(prompt, [image_url]))

    async def review_images(self, image_urls, prompt):
        return parse_json(await self._request(prompt, image_urls))
