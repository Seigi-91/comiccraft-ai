"""Frame artwork without losing the original coordinate system used by lettering."""
from PIL import Image

PAPER = "#e9e6de"
INK = "#1d2630"
MATTE = "#25282d"


def point(value):
    if isinstance(value, dict) and all(
        isinstance(value.get(key), (int, float)) and 0 <= value[key] <= 100 for key in ("x", "y")
    ):
        return value["x"] / 100, value["y"] / 100
    return None


def region_box(region):
    start = point(region)
    if not start:
        return None
    size = point({"x": region.get("width"), "y": region.get("height")})
    if size:
        return start, (min(1, start[0] + size[0]), min(1, start[1] + size[1]))
    return None


def protected_boxes(composition, bubbles):
    focal = point(composition.get("focal_point"))
    boxes = [(focal, focal)] if focal else []
    subshots = composition.get("subshots")
    regions = [composition.get("crop_safe_area")]
    if isinstance(subshots, list):
        regions.extend(shot.get("region") for shot in subshots if isinstance(shot, dict))
    lettering = composition.get("lettering_keep_clear")
    if isinstance(lettering, list):
        regions.extend(lettering)
    boxes.extend(box for region in regions if (box := region_box(region)))
    for bubble in bubbles:
        if not bubble["text"].strip():
            continue
        tail = point(bubble.get("tail"))
        if tail:
            boxes.append((tail, tail))
        position = point(bubble.get("position"))
        size = bubble.get("size")
        if size and position:
            half_width, half_height = size["width"] / 200, size["height"] / 200
            x, y = position
            boxes.append(((max(0, x - half_width), max(0, y - half_height)),
                          (min(1, x + half_width), min(1, y + half_height))))
    return boxes


def frame_page_art(image, slot_size, composition, bubbles):
    """Return frame, full-source drawing extent, origin and visible artwork bounds."""
    slot_width, slot_height = slot_size
    scale = max(slot_width / image.width, slot_height / image.height)
    full_width, full_height = image.width * scale, image.height * scale
    fractions = min(1, slot_width / full_width), min(1, slot_height / full_height)
    focal = point(composition.get("focal_point")) or (0.5, 0.5)
    boxes = protected_boxes(composition, bubbles)
    offsets = []
    for axis, fraction in enumerate(fractions):
        if fraction < 0.45:
            break
        low = max(0, max((end[axis] for _, end in boxes), default=0) - fraction)
        high = min(1 - fraction, min((start[axis] for start, _ in boxes), default=1))
        if low > high + 1e-9:
            break
        offsets.append(max(low, min(high, focal[axis] - fraction / 2)))
    if len(offsets) == 2:
        left, top = offsets
        crop = (left * image.width, top * image.height,
                min(image.width, (left + fractions[0]) * image.width),
                min(image.height, (top + fractions[1]) * image.height))
        frame = image.resize(slot_size, Image.Resampling.LANCZOS, box=crop)
        return frame, (full_width, full_height), (-left * full_width, -top * full_height), (0, 0, slot_width, slot_height)

    scale = min(slot_width / image.width, slot_height / image.height)
    width, height = max(1, round(image.width * scale)), max(1, round(image.height * scale))
    x, y = (slot_width - width) // 2, (slot_height - height) // 2
    frame = Image.new("RGB", slot_size, MATTE)
    frame.paste(image.resize((width, height), Image.Resampling.LANCZOS), (x, y))
    return frame, (width, height), (x, y), (x, y, x + width, y + height)
