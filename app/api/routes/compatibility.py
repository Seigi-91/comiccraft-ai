"""Explicit, one-request provider probes; never run automatically on page load."""
import asyncio
import hashlib
import json
from io import BytesIO
from typing import Literal
from uuid import uuid4
import httpx
from PIL import Image,ImageDraw
from pydantic import BaseModel
from fastapi import APIRouter,Depends,Request,HTTPException
from sqlalchemy import select
from app.api.local_access import require_local_settings
from app.core.config import settings
from app.db.session import get_db
from app.models.orm import ProviderVerification,ModelCall
from app.tools.desktop_bridge import task_context

router=APIRouter()
probe_lock=asyncio.Lock()


def connection(kind):
    provider = settings.AI_PROVIDER if kind in {'text','vision'} else settings.IMAGE_EDIT_PROVIDER if kind=='mask' else settings.image_provider
    if provider == 'codex_cli':
        from app.tools.codex_connector import verification_identity
        return provider,verification_identity(),settings.CODEX_MODEL or 'CLI default',None
    if kind in {'text','vision'}:
        return settings.AI_PROVIDER,settings.LOCAL_GPT_BASE_URL,settings.DEFAULT_VISION_MODEL if kind=='vision' else settings.DEFAULT_TEXT_MODEL,settings.LOCAL_GPT_API_KEY
    if kind=='mask':return settings.IMAGE_EDIT_PROVIDER,settings.IMAGE_EDIT_BASE_URL,settings.IMAGE_EDIT_MODEL,settings.IMAGE_EDIT_API_KEY
    return settings.image_provider,settings.IMAGE_API_BASE_URL if settings.IMAGE_PROVIDER else settings.LOCAL_GPT_BASE_URL,settings.IMAGE_API_MODEL if settings.IMAGE_PROVIDER else settings.DEFAULT_IMAGE_MODEL,settings.IMAGE_API_KEY if settings.IMAGE_PROVIDER else settings.LOCAL_GPT_API_KEY


def fingerprint(kind):
    return hashlib.sha256(json.dumps(connection(kind),ensure_ascii=False).encode()).hexdigest()


class Probe(BaseModel):
    kind: Literal['text','vision','image','reference','mask']
    acknowledge_cost: bool = False


@router.post('/probe')
async def probe(data:Probe,request:Request,db=Depends(get_db)):
    require_local_settings(request)
    if not data.acknowledge_cost:raise HTTPException(422,'请先确认：这会向配置的服务发送一次可能付费的真实请求。')
    provider,base,model,key=connection(data.kind)
    if provider=='chatgpt_desktop':return {'status':'handoff','detail':'旧人工回填连接已停用，请切换到官方连接器或模型 API。','model_requests':0}
    if probe_lock.locked():raise HTTPException(409,'已有验证正在执行，请稍后再试。')
    async with probe_lock:
        from app.tools.llm_client import LLMClient,VisionLLMClient
        from app.tools.image_gen import ImageGeneratorClient
        from app.tools.media import save_image_bytes
        from app.services.inpainting import edit_image
        token=task_context.set('probe:'+uuid4().hex)
        config_hash=fingerprint(data.kind)
        try:
            stream=BytesIO();im=Image.new('RGB',(1024,1024),'white');ImageDraw.Draw(im).ellipse((300,300,700,700),fill='red');im.save(stream,format='PNG')
            reference=save_image_bytes(stream.getvalue())
            if data.kind=='text':
                await LLMClient().generate_json('Connection test. Return only a JSON object: {"ok": true}.')
            elif data.kind=='vision':
                await VisionLLMClient().review_image(reference,'Describe the attached image briefly. Return only a JSON object with a description field.')
            elif data.kind=='mask':
                mask=Image.new('RGB',(1024,1024),'black');ImageDraw.Draw(mask).rectangle((350,350,600,600),fill='white');stream=BytesIO();mask.save(stream,format='PNG')
                await edit_image(reference,save_image_bytes(stream.getvalue()),'将选区内的红色改为蓝色。')
            else:
                await ImageGeneratorClient()._generate_image('A simple blue circle on a white background. No text.','',1024,1024,'flat', [reference] if data.kind=='reference' else [])
            status='passed';detail='真实接口返回了可解析的 JSON 或图片；不代表画质、语义正确性或未来可用性。'
        except httpx.HTTPStatusError as error:
            status='failed';detail=f'接口 HTTP {error.response.status_code}；请检查模型、权限、额度与协议。'
        except ValueError as error:
            status='failed';detail=str(error) if provider=='codex_cli' else '返回格式或能力校验失败，请检查服务模型与协议。'
        except Exception as error:
            status='failed';detail='验证失败（'+type(error).__name__+'）；请检查地址、模型能力、网络及响应格式。'
        finally:task_context.reset(token)
        row=ProviderVerification(id=uuid4().hex,kind=data.kind,model=model,fingerprint=config_hash,status=status,detail=detail)
        db.add(row);await db.commit()
        return {'id':row.id,'kind':row.kind,'status':status,'detail':detail,'model':model,'checked_at':row.created_at}


@router.get('/verifications')
async def verifications(db=Depends(get_db)):
    rows=(await db.execute(select(ProviderVerification).order_by(ProviderVerification.created_at.desc()).limit(30))).scalars()
    return [{'id':r.id,'kind':r.kind,'model':r.model,'status':r.status,'detail':r.detail,'checked_at':r.created_at,'matches_current_config':r.fingerprint==fingerprint(r.kind)} for r in rows]


@router.get('/usage/{task_id}')
async def usage(task_id:str,db=Depends(get_db)):
    rows=list((await db.execute(select(ModelCall).where(ModelCall.task_id==task_id).order_by(ModelCall.created_at))).scalars())
    return {'task_id':task_id,'limit':settings.MAX_MODEL_REQUESTS_PER_TASK,'reserved':len(rows),'currency_cost':None,
            'note':'请求预留数是保守上限，不等于成功次数或账单金额。中断请求可能已被服务计费。',
            'calls':[{'kind':r.kind,'model':r.model,'stage':r.stage,'status':r.status,'usage':r.usage,'error':r.error,'created_at':r.created_at} for r in rows]}
