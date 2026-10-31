from typing import Any, Dict, List, Tuple

import httpx

from app.core.config import settings


class GridPosition:
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    MIDDLE_LEFT = "middle_left"
    MIDDLE_RIGHT = "middle_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"

    GRID_MAP: Dict[str, Tuple[int, int, int, int]] = {
        CENTER: (33, 33, 66, 66),
        TOP_LEFT: (0, 0, 33, 33),
        TOP_CENTER: (33, 0, 66, 33),
        TOP_RIGHT: (66, 0, 100, 33),
        MIDDLE_LEFT: (0, 33, 33, 66),
        MIDDLE_RIGHT: (66, 33, 100, 66),
        BOTTOM_LEFT: (0, 66, 33, 100),
        BOTTOM_CENTER: (33, 66, 66, 100),
        BOTTOM_RIGHT: (66, 66, 100, 100),
    }

    @staticmethod
    def get_coordinates(position: str) -> Tuple[int, int, int, int]:
        return GridPosition.GRID_MAP.get(position, GridPosition.GRID_MAP[GridPosition.CENTER])


class CompositionControlService:
    def __init__(self):
        self.base_url = settings.SD_WEBUI_URL.rstrip("/") if settings.SD_WEBUI_URL else ""

    async def generate_scribble_sketch(
        self,
        panel_index: int,
        grid_position: str,
        character_positions: List[Dict[str, Any]] = [],
        background_elements: List[str] = [],
        width: int = 512,
        height: int = 512,
    ) -> str:
        if not self.base_url:
            return ""

        x1, y1, x2, y2 = GridPosition.get_coordinates(grid_position)

        scribble_points = []

        panel_center_x = (x1 + x2) * width // 200
        panel_center_y = (y1 + y2) * height // 200

        for char_pos in character_positions:
            char_grid_pos = char_pos.get("position", GridPosition.CENTER)
            cx1, cy1, cx2, cy2 = GridPosition.get_coordinates(char_grid_pos)
            char_x = panel_center_x + (cx1 + cx2) * width // 400 - width // 2
            char_y = panel_center_y + (cy1 + cy2) * height // 400 - height // 2

            scribble_points.append({
                "x": char_x,
                "y": char_y,
                "type": "circle",
                "radius": 30,
                "label": char_pos.get("character", "character"),
            })

        for element in background_elements:
            scribble_points.append({
                "x": width // 2,
                "y": height // 2,
                "type": "text",
                "text": element[:10],
            })

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/sdapi/v1/controlnet/scribble",
                    json={
                        "width": width,
                        "height": height,
                        "grid_position": grid_position,
                        "elements": scribble_points,
                    },
                )
                response.raise_for_status()
                response.encoding = "utf-8"
                result = response.json()

                if "image" in result:
                    return f"data:image/png;base64,{result['image']}"
                return ""
        except Exception:
            return ""

    async def generate_composition_mask(
        self,
        grid_position: str,
        character_regions: List[Dict[str, Any]] = [],
        width: int = 512,
        height: int = 512,
    ) -> str:
        if not self.base_url:
            return ""

        x1, y1, x2, y2 = GridPosition.get_coordinates(grid_position)

        mask_data = {
            "width": width,
            "height": height,
            "regions": [],
        }

        mask_data["regions"].append({
            "x": x1 * width // 100,
            "y": y1 * height // 100,
            "w": (x2 - x1) * width // 100,
            "h": (y2 - y1) * height // 100,
            "label": "panel_area",
        })

        for char_region in character_regions:
            char_pos = char_region.get("position", GridPosition.CENTER)
            cx1, cy1, cx2, cy2 = GridPosition.get_coordinates(char_pos)
            mask_data["regions"].append({
                "x": cx1 * width // 100,
                "y": cy1 * height // 100,
                "w": (cx2 - cx1) * width // 100,
                "h": (cy2 - cy1) * height // 100,
                "label": char_region.get("character", "character"),
            })

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/sdapi/v1/controlnet/mask",
                    json=mask_data,
                )
                response.raise_for_status()
                response.encoding = "utf-8"
                result = response.json()

                if "mask" in result:
                    return f"data:image/png;base64,{result['mask']}"
                return ""
        except Exception:
            return ""

    def build_composition_prompt(
        self,
        grid_position: str,
        character_positions: List[Dict[str, Any]] = [],
        shot_type: str = "medium",
    ) -> str:
        parts = [f"composition: {grid_position}"]

        shot_modifiers = {
            "close-up": "tight framing, focus on subject, detailed face",
            "medium": "medium shot, full body visible, balanced composition",
            "wide": "wide shot, full scene, environmental context",
            "extreme-wide": "extreme wide shot, grand scale, landscape",
        }

        parts.append(shot_modifiers.get(shot_type, shot_modifiers["medium"]))

        for char_pos in character_positions:
            char_name = char_pos.get("character")
            char_grid_pos = char_pos.get("position", GridPosition.CENTER)
            if char_name:
                parts.append(f"{char_name} positioned at {char_grid_pos}")

        return ", ".join(parts)
