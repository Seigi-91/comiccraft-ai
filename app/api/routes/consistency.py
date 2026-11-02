from uuid import uuid4
import hashlib,json
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,model_validator
from sqlalchemy import select
from app.db.session import get_db
from app.models.orm import Panel,ConsistencyEvaluation
from app.services.production_records import asset_hash

router=APIRouter()
DIMENSIONS=['identity','outfit','hands','props','space','lettering']


class PanelScore(BaseModel):
    index:int=Field(ge=0)
    scores:dict[str,int|None]

    @model_validator(mode='after')
    def valid(self):
        if set(self.scores)!=set(DIMENSIONS) or any(v is not None and v not in {0,1,2} for v in self.scores.values()):
            raise ValueError('六个维度须完整，分数只能为0/1/2或未知')
        return self


class Evaluation(BaseModel):
    hashes:dict[str,str]
    panels:list[PanelScore]=Field(min_length=1,max_length=24)
    notes:str=Field(default='',max_length=4000)


def summarize(scores):
    values=[v for p in scores for v in p['scores'].values() if v is not None]
    total=len(scores)*len(DIMENSIONS)
    percent=round(sum(values)/len(values)/2*100,1) if values else None
    return {'coverage':round(len(values)/total*100,1) if total else 0,'percent':percent,'passed':len(values)==total and bool(values) and 0 not in values and percent>=80,'method':'human_rubric','currency_cost':None}


async def current(db,chapter_id):
    rows=list((await db.execute(select(Panel).where(Panel.chapter_id==chapter_id).order_by(Panel.index))).scalars())
    hashes={str(p.index):asset_hash(p.image_url) or '' for p in rows}
    from app.api.routes.editing import context
    chapter,tasks=await context(db,chapter_id)
    state=(tasks[0].result or {}).get('state',{}) if tasks else {}
    hashes['_lettering']=hashlib.sha256(json.dumps({'dialogues':state.get('dialogues') or chapter.dialogues,'effects':state.get('effects',{})},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return rows,hashes


@router.get('/chapters/{chapter_id}/consistency')
async def reports(chapter_id:str,db=Depends(get_db)):
    from app.api.routes.editing import context
    await context(db,chapter_id)
    panels,hashes=await current(db,chapter_id)
    rows=(await db.execute(select(ConsistencyEvaluation).where(ConsistencyEvaluation.chapter_id==chapter_id).order_by(ConsistencyEvaluation.created_at.desc()))).scalars()
    return {'dimensions':DIMENSIONS,'hashes':hashes,'panels':[{'index':p.index,'image_url':p.image_url} for p in panels],
            'reports':[{'id':r.id,'scores':r.scores,'notes':r.notes,'created_at':r.created_at,'matches_current_images':r.snapshot['hashes']==hashes,**summarize(r.scores)} for r in rows]}


@router.post('/chapters/{chapter_id}/consistency')
async def evaluate(chapter_id:str,payload:Evaluation,db=Depends(get_db)):
    from app.api.routes.editing import context
    chapter,tasks=await context(db,chapter_id)
    panels,hashes=await current(db,chapter_id)
    if not panels or not all(hashes.values()) or payload.hashes!=hashes:raise HTTPException(409,'图片已变化或不可读，请刷新后按当前图像评测')
    if sorted(p.index for p in payload.panels)!=[p.index for p in panels]:raise HTTPException(422,'须为每格提供一次且仅一次评测')
    scores=[p.model_dump() for p in payload.panels]
    task=tasks[0] if tasks else None
    row=ConsistencyEvaluation(id=uuid4().hex,chapter_id=chapter_id,snapshot={'hashes':hashes,'task_id':task.id if task else None,'origin':'human_rubric','recorded_parameters':'see task production records; unknown is not zero'},scores=scores,notes=payload.notes)
    db.add(row);await db.commit()
    return {'id':row.id,**summarize(scores)}
