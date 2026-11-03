"""Deterministic protocol/artifact/recovery tests; never call a real model."""
import asyncio
import base64
import io
import json
from copy import deepcopy
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.tools.codex_rpc import AppServer,generated_image
from app.tools.media import save_image_bytes


def png(color='blue'):
    stream=io.BytesIO();Image.new('RGB',(40,40),color).save(stream,format='PNG');return stream.getvalue()


def test_only_typed_generation_artifacts_are_imported(tmp_path):
    path=tmp_path/'image.png';path.write_bytes(png())
    item={'type':'imageGeneration','status':'completed','savedPath':str(path)}
    assert generated_image(item,'synthetic',tmp_path)==png()
    for changed in [{**item,'type':'agentMessage'},{**item,'status':'failed'},{**item,'failure':{'type':'usageLimitExceeded'}}]:
        with pytest.raises(ValueError):generated_image(changed,'synthetic',tmp_path)
    outside=tmp_path.parent/'outside.png';outside.write_bytes(png())
    with pytest.raises(ValueError):generated_image({**item,'savedPath':str(outside)},'synthetic',tmp_path)
    assert generated_image({'type':'imageGeneration','status':'completed','result':base64.b64encode(png()).decode()},'synthetic',tmp_path)==png()


def test_native_turn_consumes_events_and_isolates_other_threads(monkeypatch,tmp_path):
    import app.tools.codex_rpc as module
    monkeypatch.setattr(module,'DATA',tmp_path)
    reference=tmp_path/'outside-run-reference.png';reference.write_bytes(png())
    working=[]
    client=AppServer();monkeypatch.setattr(client,'ensure',lambda:None)
    monkeypatch.setattr(client,'account',lambda:{'logged_in':True,'image_tool_declared':True})
    def request(method,params=None,timeout=30):
        if method=='thread/start':
            assert params['sandbox']=='workspace-write'
            working.append(params['cwd']);return {'thread':{'id':'test-thread'}}
        if method=='turn/start':
            image_path=Path(params['input'][1]['path'])
            assert image_path.is_relative_to(Path(working[0])) and image_path.read_bytes()==reference.read_bytes()
            for e in [
              {'method':'item/completed','params':{'threadId':'other-thread','item':{'type':'imageGeneration','status':'completed','savedPath':'not-allowed'}}},
              {'method':'item/completed','params':{'threadId':'test-thread','item':{'type':'imageGeneration','status':'completed','result':base64.b64encode(png()).decode()}}},
              {'method':'turn/completed','params':{'threadId':'test-thread','turn':{'id':'test-turn','status':'completed'}}}]:client.messages.put(e)
            return {'turn':{'id':'test-turn'}}
    monkeypatch.setattr(client,'request',request)
    raw,usage=client.invoke('Synthetic image probe',[reference],True)
    assert raw==png() and not client.active
    assert json.loads(next(tmp_path.rglob('receipt.json')).read_text())['transport']=='app_server'


def test_interrupted_panels_checkpoint_and_reuse_only_matching_requests(monkeypatch):
    from app.agents.panel_designer import PanelDesignerAgent
    from app.services.phase_progress import panel_progress
    calls=[];snapshots=[];fail=[True]
    agent=PanelDesignerAgent()
    async def generate(prompt,reference_images=None,generation_context=None):
        index=generation_context['panel']['index'];calls.append(index)
        if index==2 and fail[0]:fail[0]=False;raise ValueError('synthetic interruption')
        return save_image_bytes(png(['red','green','blue'][index]))
    monkeypatch.setattr(agent.image_gen,'generate_image',generate)
    board={'panels':[{'index':i,'action':'同一场景'+str(i)} for i in range(3)]}
    async def checkpoint(panels):snapshots.append(deepcopy(panels))
    async def run():
        token=panel_progress.set(checkpoint)
        try:
            with pytest.raises(ValueError):await agent.generate_panels(board)
            assert len(snapshots[-1])==2
            result=await agent.generate_panels(board,previous=snapshots[-1])
            assert calls==[0,1,2,2] and sum(p.get('reused_on_resume',False) for p in result)==2
            changed=deepcopy(board);changed['panels'][0]['action']='新的构图'
            before=len(calls);await agent.generate_panels(changed,previous=result)
            assert calls[before]==0
        finally:panel_progress.reset(token)
    asyncio.run(run())


