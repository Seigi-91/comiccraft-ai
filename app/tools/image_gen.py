import base64
import httpx
from app.core.config import settings
from app.tools.desktop_bridge import request_chatgpt
from app.tools.media import save_image_bytes


class ImageGeneratorClient:
    def __init__(self, model=None):
        self.model = model or settings.DEFAULT_IMAGE_MODEL

    async def generate_image(
        self,
        prompt,
        negative_prompt="",
        width=1024,
        height=1024,
        style="comic",
        reference_images=None,
        generation_context=None,
    ):
        from app.services.production_records import start_record,finish_record
        from app.tools.desktop_bridge import PendingChatGPT
        record_prompt=f"{prompt}\n画风：{style}。画幅 {width}×{height}。避免：{negative_prompt}。不要绘制文字或水印。"
        record=await start_record(record_prompt,reference_images,self.model,width,height,style,generation_context)
        try:
            result=await self._generate_image(prompt,negative_prompt,width,height,style,reference_images)
        except PendingChatGPT:
            await finish_record(record,'waiting')
            raise
        except Exception as error:
            await finish_record(record,'failed',error=type(error).__name__)
            raise
        await finish_record(record,'completed',image_url=result)
        return result

    async def _generate_image(self,prompt,negative_prompt,width,height,style,reference_images):
        full_prompt = f"{prompt}\n画风：{style}。画幅 {width}×{height}。避免：{negative_prompt}。不要绘制文字或水印。"
        if settings.AI_PROVIDER == "chatgpt_desktop":
            return request_chatgpt("image", full_prompt, reference_images)
        if reference_images:
            raise ValueError("HTTP 模式暂不支持参考图编辑，请使用 ChatGPT 协作模式")
        headers = (
            {"Authorization": f"Bearer {settings.LOCAL_GPT_API_KEY}"}
            if settings.LOCAL_GPT_API_KEY
            else {}
        )
        async with httpx.AsyncClient(timeout=settings.GPT_TIMEOUT) as client:
            response = await client.post(
                settings.LOCAL_GPT_BASE_URL.rstrip("/") + "/images/generations",
                headers=headers,
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "n": 1,
                    "size": f"{width}x{height}",
                },
            )
            response.raise_for_status()
            item = response.json()["data"][0]
            if item.get("b64_json"):
                return save_image_bytes(base64.b64decode(item["b64_json"], validate=True))
            if item.get("url"):
                image = await client.get(item["url"])
                image.raise_for_status()
                return save_image_bytes(image.content)
            raise ValueError("本地 GPT 未返回图片")

    async def generate_images(self, prompts, **kwargs):
        return [await self.generate_image(prompt, **kwargs) for prompt in prompts]
