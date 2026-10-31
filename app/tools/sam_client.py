import base64
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings


class SAMClient:
    def __init__(self):
        self.base_url = settings.SD_WEBUI_URL.rstrip("/") if settings.SD_WEBUI_URL else ""

    async def segment_face(self, image_url: str) -> Dict[str, Any]:
        if not self.base_url:
            return {
                "mask_url": "",
                "bbox": {"x": 50, "y": 50, "width": 150, "height": 150},
                "success": False,
                "message": "SD WebUI not configured, returning placeholder",
            }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/sdapi/v1/sam/segment",
                    json={
                        "image_url": image_url,
                        "points": [[256, 256]],
                        "labels": [1],
                    },
                )
                response.raise_for_status()
                response.encoding = "utf-8"
                result = response.json()

                if "mask" in result:
                    return {
                        "mask_url": f"data:image/png;base64,{result['mask']}",
                        "bbox": result.get("bbox", {"x": 0, "y": 0, "width": 512, "height": 512}),
                        "success": True,
                        "message": "Face segmentation successful",
                    }
                return {
                    "mask_url": "",
                    "bbox": {"x": 50, "y": 50, "width": 150, "height": 150},
                    "success": False,
                    "message": "No mask returned",
                }
        except Exception as e:
            return {
                "mask_url": "",
                "bbox": {"x": 50, "y": 50, "width": 150, "height": 150},
                "success": False,
                "message": f"Segmentation failed: {str(e)}",
            }

    async def extract_ip_adapter_embedding(self, image_url: str) -> List[float]:
        if not self.base_url:
            return [0.0] * 768

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/sdapi/v1/ip-adapter/extract",
                    json={"image_url": image_url, "model": "ip-adapter_sd15"},
                )
                response.raise_for_status()
                response.encoding = "utf-8"
                result = response.json()

                if "embedding" in result:
                    return result["embedding"]
                return [0.0] * 768
        except Exception as e:
            return [0.0] * 768


class CharacterConsistencyService:
    def __init__(self, character_repo=None):
        self.sam_client = SAMClient()
        self.character_repo = character_repo
        self.character_embeddings: Dict[str, List[float]] = {}
        self.character_reference_images: Dict[str, str] = {}

    async def create_character_profile(
        self,
        character_id: str,
        name: str,
        reference_image_url: str,
        appearance_description: str = "",
    ) -> Dict[str, Any]:
        segment_result = await self.sam_client.segment_face(reference_image_url)
        embedding = await self.sam_client.extract_ip_adapter_embedding(reference_image_url)

        self.character_embeddings[character_id] = embedding
        self.character_reference_images[character_id] = reference_image_url

        if self.character_repo:
            await self.character_repo.update(character_id, {
                "reference_image_url": reference_image_url,
                "face_mask_url": segment_result.get("mask_url", ""),
                "face_bbox": segment_result.get("bbox", {}),
                "ip_adapter_embedding": {"embedding": embedding},
            })

        return {
            "character_id": character_id,
            "name": name,
            "reference_image_url": reference_image_url,
            "face_mask_url": segment_result.get("mask_url", ""),
            "face_bbox": segment_result.get("bbox", {}),
            "embedding_extracted": len(embedding) > 0,
            "appearance_description": appearance_description,
            "created_at": "2026-07-13T00:00:00Z",
        }

    async def get_character_reference_images(self, character_ids: List[str]) -> List[str]:
        if self.character_repo:
            images = []
            for cid in character_ids:
                profile = await self.character_repo.get(cid)
                if profile and profile.is_confirmed and profile.reference_image_url:
                    images.append(profile.reference_image_url)
            return images

        return [
            self.character_reference_images.get(cid, "")
            for cid in character_ids
            if self.character_reference_images.get(cid)
        ]

    async def get_character_embedding(self, character_id: str) -> Optional[List[float]]:
        if self.character_repo:
            profile = await self.character_repo.get(character_id)
            if profile and profile.ip_adapter_embedding:
                return profile.ip_adapter_embedding.get("embedding", [])
        return self.character_embeddings.get(character_id)

    async def update_character_reference(self, character_id: str, new_image_url: str) -> bool:
        try:
            embedding = await self.sam_client.extract_ip_adapter_embedding(new_image_url)
            self.character_embeddings[character_id] = embedding
            self.character_reference_images[character_id] = new_image_url

            if self.character_repo:
                await self.character_repo.update(character_id, {
                    "reference_image_url": new_image_url,
                    "ip_adapter_embedding": {"embedding": embedding},
                })

            return True
        except Exception:
            return False

    async def confirm_character_profile(self, character_id: str) -> bool:
        if self.character_repo:
            profile = await self.character_repo.confirm(character_id)
            return profile is not None
        return False
