import base64
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from PIL import Image
from app.core.paths import MEDIA


def local_image_path(url):
    if not url.startswith("/media/") or Path(url).name != url.removeprefix("/media/"):
        raise ValueError("仅支持本站 /media/ 图片")
    return MEDIA / Path(url).name


def save_image_bytes(data):
    if len(data) > 20 * 1024 * 1024:
        raise ValueError("图片不得超过 20 MB")
    with Image.open(BytesIO(data)) as image:
        if image.width * image.height > 25_000_000:
            raise ValueError("图片像素过大")
        image.load()
        path = MEDIA / f"{uuid4().hex}.png"
        image.convert("RGB").save(path)
    return f"/media/{path.name}"


def image_data_url(url):
    if url.startswith("/media/"):
        return (
            "data:image/png;base64," + base64.b64encode(local_image_path(url).read_bytes()).decode()
        )
    return url
