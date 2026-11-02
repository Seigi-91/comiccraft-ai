import asyncio
from uuid import uuid4
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import update
from app.main import app
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.orm import TaskLease
from app.services.task_leases import claim,release,renew,now,leased_task
from app.services.model_budget import reserve,finish,RequestLimitExceeded
from app.tools.desktop_bridge import task_context


def test_request_budget_is_persistent_and_blocks_extra_call(monkeypatch):
    monkeypatch.setattr(settings,'MAX_MODEL_REQUESTS_PER_TASK',1)
    async def run():
        task='budget-test:'+uuid4().hex;token=task_context.set(task)
        try:
            first=await reserve('text','test-model');await finish(first,'failed',error='HTTPStatusError')
            try:await reserve('text','test-model')
            except RequestLimitExceeded:pass
            else:raise AssertionError('Budget did not block second reservation')
            return task
        finally:task_context.reset(token)
    with TestClient(app) as c:
        task=asyncio.run(run());r=c.get('/api/studio/usage/'+task).json()
        assert r['reserved']==1 and r['calls'][0]['status']=='failed' and r['currency_cost'] is None


def test_task_lease_duplicate_run_and_expiry():
    async def run():
        task='lease-test:'+uuid4().hex
        assert await claim(task,'a')
        assert not await claim(task,'b')
        assert await renew(task,'a') and not await renew(task,'b')
        async with AsyncSessionLocal() as db:
            await db.execute(update(TaskLease).where(TaskLease.task_id==task).values(expires_at=now()-timedelta(seconds=1)));await db.commit()
        assert await claim(task,'b')
        await release(task,'a');assert not await claim(task,'c')
        await release(task,'b');assert await claim(task,'c');await release(task,'c')
        started=asyncio.Event();unblock=asyncio.Event();calls=[]
        @leased_task
        async def work(task_id):
            calls.append(task_id);started.set();await unblock.wait()
        first=asyncio.create_task(work(task));await started.wait();await work(task);unblock.set();await first
        assert len(calls)==1
    with TestClient(app):asyncio.run(run())


def test_character_approval_lock_and_draft_isolation():
    from app.services.character_details import creative_character
    from app.models.orm import CharacterProfile
    with TestClient(app) as c:
        imported=c.post('/api/onboarding/sample').json();pid=imported['project_id']
        char=c.get(f'/api/projects/{pid}/characters').json()[0];cid=char['id']
        base=f'/api/assets/projects/{pid}/characters/{cid}'
        head=c.get(base+'/assets').json()
        if head['locked']:
            c.post(base+'/unlock',json={'expected_revision':head['revision_id']})
        r=c.post(base+'/approve',json={'expected_revision':head['revision_id']});assert r.status_code==200,r.text
        revision=r.json()['revision_id']
        draft=char['modules'];draft['appearance']='草稿的新外貌'
        assert c.put(f'/api/projects/{pid}/characters/{cid}/modules',json=draft).status_code==409
        assert c.post(base+'/unlock',json={'expected_revision':'stale'}).status_code==409
        assert c.post(base+'/unlock',json={'expected_revision':revision}).status_code==200
        assert c.put(f'/api/projects/{pid}/characters/{cid}/modules',json=draft).status_code==200
        async def frozen():
            async with AsyncSessionLocal() as db:return await creative_character(db,await db.get(CharacterProfile,cid))
        result=asyncio.run(frozen());assert result['appearance']!='草稿的新外貌' and result['asset_revision_id']==revision
        r=c.post(base+'/approve',json={'expected_revision':revision});assert r.status_code==200
        assert asyncio.run(frozen())['appearance']=='草稿的新外貌'
        # Leave the imported example editable for other tests.
        c.post(base+'/unlock',json={'expected_revision':r.json()['revision_id']})


def test_consistency_unknown_is_not_pass_and_stale_hash_rejected():
    from app.api.routes.consistency import DIMENSIONS
    with TestClient(app) as c:
        cid=c.post('/api/onboarding/sample').json()['chapter_id'];base=f'/api/quality/chapters/{cid}/consistency'
        current=c.get(base).json()
        panels=[{'index':p['index'],'scores':{k:None for k in DIMENSIONS}} for p in current['panels']]
        r=c.post(base,json={'hashes':current['hashes'],'panels':panels});assert r.status_code==200,r.text
        assert r.json()['percent'] is None and not r.json()['passed']
        for p in panels:p['scores']={k:2 for k in DIMENSIONS}
        assert c.post(base,json={'hashes':current['hashes'],'panels':panels}).json()['passed']
        assert c.post(base,json={'hashes':{},'panels':panels}).status_code==409


def test_probe_requires_cost_consent_and_records_protocol_only(monkeypatch):
    from app.tools.llm_client import LLMClient
    async def fake(*args,**kwargs):return {'ok':True}
    monkeypatch.setattr(LLMClient,'generate_json',fake)
    monkeypatch.setattr(settings,'AI_PROVIDER','local_http')
    monkeypatch.setattr(settings,'LOCAL_GPT_API_KEY','private-probe-key')
    with TestClient(app) as c:
        assert c.post('/api/studio/probe',json={'kind':'text'}).status_code==422
        assert c.post('/api/studio/probe',json={'kind':'text','acknowledge_cost':True},headers={'Origin':'https://evil.example'}).status_code==403
        r=c.post('/api/studio/probe',json={'kind':'text','acknowledge_cost':True});assert r.status_code==200,r.text
        assert r.json()['status']=='passed' and 'private-probe-key' not in r.text
        rows=c.get('/api/studio/verifications').json();assert rows[0]['matches_current_config']
        monkeypatch.setattr(settings,'LOCAL_GPT_API_KEY','different')
        assert not c.get('/api/studio/verifications').json()[0]['matches_current_config']
