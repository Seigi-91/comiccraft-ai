from typing import Any, Dict, List

import httpx

from app.core.config import settings


class SDClient:
    def __init__(self):
        self.base_url = settings.SD_WEBUI_URL.rstrip("/")
        self.api_key = settings.SD_WEBUI_API_KEY

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        control_type: str = "scribble",
        ip_adapter_images: List[str] = [],
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
        cfg_scale: float = 7.0,
        seed: int = -1,
    ) -> str:
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "seed": seed,
            "controlnet_units": [],
        }

        if control_type == "scribble":
            payload["controlnet_units"].append({
                "module": "scribble",
                "model": "control_sd15_scribble [fef5e48e]",
                "weight": 1.0,
                "resize_mode": "Crop and Resize",
                "control_mode": "Balanced",
            })

        if ip_adapter_images:
            payload["alwayson_scripts"] = {
                "IP-Adapter": {
                    "args": [
                        {
                            "image": img_url,
                            "weight": 0.8,
                        }
                        for img_url in ip_adapter_images[:3]
                    ]
                }
            }

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    f"{self.base_url}/sdapi/v1/txt2img",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                )
                response.raise_for_status()
                response.encoding = "utf-8"
                result = response.json()

                if "images" in result and result["images"]:
                    return f"data:image/png;base64,{result['images'][0]}"
                return "https://example.com/placeholder.png"
        except Exception as e:
            return None

    async def inpaint(
        self,
        image_url: str,
        mask_url: str,
        prompt: str,
        negative_prompt: str = "",
    ) -> str:
        # TODO: 实现局部重绘功能
        return "https://example.com/inpainted.png"
