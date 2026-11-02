import asyncio
from fastapi import APIRouter, Request
from app.api.local_access import require_local_settings
from app.tools.codex_connector import status
router=APIRouter()


@router.get("/status")
async def connection_status(request:Request):
    require_local_settings(request)
    return await asyncio.to_thread(status)


@router.get("/installer")
async def installer():
    import io, zipfile
    from fastapi.responses import Response
    from app.core.paths import ROOT
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as archive:
        for name in ["Install-Codex-Connector.cmd","scripts/install_codex.ps1","scripts/install_codex.sh"]:
            text=(ROOT/name).read_text(encoding="utf-8")
            if name.endswith((".cmd",".ps1")):text=text.replace("\r\n","\n").replace("\n","\r\n")
            archive.writestr(name,text.encode("utf-8"))
        archive.writestr("README.txt","Unzip first. Windows: double-click Install-Codex-Connector.cmd. Requires Node.js 20+. Installs official @openai/codex and opens its ChatGPT login. No app keys or account credentials are in this package. macOS/Linux: bash scripts/install_codex.sh. Then refresh website status and explicitly test capabilities.")
    return Response(buffer.getvalue(),media_type="application/zip",headers={"Content-Disposition":'attachment; filename="ComicCraft-Codex-Connector.zip"'})


@router.get("/account")
async def account(request:Request):
    require_local_settings(request)
    from app.tools.codex_rpc import client
    if client.active:return {"busy":True,"model_requests":0}
    try:return await asyncio.to_thread(client.account)
    except (ValueError,TimeoutError,OSError):return {"logged_in":False,"detail":"官方连接未就绪，请安装连接器或重试检查","model_requests":0}


@router.post("/login")
async def login(request:Request):
    require_local_settings(request)
    from app.tools.codex_rpc import client
    from app.api.routes.tasks import active_tasks
    from fastapi import HTTPException
    from app.api.routes.compatibility import probe_lock
    if client.active or active_tasks or probe_lock.locked():raise HTTPException(409,"任务执行中，请完成后再登录")
    try:return await asyncio.to_thread(client.start_login)
    except (ValueError,TimeoutError,OSError) as error:raise HTTPException(422,str(error))


@router.post("/login/cancel")
async def cancel_login(request:Request):
    require_local_settings(request)
    from app.tools.codex_rpc import client
    from fastapi import HTTPException
    from app.api.routes.compatibility import probe_lock
    if client.active or probe_lock.locked():raise HTTPException(409,"任务执行中，请稍后再试")
    return await asyncio.to_thread(client.cancel_login)


from pydantic import BaseModel
from fastapi import Depends,HTTPException
from app.db.session import get_db


class VerifySetup(BaseModel):
    include_images:bool=True
    acknowledge_usage:bool=False


class EnableSetup(BaseModel):
    include_images:bool=True


def codex_fingerprint():
    import hashlib,json
    from app.tools.codex_connector import verification_identity
    from app.core.config import settings
    return hashlib.sha256(json.dumps(('codex_cli',verification_identity(),settings.CODEX_MODEL or 'CLI default',None),ensure_ascii=False).encode()).hexdigest()


@router.post("/verify")
async def verify_setup(data:VerifySetup,request:Request,db=Depends(get_db)):
    require_local_settings(request)
    if not data.acknowledge_usage:raise HTTPException(422,"请确认：验证会消耗本人的模型额度")
    from app.api.routes.compatibility import probe_lock
    from app.api.routes.tasks import active_tasks
    from app.tools.codex_rpc import client
    if active_tasks or client.active or probe_lock.locked():raise HTTPException(409,"已有任务或验证进行中")
    from app.tools.codex_connector import execute
    from app.tools.llm_client import parse_json
    from app.tools.media import save_image_bytes
    from app.tools.desktop_bridge import task_context
    from app.services.model_budget import reserve,finish,reported_usage
    from app.core.config import settings
    from app.models.orm import ProviderVerification
    from PIL import Image,ImageDraw
    from io import BytesIO
    from uuid import uuid4
    async with probe_lock:
        token=task_context.set('codex-setup:'+uuid4().hex)
        results=[]
        try:
            im=Image.new('RGB',(512,512),'white');ImageDraw.Draw(im).ellipse((100,100,412,412),fill='red');stream=BytesIO();im.save(stream,format='PNG');reference=save_image_bytes(stream.getvalue())
            for kind in ['text','vision']+(['image'] if data.include_images else []):
                receipt=await reserve('codex_'+kind,settings.CODEX_MODEL or 'CLI default');usage_token=reported_usage.set(None)
                image_url=None
                try:
                    if kind=='text':
                        reply=parse_json(await execute('Connection check. Return only JSON {"ok":true}.'))
                        if reply.get('ok') is not True:raise ValueError('文字校验未返回ok=true')
                    elif kind=='vision':
                        reply=parse_json(await execute('Inspect this test image. Return JSON with color and shape as short English words. Do not generate an image.',[reference]))
                        if reply.get('color','').lower()!='red' or reply.get('shape','').lower()!='circle':raise ValueError('视觉校验未识别出测试图的红色圆形')
                    else:image_url=save_image_bytes(await execute('Generate one simple blue circle centered on a white square background. No text.',image_output=True))
                    state='passed';detail='本次官方自动连接返回有效结果；不代表所有作品的质量保证'
                    await finish(receipt,'completed',reported_usage.get())
                except Exception as error:
                    state='failed';detail=str(error) if isinstance(error,ValueError) else '官方连接执行失败，请检查登录、额度与版本'
                    await finish(receipt,'failed',reported_usage.get(),type(error).__name__)
                finally:reported_usage.reset(usage_token)
                row=ProviderVerification(id=uuid4().hex,kind=kind,model=settings.CODEX_MODEL or 'CLI default',fingerprint=codex_fingerprint(),status=state,detail=detail)
                db.add(row);await db.commit()
                results.append({'kind':kind,'status':state,'detail':detail,'image_url':image_url})
                if state=='failed':break
        finally:task_context.reset(token)
        return {'results':results,'all_passed':len(results)==(3 if data.include_images else 2) and all(r['status']=='passed' for r in results),'note':'本次验证至少执行文字/视觉两项，可选生图；不是一次底层模型调用。'}


@router.post("/enable")
async def enable_setup(data:EnableSetup,request:Request,db=Depends(get_db)):
    require_local_settings(request)
    from sqlalchemy import select
    from app.models.orm import ProviderVerification
    from app.api.routes.studio import update_connection,ConnectionUpdate
    from app.core.config import settings
    from app.tools.codex_rpc import client
    account=await asyncio.to_thread(client.account)
    if not account["logged_in"]:raise HTTPException(409,"请先完成本人ChatGPT登录")
    rows=(await db.execute(select(ProviderVerification).where(ProviderVerification.fingerprint==codex_fingerprint()).order_by(ProviderVerification.created_at.desc()))).scalars()
    latest={}
    for row in rows:latest.setdefault(row.kind,row.status)
    required=['text','vision']+(['image'] if data.include_images else [])
    if not all(latest.get(kind)=='passed' for kind in required):raise HTTPException(409,"请先完成当前连接的文字、视觉及所选图片验证；不会把未验证能力自动启用")
    return await update_connection(ConnectionUpdate(text_provider='codex_cli',codex_model=settings.CODEX_MODEL,image_provider='codex_cli' if data.include_images else None,use_for_repairs=False),request)
