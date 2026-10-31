"""Create a readable six-panel sheet and archive from unchanged generated art."""
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/rain-night-light"


def wrap(draw, text, font, max_width):
    result = []
    line = ""
    for char in text:
        if draw.textlength(line + char, font=font) > max_width:
            result.append(line)
            line = char
        else:
            line += char
    return result + ([line] if line else [])


def main():
    production = json.loads((OUTPUT / "production.json").read_text(encoding="utf-8"))
    font_path = "C:/Windows/Fonts/msyh.ttc"
    title_font = ImageFont.truetype(font_path, 64)
    subtitle_font = ImageFont.truetype(font_path, 25)
    caption_font = ImageFont.truetype(font_path, 29)
    number_font = ImageFont.truetype(font_path, 22)
    panel_size = 820
    width = 1800
    margin = 60
    gap = 40
    row_height = 980
    heading = 200
    canvas = Image.new("RGB", (width, heading + 3 * row_height + 80), "#f6f1e8")
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 34), "雨夜留灯", font=title_font, fill="#202735")
    draw.text((margin, 124), "一封旧信，一只小猫，一盏为晚归者留下的灯。", font=subtitle_font, fill="#6b655e")
    for panel in production["panels"]:
        index = panel["index"]
        x = margin + (index % 2) * (panel_size + gap)
        y = heading + (index // 2) * row_height
        with Image.open(OUTPUT / (panel["slug"] + ".png")) as source:
            # No paint-over or image repair: only proportional resizing of artwork.
            image = source.convert("RGB")
            image.thumbnail((panel_size, panel_size), Image.Resampling.LANCZOS)
            canvas.paste(image, (x + (panel_size-image.width)//2, y))
        draw.text((x, y + panel_size + 14), f"0{index+1}  {panel['title'].split('：')[-1]}", font=number_font, fill="#946f3c")
        for line_number, line in enumerate(wrap(draw, panel["caption"], caption_font, panel_size)):
            draw.text((x, y + panel_size + 51 + line_number*42), line, font=caption_font, fill="#252831")
    draw.text((margin, canvas.height - 50), "完  ·  人物设定与六格原图、提示词、创作与审核记录随作品保存", font=number_font, fill="#8a8176")
    sheet = OUTPUT / "雨夜留灯-六格漫画.png"
    canvas.save(sheet)
    preview = canvas.copy()
    preview.thumbnail((1100, 2200), Image.Resampling.LANCZOS)
    preview.save(OUTPUT / "雨夜留灯-预览.jpg", quality=92)
    files = [path for path in OUTPUT.rglob("*") if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".md", ".json"}]
    with ZipFile(OUTPUT / "雨夜留灯-完整创作包.zip", "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(OUTPUT))
        archive.write(ROOT / "skills/SOURCES.json", "skillsmp-sources.json")
    print(str(sheet))


if __name__ == '__main__':
    main()
