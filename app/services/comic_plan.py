"""Page geometry and scene references shared by planning and rendering."""
from collections import Counter
from itertools import combinations

PAGE_SIZE = (1000, 1200)


def auto_pages(panels):
    """Give a story beat a wide row and pair details with their context."""
    rows = []
    pending = None
    for panel in panels:
        role = panel["composition"].get("page_role")
        shot = panel["shot_type"].casefold()
        if role in ("anchor", "detail", "reaction", "context"):
            wide = role == "anchor"
            detail = role in ("detail", "reaction")
        else:
            wide = any(term in shot for term in ("全景", "远景", "wide", "establish"))
            detail = any(term in shot for term in ("特写", "close-up", "insert"))
        entry = (panel["index"], detail)
        if wide:
            if pending is not None:
                rows.append([pending])
                pending = None
            rows.append([entry])
        elif pending is not None:
            rows.append([pending, entry])
            pending = None
        else:
            pending = entry
    if pending is not None:
        rows.append([pending])

    pages = []
    gutter, margin = 1.6, 3.4
    for start in range(0, len(rows), 3):
        group = rows[start:start + 3]
        if len(group) == 1 and len(group[0]) == 2:
            group = [[entry] for entry in group[0]]
        available = 100 - 2 * margin - (len(group) - 1) * gutter
        # Keep a narrow detail from becoming a tall slot when paired with context.
        weights = [1.25 if len(row) == 1 else 0.85 if row[0][1] != row[1][1] else 1 for row in group]
        regions = []
        y = margin
        for row, weight in zip(group, weights):
            height = available * weight / sum(weights)
            if len(row) == 1:
                widths = [100 - 2 * margin]
            else:
                left_detail, right_detail = row[0][1], row[1][1]
                split = 0.35 if left_detail and not right_detail else 0.65 if right_detail and not left_detail else 0.5
                widths = [(100 - 2 * margin - gutter) * share for share in (split, 1 - split)]
            x = margin
            for (index, _), width in zip(row, widths):
                regions.append(dict(panel_index=index, x=round(x, 3), y=round(y, 3),
                                    width=round(width, 3), height=round(height, 3), inset_of=None))
                x += width + gutter
            y += height + gutter
        pages.append({"height": 1440 if len(group) == 3 else PAGE_SIZE[1], "regions": regions})
    return pages


def validate_pages(pages, indices):
    order = [region["panel_index"] for page in pages for region in page["regions"]]
    if order != sorted(indices):
        raise ValueError("页面须按阅读顺序覆盖每格一次")
    for page in pages:
        regions = page["regions"]
        seen = {}
        for region in regions:
            x, y, width, height = (region[key] for key in ("x", "y", "width", "height"))
            if x + width > 100 or y + height > 100:
                raise ValueError("格区超出页边")
            parent_index = region.get("inset_of")
            if parent_index is not None:
                parent = seen.get(parent_index)
                if (not parent or parent.get("inset_of") is not None
                        or x < parent["x"] or y < parent["y"]
                        or x + width > parent["x"] + parent["width"]
                        or y + height > parent["y"] + parent["height"]
                        or width * height >= parent["width"] * parent["height"]):
                    raise ValueError("插格须位于本页较早的主格内")
            seen[region["panel_index"]] = region
        for left, right in combinations(regions, 2):
            if right.get("inset_of") == left["panel_index"]:
                continue
            if (max(left["x"], right["x"]) < min(left["x"] + left["width"], right["x"] + right["width"])
                    and max(left["y"], right["y"]) < min(left["y"] + left["height"], right["y"] + right["height"])):
                raise ValueError("格区重叠，请调整坐标或显式设为插格")


def has_ambiguous_reading_order(regions):
    """Check conflicts with row-first reading in automatically drafted layouts."""
    outer = [region for region in regions if region.get("inset_of") is None]
    for earlier, later in combinations(outer, 2):
        if later["y"] + later["height"] <= earlier["y"]:
            return True
        if abs(earlier["y"] - later["y"]) <= 2 and later["x"] + later["width"] <= earlier["x"]:
            return True
    for upper, rail, lower in combinations(outer, 3):
        if (upper["y"] + upper["height"] <= lower["y"]
                and max(upper["x"] + upper["width"], lower["x"] + lower["width"]) <= rail["x"]
                and rail["y"] <= upper["y"] + 2
                and rail["y"] + rail["height"] >= lower["y"] + lower["height"] - 2):
            # Row-first indices enter the tall right panel before completing the left stack.
            return True
    return False


def needs_page_rebalance(pages, panels):
    """Repair automatic drafts with unclear navigation or weak visual hierarchy."""
    roles = {panel["index"]: panel["composition"].get("page_role") for panel in panels}
    for page in pages:
        if has_ambiguous_reading_order(page["regions"]):
            return True
        weights = {}
        for region in page["regions"]:
            role = roles.get(region["panel_index"])
            if role in ("anchor", "detail", "reaction"):
                weights.setdefault(role, []).append(region["width"] * region["height"])
        details = weights.get("detail", []) + weights.get("reaction", [])
        anchors = weights.get("anchor", [])
        if details and anchors and min(anchors) < max(details) * 1.15:
            return True
    return False


def validate_scenes(board):
    scene_ids = [scene["id"] for scene in board.get("scenes", [])]
    if len(scene_ids) != len(set(scene_ids)):
        raise ValueError("场景 ID 必须唯一")
    if any(panel.get("scene_id") and panel["scene_id"] not in scene_ids for panel in board["panels"]):
        raise ValueError("分镜引用了不存在的场景")


def effective_references(board, assets, overrides):
    """Match approved versions by exact name, then allow per-shot overrides."""
    scenes = {scene["id"]: scene for scene in board.get("scenes", [])}
    keys = [(asset["kind"], asset["name"].strip().casefold()) for asset in assets]
    counts = Counter(keys)
    lookup = {key: asset for key, asset in zip(keys, assets) if counts[key] == 1}
    bindings = {}
    for panel in board["panels"]:
        index = str(panel["index"])
        if index in overrides:
            bindings[index] = overrides[index]
            continue
        scene = scenes.get(panel.get("scene_id"))
        if not scene:
            continue
        visible = [person.get("character") for person in (panel.get("character_positions") or [])
                   if isinstance(person, dict) and person.get("character")]
        names = [("scene", scene["name"]), *[("character", name) for name in visible or scene["characters"]],
                 *[("prop", name) for name in scene["props"]]]
        selected = {}
        for kind, name in names:
            asset = lookup.get((kind, name.strip().casefold()))
            if asset:
                selected[asset["id"]] = asset
        bindings[index] = list(selected.values())[:3]
    return bindings