def test_review_cache_invalidates_changed_image_and_identity(monkeypatch):
    from app.agents.style_reviewer import StyleReviewerAgent
    agent=StyleReviewerAgent();calls=[]
    async def review(images,prompt):calls.append(images);return {'passed':True,'score':95,'issues':[]}
    monkeypatch.setattr(agent.llm_client,'review_images',review)
    panels=[{'index':i,'image_url':save_image_bytes(png(c)),'prompt':'synthetic'} for i,c in enumerate(['red','green','blue','white'])]
    async def run():
        first=await agent.review_panels(panels);assert len(calls)==4
        second=await agent.review_panels(panels,previous_reviews=first['panel_reviews']);assert len(calls)==4
        changed=deepcopy(panels);changed[3]['image_url']=save_image_bytes(png('black'))
        third=await agent.review_panels(changed,previous_reviews=second['panel_reviews']);assert len(calls)==5
        assert sum(r.get('reused_review',False) for r in third['panel_reviews'])==3
        await agent.review_panels(changed,characters=[{'reference_image_url':save_image_bytes(png('yellow'))}],previous_reviews=third['panel_reviews'])
        assert len(calls)==9
    asyncio.run(run())


def test_old_manual_handoff_can_continue_automatically_without_fake_reply(monkeypatch, legacy_handoff_fixture):
    from tests.test_studio_workflow import pending,task
    from app.tools.llm_client import LLMClient
    from app.tools.desktop_bridge import read_job
    monkeypatch.setattr(settings,'AI_PROVIDER','chatgpt_desktop')
    monkeypatch.setattr(settings,'IMAGE_PROVIDER','chatgpt_desktop')
    async def automatic(self,prompt):
        if '"title": "StoryboardSchema"' in prompt:return {'panels':[{'index':0,'shot_type':'中景','perspective':'平视','composition':{},'action':'递钥匙'}],'layout_type':'条漫'}
        if '"title": "DialogueSchema"' in prompt:return {'bubbles':[]}
        return {'title':'自动继续','world_view':'书店','outline':[{'event':'递钥匙'}],'characters':[]}
    with TestClient(app) as c:
        pid=c.post('/api/projects',json={'name':'自动继续测试'}).json()['id']
        cid=c.post('/api/projects/'+pid+'/chapters',json={'title':'自动继续'}).json()['id']
        c.post('/api/tasks/generate-chapter',json={'project_id':pid,'chapter_id':cid})
        old,job=pending(c,cid)
        assert c.post('/api/tasks/'+old['id']+'/continue-automatic').status_code==409
        monkeypatch.setattr(settings,'AI_PROVIDER','codex_cli');monkeypatch.setattr(LLMClient,'generate_json',automatic)
        assert c.post('/api/tasks/'+old['id']+'/continue-automatic',headers={'Origin':'https://evil.example'}).status_code==403
        r=c.post('/api/tasks/'+old['id']+'/continue-automatic');assert r.status_code==200,r.text
        current,next_job=pending(c,cid)
        assert next_job['kind']=='image' and current['result']['state']['outline']['title']=='自动继续'
        assert read_job(job['id'])['status']=='superseded' and 'response' not in read_job(job['id'])


def test_setup_verifies_all_capabilities_before_enable_and_account_changes_invalidate(monkeypatch,tmp_path):
    from app.api.routes import codex_connection as route
    from app.tools import codex_connector
    from app.tools.codex_rpc import client
    from app.core import paths
    for name in ['AI_PROVIDER','IMAGE_PROVIDER','CODEX_MODEL','IMAGE_EDIT_PROVIDER']:
        monkeypatch.setattr(settings,name,getattr(settings,name))
    monkeypatch.setattr(settings,'IMAGE_PROVIDER','chatgpt_desktop')
    monkeypatch.setattr(settings,'CODEX_MODEL','synthetic-setup')
    monkeypatch.setattr(paths,'ROOT',tmp_path)
    monkeypatch.setattr(client,'account_signature','synthetic-account-A')
    monkeypatch.setattr(client,'account',lambda:{'logged_in':True})
    calls=[]
    async def execute(prompt,images=None,image_output=False):
        calls.append(image_output)
        if image_output:return png()
        return '{"color":"red","shape":"circle"}' if images else '{"ok":true}'
    monkeypatch.setattr(codex_connector,'execute',execute)
    with TestClient(app) as c:
        assert c.post('/api/codex/verify',json={'acknowledge_usage':False}).status_code==422
        assert not calls
        assert c.post('/api/codex/enable',json={'include_images':True}).status_code==409
        r=c.post('/api/codex/verify',json={'acknowledge_usage':True,'include_images':True});assert r.status_code==200,r.text
        assert r.json()['all_passed'] and calls==[False,False,True]
        assert c.post('/api/codex/enable',json={'include_images':True}).status_code==200
        assert settings.AI_PROVIDER=='codex_cli' and settings.IMAGE_PROVIDER=='codex_cli'
        monkeypatch.setattr(client,'account_signature','synthetic-account-B')
        assert c.post('/api/codex/enable',json={'include_images':True}).status_code==409


