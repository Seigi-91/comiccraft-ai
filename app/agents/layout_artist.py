import asyncio
from pathlib import Path
from uuid import uuid4
from PIL import Image, ImageDraw, ImageFont
from app.agents.base import TextAgent
from app.agents.skills import instructions
from app.core.paths import MEDIA
from app.core.config import settings
from app.tools.media import local_image_path
from app.services.page_framing import INK, PAPER, frame_page_art, region_box


class LayoutArtistAgent(TextAgent):
    async def compose_final(self, panels, dialogues, effects=None, storyboard=None):
        self.system_prompt = instructions("layout_artist", str(dialogues))
        return await asyncio.to_thread(self._render, panels, dialogues, effects, storyboard)

    def _render(self, panels, dialogues, effects=None, storyboard=None):
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
        has_chinese=any('\u4e00'<=char<='\u9fff' for bubble in dialogues.get('bubbles',[]) for char in bubble.get('text',''))
        if has_chinese and bytes(font.getmask('中'))==bytes(font.getmask('\uffff')):
            raise ValueError('所选字体缺少中文字形，请安装 Noto Sans CJK 并设置 COMIC_FONT_PATH')
        width, strip_margin = 1000, 28
        from app.services.comic_plan import PAGE_SIZE, validate_pages
        pages = (storyboard or {}).get("pages") or []
        placements = {}
        page_offsets = []
        next_page_top = 0
        compositions = {shot["index"]: shot.get("composition") or {} for shot in (storyboard or {}).get("panels", [])}
        if pages:
            validate_pages(pages, [panel["index"] for panel in panels])
            for page_no, page in enumerate(pages):
                page_offsets.append(next_page_top)
                next_page_top += page.get("height", PAGE_SIZE[1]) + 20
                for region in page["regions"]:
                    placements[region["panel_index"]] = (page_no, region)
        pieces = []
        geometry = []
        for panel in sorted(panels, key=lambda p: p["index"]):
            with Image.open(local_image_path(panel["image_url"])) as source:
                from app.services.effects import apply_effects
                image = apply_effects(source,(effects or {}).get(str(panel["index"]),[]))
                panel_bubbles = [bubble for bubble in dialogues.get("bubbles", [])
                                 if bubble["panel_index"] == panel["index"]]
                if pages:
                    page_no, region = placements[panel["index"]]
                    page_width, default_height = PAGE_SIZE
                    page_height = pages[page_no].get("height", default_height)
                    slot_width = round((region["x"] + region["width"]) * page_width / 100) - round(region["x"] * page_width / 100)
                    slot_height = round((region["y"] + region["height"]) * page_height / 100) - round(region["y"] * page_height / 100)
                    piece, (art_width, art_height), (offset, margin), visible = frame_page_art(
                        image, (slot_width, slot_height), compositions.get(panel["index"], {}), panel_bubbles
                    )
                else:
                    image.thumbnail((width - strip_margin * 2, 1800))
                    art_width, art_height = image.size
                    offset, margin = (width - art_width) // 2, strip_margin
                    visible = offset, margin, offset + art_width, margin + art_height
                    piece = Image.new("RGB", (width, art_height + strip_margin * 2), "white")
                    piece.paste(image, (offset, margin))
                visible_left, visible_top, visible_right, visible_bottom = visible
                visible_width = visible_right - visible_left
                visible_height = visible_bottom - visible_top
                draw = ImageDraw.Draw(piece)
                placed = []
                keep_clear = []
                if pages:
                    regions = compositions.get(panel["index"], {}).get("lettering_keep_clear")
                    if isinstance(regions, list):
                        for item in regions:
                            box = region_box(item)
                            if box:
                                (x0, y0), (x1, y1) = box
                                keep_clear.append((offset + x0 * art_width, margin + y0 * art_height,
                                                   offset + x1 * art_width, margin + y1 * art_height))
                    for child in pages[page_no]["regions"]:
                        if child.get("inset_of") != panel["index"]:
                            continue
                        left = round(child["x"] * page_width / 100) - round(region["x"] * page_width / 100)
                        top = round(child["y"] * page_height / 100) - round(region["y"] * page_height / 100)
                        placed.append((left, top, left + round(child["width"] * page_width / 100),
                                       top + round(child["height"] * page_height / 100)))
                for bubble in panel_bubbles:
                    text = bubble["text"].strip()
                    if not text:
                        continue
                    default_font = (20 if visible_width < 420 else 22) if pages else 26
                    font = ImageFont.truetype(str(font_path), bubble.get("font_size", default_font))
                    size = bubble.get("size")
                    padding = 32 if pages else 48
                    line_gap = 7 if pages else 10
                    vertical_padding = 28 if pages else 40
                    max_text_width = (round(art_width * size["width"] / 100) - padding) if size else min(340, visible_width - padding - 12)
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
                    bw = min(visible_width - 12, max(100, int(max(font.getlength(l) for l in lines)) + padding))
                    bh = len(lines) * (font.size + line_gap) + vertical_padding
                    if size:
                        bw = round(art_width * size["width"] / 100)
                        requested_height = round(art_height * size["height"] / 100)
                        if bh > requested_height:
                            raise ValueError("气泡装不下文字，请增大高度、缩短台词或减小字号")
                        bh = requested_height
                    inset = 0 if size else 6
                    if bh > visible_height - inset * 2 or bw > visible_width - inset * 2:
                        raise ValueError("气泡超出可见格区，请缩短台词或使用更大的分镜")
                    position = bubble.get("position") or {}
                    px = max(0, min(100, position.get("x", 50)))
                    py = max(0, min(100, position.get("y", 15)))
                    desired_x, desired_y = offset + art_width * px / 100, margin + art_height * py / 100
                    left = max(visible_left + inset, min(visible_right - bw - inset, round(desired_x - bw / 2)))
                    top = max(visible_top + inset, min(visible_bottom - bh - inset, round(desired_y - bh / 2)))

                    def overlaps(box, regions):
                        return any(box[0] < r[2]+10 and box[2]+10 > r[0] and box[1] < r[3]+10 and box[3]+10 > r[1] for r in regions)

                    candidates = [(left, top)] + [(x, y) for y in range(visible_top+6, visible_bottom-bh-5, 24) for x in (left, visible_left+6, visible_right-bw-6)]
                    candidates.sort(key=lambda xy: abs(xy[0]-left)+abs(xy[1]-top))
                    available = [(x,y) for x,y in candidates if not overlaps((x,y,x+bw,y+bh), placed)]
                    found = (left, top) if size else next(
                        ((x,y) for x,y in available if not overlaps((x,y,x+bw,y+bh), keep_clear)),
                        available[0] if available else None,
                    )
                    if found is None:
                        raise ValueError("气泡空间不足，请减少台词或调整分镜")
                    left, top = found
                    box = (left, top, left+bw, top+bh)
                    placed.append(box)
                    resolved_position = {
                        "x": (left-offset+bw/2)/art_width*100,
                        "y": (top-margin+bh/2)/art_height*100,
                    }
                    if size and abs(left + bw / 2 - desired_x) <= 1 and abs(top + bh / 2 - desired_y) <= 1:
                        resolved_position = {"x": px, "y": py}
                    tip = bubble.get("tail") or {
                        "x": (min(visible_right - 1, left+23)-offset)/art_width*100,
                        "y": (min(visible_bottom - 1, top+bh+22)-margin)/art_height*100,
                    }
                    resolved_size = size if size else {"width": bw/art_width*100, "height": bh/art_height*100}
                    geometry.append({**bubble, "position": resolved_position, "size": resolved_size, "tail": tip, "font_size": font.size})
                    kind = bubble.get("bubble_type", "speech").lower()
                    fill, ink = ("#fffdf4", INK) if pages else ("#ffffff", "#151826")
                    tx, ty = offset+art_width*tip["x"]/100, margin+art_height*tip["y"]/100
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
                        draw.text((left+(bw-font.getlength(line))/2,top+(11 if pages else 17)+n*(font.size+line_gap)),line,font=font,fill=ink)
                if pages:
                    frame = (0, 0, piece.width - 1, piece.height - 1)
                    if region.get("inset_of") is not None:
                        draw.rectangle(frame, outline=PAPER, width=7)
                    draw.rectangle(frame, outline=INK, width=3)
                    pieces.append((piece, (round(region["x"] * page_width / 100),
                                           round(region["y"] * page_height / 100) + page_offsets[page_no])))
                else:
                    pieces.append((piece, (0, pieces[-1][1][1] + pieces[-1][0].height + 20 if pieces else 0)))
        total = next_page_top - 20 if pages else pieces[-1][1][1] + pieces[-1][0].height
        if total > 40000:
            raise ValueError("成稿过长，请拆分章节")
        canvas = Image.new("RGB", (width, total), "#e5e7eb")
        if pages:
            for page, top in zip(pages, page_offsets):
                canvas.paste(PAPER, (0, top, width, top + page.get("height", PAGE_SIZE[1])))
        for piece, origin in pieces:
            canvas.paste(piece, origin)
        path = MEDIA / f"comic-{uuid4().hex}.png"
        canvas.save(path)
        return {
            "final_image_url": f"/media/{path.name}",
            "width": width,
            "height": total,
            "layout_type": "分页" if pages else "条漫",
            "total_panels": len(panels),
            "bubble_geometry": geometry,
        }

    async def execute(self, **kwargs):
        return await self.compose_final(**kwargs)
