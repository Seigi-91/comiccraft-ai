import asyncio
from pathlib import Path
from uuid import uuid4
from PIL import Image, ImageDraw, ImageFont
from app.agents.base import TextAgent
from app.agents.skills import instructions
from app.core.paths import MEDIA
from app.core.config import settings
from app.tools.media import local_image_path


class LayoutArtistAgent(TextAgent):
    async def compose_final(self, panels, dialogues, effects=None):
        self.system_prompt = instructions("layout_artist")
        return await asyncio.to_thread(self._render, panels, dialogues, effects)

    def _render(self, panels, dialogues, effects=None):
        if not panels or any(p.get("status") != "passed" for p in panels):
            raise ValueError("只有全部通过审核的面板可以导出")
        font_path = next(
            (
                p
                for p in [
                    Path(settings.COMIC_FONT_PATH) if settings.COMIC_FONT_PATH else Path("/__unset_comic_font__"),
                    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
                    Path("C:/Windows/Fonts/msyh.ttc"),
                    Path("C:/Windows/Fonts/simhei.ttf"),
                    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                ]
                if p.exists()
            ),
            None,
        )
        if font_path is None:
            raise ValueError("未找到字体，请安装中文字体")
        font = ImageFont.truetype(str(font_path), 26)
        width, margin = 1000, 28
        pieces = []
        geometry = []
        for panel in sorted(panels, key=lambda p: p["index"]):
            with Image.open(local_image_path(panel["image_url"])) as source:
                from app.services.effects import apply_effects
                image = apply_effects(source,(effects or {}).get(str(panel["index"]),[]))
                image.thumbnail((width - margin * 2, 1800))
                piece = Image.new("RGB", (width, image.height + margin * 2), "white")
                offset = (width - image.width) // 2
                piece.paste(image, (offset, margin))
                draw = ImageDraw.Draw(piece)
                placed = []
                for bubble in dialogues.get("bubbles", []):
                    if bubble["panel_index"] != panel["index"]:
                        continue
                    text = bubble["text"].strip()
                    if not text:
                        continue
                    font = ImageFont.truetype(str(font_path), bubble.get("font_size", 26))
                    size = bubble.get("size")
                    max_text_width = (round(image.width * size["width"] / 100) - 48) if size else min(340, image.width - 60)
                    if max_text_width < font.getlength("字"):
                        raise ValueError("气泡过窄，请增大宽度或减小字号")
                    lines, line = [], ""
                    for char in text:
                        if char == "\n":
                            lines.append(line); line = ""; continue
                        if line and font.getlength(line + char) > max_text_width:
                            lines.append(line); line = char
                        else:
                            line += char
                    if line:
                        lines.append(line)
                    bw = min(image.width - 12, max(100, int(max(font.getlength(l) for l in lines)) + 48))
                    bh = len(lines) * (font.size + 10) + 40
                    if size:
                        bw = round(image.width * size["width"] / 100)
                        requested_height = round(image.height * size["height"] / 100)
                        if bh > requested_height:
                            raise ValueError("气泡装不下文字，请增大高度、缩短台词或减小字号")
                        bh = requested_height
                    inset = 0 if size else 6
                    if bh > image.height - inset * 2:
                        raise ValueError("台词气泡过高，请缩短台词或使用更大的分镜")
                    position = bubble.get("position") or {}
                    px = max(0, min(100, position.get("x", 50)))
                    py = max(0, min(100, position.get("y", 15)))
                    left = offset + max(inset, min(image.width - bw - inset, round(image.width * px / 100 - bw / 2)))
                    top = margin + max(inset, min(image.height - bh - inset, round(image.height * py / 100 - bh / 2)))
                    # Find a nearby free region if two supplied positions collide.
                    def overlaps(box):
                        return any(box[0] < r[2]+10 and box[2]+10 > r[0] and box[1] < r[3]+10 and box[3]+10 > r[1] for r in placed)
                    candidates = [(left, top)] + [(x, y) for y in range(margin+6, margin+image.height-bh-5, 24) for x in (left, offset+6, offset+image.width-bw-6)]
                    candidates.sort(key=lambda xy: abs(xy[0]-left)+abs(xy[1]-top))
                    found = (left, top) if size else next(((x,y) for x,y in candidates if not overlaps((x,y,x+bw,y+bh))), None)
                    if found is None:
                        raise ValueError("气泡空间不足，请减少台词或调整分镜")
                    left, top = found
                    box = (left, top, left+bw, top+bh)
                    placed.append(box)
                    resolved_position = {"x": (left-offset+bw/2)/image.width*100, "y": (top-margin+bh/2)/image.height*100}
                    tip = bubble.get("tail") or {"x": max(0, (left-offset+23)/image.width*100), "y": min(100, (top-margin+bh+22)/image.height*100)}
                    geometry.append({**bubble, "position": resolved_position, "size": {"width": bw/image.width*100, "height": bh/image.height*100}, "tail": tip, "font_size": font.size})
                    kind = bubble.get("bubble_type", "speech").lower()
                    fill, ink = "#ffffff", "#151826"
                    tx, ty = offset+image.width*tip["x"]/100, margin+image.height*tip["y"]/100
                    cx, cy = left+bw/2, top+bh/2
                    dx, dy = tx-cx, ty-cy
                    factor = min(bw/2/abs(dx) if dx else float("inf"), bh/2/abs(dy) if dy else float("inf"))
                    outside = factor < 1
                    ex, ey = cx+dx*factor if outside else cx, cy+dy*factor if outside else cy
                    if kind in ("narration", "narrator", "caption", "旁白"):
                        draw.rounded_rectangle(box, radius=5, fill="#fff4da", outline=ink, width=3)
                    elif kind in ("thought", "thinking", "inner", "内心独白", "心声"):
                        if outside:
                            for t, radius in ((0.4, 7), (0.8, 4)):
                                x, y = ex+(tx-ex)*t, ey+(ty-ey)*t
                                draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=fill,outline=ink,width=2)
                        draw.rounded_rectangle(box, radius=36, fill=fill, outline=ink, width=3)
                    else:
                        if outside:
                            if abs(ex-cx)/(bw/2) >= abs(ey-cy)/(bh/2):
                                base=[(ex,max(top+10,ey-10)),(ex,min(top+bh-10,ey+10))]
                            else:
                                base=[(max(left+10,ex-10),ey),(min(left+bw-10,ex+10),ey)]
                            draw.polygon([base[0],(tx,ty),base[1]],fill=fill,outline=ink,width=3)
                        draw.rounded_rectangle(box, radius=28, fill=fill, outline=ink, width=3)
                        if outside:
                            draw.line(base,fill=fill,width=4)
                    for n, line in enumerate(lines):
                        draw.text((left+(bw-font.getlength(line))/2,top+17+n*(font.size+10)),line,font=font,fill=ink)
                pieces.append(piece)
        total = sum(p.height for p in pieces) + 20 * (len(pieces) - 1)
        if total > 40000:
            raise ValueError("条漫过长，请拆分章节")
        canvas = Image.new("RGB", (width, total), "#e5e7eb")
        y = 0
        for piece in pieces:
            canvas.paste(piece, (0, y))
            y += piece.height + 20
        path = MEDIA / f"comic-{uuid4().hex}.png"
        canvas.save(path)
        return {
            "final_image_url": f"/media/{path.name}",
            "width": width,
            "height": total,
            "layout_type": "条漫",
            "total_panels": len(panels),
            "bubble_geometry": geometry,
        }

    async def execute(self, **kwargs):
        return await self.compose_final(**kwargs)
