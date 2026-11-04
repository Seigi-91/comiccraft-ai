"""Validate and translate in-panel multi-shot plans into renderer instructions."""

TECHNIQUES = {
    "detail": (1, "主画面交代动作与物体归属，小格只放大同一时刻的关键细节。"),
    "pov": (1, "主画面先建立谁在看，小格从该人物的视点呈现所见，保留视线方向和可辨认的目标。"),
    "reaction": (1, "主画面交代触发，短暂表情或手势用一个近景小格回应。需要停顿的反应留独立外格。"),
    "action_progression": (2, "子镜头依次推进同一短动作，保持机位、方向和道具归属。避免把不同瞬间画成同场分身。"),
    "memory": (1, "现时画面主导，小格只给一瞥记忆。用色温、边框或视角差异区分时间层，读完仍回到当前场景。"),
    "parallel": (1, "已交代的另一空间只短暂切入，使用共享信号提示同步，人物与地标分开。完整的第二事件另开格。"),
}
CUE_REQUIRED = {"pov", "action_progression", "memory", "parallel"}


def rectangle(region):
    if not isinstance(region, dict):
        raise ValueError("子镜头需要填写位置和大小")
    x, y, width, height = (region.get(key) for key in ("x", "y", "width", "height"))
    if (not all(type(value) in (int, float) and 0 <= value <= 100 for value in (x, y, width, height))
            or not width or not height or x + width > 100 or y + height > 100):
        raise ValueError("子镜头须位于画框内，且宽高大于零")
    return x, y, x + width, y + height


def overlaps(left, right):
    return (max(left[0], right[0]) < min(left[2], right[2])
            and max(left[1], right[1]) < min(left[3], right[3]))


def subshot_directive(composition):
    """Keep legacy geometry valid and apply stronger constraints to tagged techniques."""
    shots = composition.get("subshots")
    shots = [] if shots is None else shots
    if not isinstance(shots, list) or len(shots) > 4:
        raise ValueError("每格最多四个子镜头")
    boxes = [rectangle(shot.get("region") if isinstance(shot, dict) else None) for shot in shots]
    technique = composition.get("subshot_strategy")
    if not technique:
        return None
    if not isinstance(technique, str) or technique not in TECHNIQUES:
        raise ValueError("未知格内镜头手法")
    max_count, guide = TECHNIQUES[technique]
    if not 1 <= len(shots) <= max_count:
        raise ValueError(f"{technique} 须有 1–{max_count} 个子镜头")
    cue = composition.get("subshot_cue") or ""
    if not isinstance(cue, str) or len(cue) > 240 or (technique in CUE_REQUIRED and not cue.strip()):
        raise ValueError(f"{technique} 需要明确的视线、时空或动作提示（最多 240 字）")
    if any(not isinstance(shot.get("content"), str) or not shot["content"].strip() for shot in shots):
        raise ValueError("请为每个子镜头填写可绘制的内容")
    if any(right-left < 18 or bottom-top < 14 for left, top, right, bottom in boxes):
        raise ValueError("子镜头宽度至少 18%，高度至少 14%，保证缩小时可读")
    if sum((right-left)*(bottom-top) for left, top, right, bottom in boxes) > 4000:
        raise ValueError("子镜头合计不得超过外格 40%，需保留明确主画面")
    if len(boxes) == 2:
        first, second = boxes
        if overlaps(first, second):
            raise ValueError("格内子镜头不得相互遮挡")
        # Row-first reading with left-to-right order within a shared row.
        if (first[1] >= second[3] or
                (first[1] < second[3] and second[1] < first[3] and first[0] >= second[0])):
            raise ValueError("连续动作子镜头应按从上到下、同排从左到右排列")
    protected = composition.get("lettering_keep_clear") or []
    if isinstance(protected, list):
        for region in protected:
            try:
                keep_clear = rectangle(region)
            except ValueError:
                continue
            if any(overlaps(box, keep_clear) for box in boxes):
                raise ValueError("子镜头覆盖了主画面的脸、手或关键道具保护区")
    return {
        "technique": technique,
        "cue": cue,
        "direction": guide,
        "insets_in_reading_order": shots,
        "frame": "单一外框，主画面占主导。只在指定区域绘制有清楚边界的小镜头，保留对白空间。保持大小层级，画面文字留给排字。相同角色只可在标明为另一视点、时刻或地点的镜头中再出现，避免画成同场分身。",
    }


def validate_storyboard_subshots(board):
    for panel in board["panels"]:
        try:
            subshot_directive(panel["composition"])
        except ValueError as error:
            raise ValueError(f"第 {panel['index'] + 1} 格：{error}") from error