def test_setup_image_failure_keeps_existing_configuration(monkeypatch,tmp_path):
    from app.tools import codex_connector
    from app.tools.codex_rpc import client
    from app.core import paths
    monkeypatch.setattr(paths,'ROOT',tmp_path)
    for name in ['AI_PROVIDER','IMAGE_PROVIDER','CODEX_MODEL']:monkeypatch.setattr(settings,name,getattr(settings,name))
    monkeypatch.setattr(settings,'CODEX_MODEL','synthetic-failed-image')
    monkeypatch.setattr(settings,'IMAGE_PROVIDER','chatgpt_desktop')
    monkeypatch.setattr(client,'account_signature','synthetic-failure-account')
    monkeypatch.setattr(client,'account',lambda:{'logged_in':True})
    async def execute(prompt,images=None,image_output=False):
        if image_output:raise ValueError('synthetic image failure')
        return '{"color":"red","shape":"circle"}' if images else '{"ok":true}'
    monkeypatch.setattr(codex_connector,'execute',execute)
    with TestClient(app) as c:
        r=c.post('/api/codex/verify',json={'acknowledge_usage':True});assert not r.json()['all_passed']
        assert settings.IMAGE_PROVIDER=='chatgpt_desktop'
        assert c.post('/api/codex/enable',json={'include_images':True}).status_code==409
        assert c.post('/api/codex/enable',json={'include_images':False}).status_code==200
        assert settings.IMAGE_PROVIDER=='chatgpt_desktop'


def test_app_server_reuses_warm_process_and_disables_external_tools(monkeypatch):
    from app.tools import codex_connector
    import app.tools.codex_rpc as module
    client=AppServer();starts=[]
    monkeypatch.setattr(codex_connector,'identity',lambda:'synthetic-binary')
    monkeypatch.setattr(codex_connector,'command',lambda:['/synthetic/codex'])
    class Proc:
        stdin=None;stdout=None
        def __init__(self,args,**kwargs):starts.append(args)
        def poll(self):return None
    monkeypatch.setattr(module.subprocess,'Popen',Proc)
    monkeypatch.setattr(client,'_pump',lambda *args:None)
    monkeypatch.setattr(client,'_send',lambda *args:None)
    monkeypatch.setattr(client,'close',lambda:setattr(client,'proc',None))
    def request(method,params=None,timeout=30):
        if method=='modelProvider/capabilities/read':return {'imageGeneration':True}
        if method=='mcpServerStatus/list':return {'data':[{'name':'synthetic_server','tools':{'fake':{}} if len(starts)==1 else {},'resources':[],'resourceTemplates':[]}]}
        return {}
    monkeypatch.setattr(client,'request',request)
    client.ensure();assert len(starts)==2
    assert 'mcp_servers.synthetic_server.enabled=false' in starts[-1]
    client.ensure();assert len(starts)==2


def test_native_timeout_closes_transport_without_replaying_turn(monkeypatch,tmp_path):
    import app.tools.codex_rpc as module
    monkeypatch.setattr(module,'DATA',tmp_path)
    client=AppServer();requests=[];closed=[]
    monkeypatch.setattr(client,'ensure',lambda:None)
    monkeypatch.setattr(client,'account',lambda:{'logged_in':True,'image_tool_declared':True})
    def request(method,params=None,timeout=30):
        requests.append(method)
        return {'thread':{'id':'synthetic-thread'}} if method=='thread/start' else {'turn':{'id':'synthetic-turn'}}
    monkeypatch.setattr(client,'request',request)
    def receive(timeout):raise TimeoutError('synthetic timeout')
    monkeypatch.setattr(client,'_receive',receive);monkeypatch.setattr(client,'close',lambda:closed.append(True))
    with pytest.raises(ValueError,match='超时'):client.invoke('synthetic',[])
    assert requests.count('turn/start')==1 and closed and not client.active


def test_unit_suite_cannot_spend_native_account_quota():
    from app.tools.codex_rpc import client
    with pytest.raises(AssertionError,match='must mock'):
        client.invoke('This must not reach a real model',[])
    import httpx
    async def request():
        async with httpx.AsyncClient() as c:await c.get('https://unit-test.invalid')
    with pytest.raises(AssertionError,match='must mock'):
        asyncio.run(request())


def test_retired_provider_does_not_create_new_handoff():
    from app.tools.desktop_bridge import list_jobs
    with TestClient(app) as c:
        pid=c.post('/api/projects',json={'name':'Retired provider regression'}).json()['id']
        cid=c.post('/api/projects/'+pid+'/chapters',json={'title':'Test'}).json()['id']
        created=c.post('/api/tasks/generate-chapter',json={'project_id':pid,'chapter_id':cid}).json()
        latest=c.get('/api/studio/chapters/'+cid+'/task').json()
        assert latest['status']=='failed' and '人工回填模式已停用' in latest['error_message']
        assert not list_jobs(created['id'])
