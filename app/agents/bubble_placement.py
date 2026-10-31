import json
from copy import deepcopy
from pydantic import BaseModel, Field, model_validator
from app.models.schemas import BubblePosition, BubbleSize
from app.tools.llm_client import VisionLLMClient
from app.tools.desktop_bridge import stage_context
from app.core.paths import ROOT


class Region(BaseModel):
    kind: str
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    width: float = Field(gt=0, le=100)
    height: float = Field(gt=0, le=100)

    @model_validator(mode="after")
    def bounds(self):
        if self.x+self.width > 100 or self.y+self.height > 100:
            raise ValueError("保护区域超出画面")
        return self


class Placement(BaseModel):
    id: int
    position: BubblePosition
    size: BubbleSize
    tail: BubblePosition


class PlacementPlan(BaseModel):
    fits: bool
    reason: str
    regions: list[Region] = Field(max_length=100)
    placements: list[Placement] = Field(max_length=100)


def validate_plan(plan, bubbles):
    if not plan.fits:
        raise ValueError("视觉定位需要人工调整："+plan.reason)
    ids = [p.id for p in plan.placements]
    if sorted(ids) != sorted(bubbles):
        raise ValueError("定位结果必须完整且不重复引用全部台词")
    boxes=[]
    for p in plan.placements:
        x,y=p.position.x-p.size.width/2,p.position.y-p.size.height/2
        box=(x,y,x+p.size.width,y+p.size.height)
        if min(box)<0 or box[2]>100 or box[3]>100:
            raise ValueError("气泡超出画面")
        obstacles=boxes+[(r.x-1,r.y-1,r.x+r.width+1,r.y+r.height+1) for r in plan.regions]
        if any(box[0]<r[2] and box[2]>r[0] and box[1]<r[3] and box[3]>r[1] for r in obstacles):
            raise ValueError("气泡覆盖保护区域或其他气泡，请重新定位")
        boxes.append(box)


async def place_bubbles(state):
    dialogues=deepcopy(state.get('dialogues') or {'bubbles':[]})
    evidence=[]
    skill=(ROOT/'skills/bubble-placement/SKILL.md').read_text(encoding='utf-8')
    for panel in state['panels']:
        bubbles={i:b for i,b in enumerate(dialogues['bubbles']) if b['panel_index']==panel['index'] and b['text'].strip()}
        if not bubbles:
            continue
        prompt=skill+'\n输出 Schema：'+json.dumps(PlacementPlan.model_json_schema(),ensure_ascii=False)+'\n台词（id 不得改变）：'+json.dumps(bubbles,ensure_ascii=False)
        token=stage_context.set('bubble_placement:'+str(panel['index']))
        try:
            plan=PlacementPlan.model_validate(await VisionLLMClient().review_images([panel['image_url']],prompt))
        finally:
            stage_context.reset(token)
        validate_plan(plan,bubbles)
        for p in plan.placements:
            dialogues['bubbles'][p.id].update(position=p.position.model_dump(),size=p.size.model_dump(),tail=p.tail.model_dump())
        evidence.append({'panel_index':panel['index'],**plan.model_dump()})
    return {'dialogues':dialogues,'bubble_placement_report':evidence,'phase':'layout'}
