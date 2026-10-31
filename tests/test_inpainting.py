import asyncio
import io
import base64
from uuid import uuid4
import httpx
from PIL import Image, ImageChops
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import AsyncSessionLocal
from app.models.orm import Panel,Task,TaskStatus,Phase,PanelStatus,Chapter
from app.tools.media import save_image_bytes,local_image_path
from app.core.config import settings
from app.services.inpainting import edit_image


def image_bytes(color):
    out=io.BytesIO();Image.new('RGB',(128,128),color).save(out,'PNG');return out.getvalue()


async def seed(cid,pid,url):
    async with AsyncSessionLocal() as db:
        chapter=await db.get(Chapter,cid);chapter.phase=Phase.COMPLETED;chapter.dialogues={'bubbles':[]}
        db.add(Panel(id=str(uuid4()),chapter_id=cid,index=0,image_url=url,status=PanelStatus.PASSED))
        db.add(Task(id=str(uuid4()),chapter_id=cid,project_id=pid,type='test',status=TaskStatus.COMPLETED,result={'state':{'panels':[{'index':0,'image_url':url,'status':'passed'}],'dialogues':{'bubbles':[]},'phase':'completed'}}))
        await db.commit()


def test_desktop_repair_mask_compare_accept_and_restore():
    with TestClient(app) as c:
        p=c.post('/api/projects',json={'name':'局部精修测试'}).json()
        ch=c.post(f"/api/projects/{p['id']}/chapters",json={'title':'第一格'}).json();cid=ch['id']
        url=save_image_bytes(image_bytes('red'));asyncio.run(seed(cid,p['id'],url))
        root='/api/repairs/'+cid
        polygons=[[{'x':30,'y':30},{'x':60,'y':30},{'x':60,'y':60},{'x':30,'y':60}]]
        invalid=c.post(root+'/panels/0',json={'instructions':'修手','source_url':url,'polygons':[[{'x':0,'y':0},{'x':100,'y':0},{'x':100,'y':100},{'x':0,'y':100}]]})
        assert invalid.status_code==422
        r=c.post(root+'/panels/0',json={'instructions':'修正手指','source_url':url,'polygons':polygons});assert r.status_code==200,r.text
        repair=c.get(root).json()[0];assert repair['status']=='waiting'
        assert repair['job']['images']==[url,repair['mask_url']]
        candidate_input=save_image_bytes(image_bytes('blue'))
        r=c.post(root+'/'+repair['id']+'/reply',json={'image_url':candidate_input});assert r.status_code==200,r.text
        candidate=Image.open(local_image_path(r.json()['candidate_url'])).convert('RGB')
        original=Image.open(local_image_path(url)).convert('RGB');mask=Image.open(local_image_path(repair['mask_url'])).convert('L')
        diff=ImageChops.difference(candidate,original)
        assert Image.composite(diff,Image.new('RGB',diff.size),ImageChops.invert(mask)).getbbox() is None
        assert candidate.getpixel((50,50))==(0,0,255)
        assert c.get(f"/api/projects/{p['id']}/chapters/{cid}").json()['panels'][0]['image_url']==url
        r=c.post(root+'/'+repair['id']+'/accept',json={'expected_version':None});assert r.status_code==200,r.text
        assert c.get(f"/api/projects/{p['id']}/chapters/{cid}").json()['panels'][0]['image_url']!=url
        versions=c.get('/api/editing/'+cid+'/versions').json();before=next(v for v in versions if v['label']=='采用局部精修前')
        restored=c.post('/api/editing/'+cid+'/versions/'+before['id']+'/restore',json={'expected_version':versions[0]['id']});assert restored.status_code==200
        assert c.get(f"/api/projects/{p['id']}/chapters/{cid}").json()['panels'][0]['image_url']==url
        assert c.post(root+'/'+repair['id']+'/accept',json={'expected_version':None}).status_code==409


def test_http_edits_contract_and_outside_mask_preservation(monkeypatch):
    from app.services import inpainting
    original_client=httpx.AsyncClient
    def transport(request):
        assert request.url.path=='/v1/images/edits'
        body=request.read()
        assert b'name="mask"' in body and b'name="image"' in body
        boundary=request.headers['content-type'].split('boundary=')[1].encode()
        mask_part=next(part for part in body.split(b'--'+boundary) if b'filename="mask.png"' in part)
        mask_bytes=mask_part.split(b'\r\n\r\n',1)[1][:-2]
        alpha=Image.open(io.BytesIO(mask_bytes)).getchannel('A')
        assert alpha.getpixel((0,0))==255 and alpha.getpixel((60,45))==0
        assert b'gpt-image-1' in body and request.headers['authorization']=='Bearer test-only'
        return httpx.Response(200,json={'data':[{'b64_json':base64.b64encode(image_bytes('blue')).decode()}]})
    monkeypatch.setattr(inpainting.httpx,'AsyncClient',lambda **kwargs:original_client(transport=httpx.MockTransport(transport)))
    monkeypatch.setattr(settings,'IMAGE_EDIT_BASE_URL','http://test/v1');monkeypatch.setattr(settings,'IMAGE_EDIT_API_KEY','test-only')
    source=save_image_bytes(image_bytes('red'))
    mask=inpainting.create_mask(source,[[{'x':30,'y':30},{'x':60,'y':30},{'x':60,'y':60}]])
    result=asyncio.run(edit_image(source,mask,'fix hand'))
    image=Image.open(local_image_path(result));assert image.getpixel((0,0))==(255,0,0)


def test_candidate_resize_requires_explicit_opt_in():
    import pytest
    from app.services.inpainting import create_mask,composite_candidate
    source=save_image_bytes(image_bytes('red'))
    mask=create_mask(source,[[{'x':20,'y':20},{'x':60,'y':20},{'x':60,'y':60}]])
    output=io.BytesIO();Image.new('RGB',(64,64),'blue').save(output,'PNG')
    with pytest.raises(ValueError):composite_candidate(source,mask,output.getvalue())
    candidate=composite_candidate(source,mask,output.getvalue(),allow_resize=True)
    assert Image.open(local_image_path(candidate)).size==(128,128)
    assert Image.open(local_image_path(candidate)).getpixel((0,0))==(255,0,0)
