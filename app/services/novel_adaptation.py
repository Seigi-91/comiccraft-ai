"""Lossless bounded source segmentation and immutable chapter adaptation inputs."""
import hashlib
import re
from sqlalchemy import select
from app.models.orm import NovelAdaptation

MAX_TEXT = 300_000
SEGMENT_SIZE = 8_000
MAX_SEGMENTS = 200
HEADING = re.compile(r"(?m)^[ \t]*(?:#{1,6}[ \t]+)?(?:第[零〇一二三四五六七八九十百千万两0-9]+[章回节卷部][^\n]{0,100}|(?:序章|序言|楔子|尾声|后记)[^\n]{0,80}|chapter[ \t]+[0-9ivxlcdm]+[^\n]{0,100})[ \t]*$", re.IGNORECASE)


def normalize(text):
    text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip() or len(text) > MAX_TEXT or "\x00" in text:
        raise ValueError("请输入非空小说正文，最多30万字符，不接受二进制文件")
    return text


def split_novel(text):
    text = normalize(text)
    headings = []
    for heading in HEADING.finditer(text):
        headings.append(heading)
        if len(headings) > MAX_SEGMENTS:
            raise ValueError("章节标题超过200个，请分卷导入")
    starts = [m.start() for m in headings]
    if starts and not text[:starts[0]].strip():
        starts.pop(0)
    boundaries = sorted({0, len(text), *starts})
    segments = []
    for start, end in zip(boundaries, boundaries[1:]):
        cursor = start
        while cursor < end:
            stop = min(cursor + SEGMENT_SIZE, end)
            if stop < end:
                paragraph = text.rfind("\n", cursor + SEGMENT_SIZE // 2, stop)
                if paragraph >= 0:
                    stop = paragraph + 1
            excerpt = text[cursor:stop]
            first = excerpt.strip().split("\n", 1)[0][:90] if excerpt.strip() else "空白前言"
            title = first if HEADING.fullmatch(first) else f"片段 {len(segments) + 1}"
            segments.append({"index": len(segments), "title": title, "start": cursor, "end": stop, "characters": stop - cursor})
            cursor = stop
    if len(segments) > MAX_SEGMENTS:
        raise ValueError("分段超过200段，请分卷导入")
    return text, segments


async def chapter_source(db, chapter_id):
    row = (await db.execute(select(NovelAdaptation).where(NovelAdaptation.chapter_id == chapter_id))).scalar_one_or_none()
    return row.snapshot if row else None


def source_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
