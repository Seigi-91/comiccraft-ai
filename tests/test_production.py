import asyncio
from fastapi.testclient import TestClient
from PIL import Image,ImageChops
from app.main import app
from tests.test_inpainting import seed,image_bytes
from tests.test_studio_workflow import task,image_upload,respond,plan_to_image
from app.tools.media import save_image_bytes,local_image_path


def project(c):return c.post('/api/projects',json={'name':'素材生产测试'}).json()['id']
def chapter(c,pid,title='测试章节'):return c.post(f'/api/projects/{pid}/chapters',json={'title':title}).json()['id']
def seeded(c):
    pid=project(c);cid=chapter(c,pid);url=save_image_bytes(image_bytes('red'));asyncio.run(seed(cid,pid,url));return pid,cid,url


def test_snapshot_provenance_and_immutable_generation_context():
    with TestClient(app) as c:
        pid,cid,url=seeded(c)
        assert c.post('/api/production/chapters/'+cid+'/capture').json()['captured']==1
        record=c.get('/api/production/chapters/'+cid+'/records').json()[0]
        assert record['origin']=='current_capture_not_historical_generation'
        assert record['snapshot']['historical_generation_parameters']=='unknown'
        assert len(record['snapshot']['image_sha256'])==64
        other=chapter(c,pid)
        c.post('/api/tasks/generate-chapter',json={'project_id':pid,'chapter_id':other})
        plan_to_image(c,other)
        records=c.get('/api/production/chapters/'+other+'/records').json()
        assert records[0]['status']=='waiting'
        assert records[0]['snapshot']['context']['characters'][0]['appearance']=='红外套'
        respond(c,other,{'image_url':image_upload(c)})
        records=c.get('/api/production/chapters/'+other+'/records').json()
        assert records[0]['status']=='completed' and records[0]['image_url']
        assert records[0]['snapshot']['context']['panel']['index']==0


def test_batch_pause_resume_cancel_and_restart():
    with TestClient(app) as c:
        pid=project(c);first=chapter(c,pid,'第一章');second=chapter(c,pid,'第二章')
        r=c.post(f'/api/production/projects/{pid}/batches',json={'name':'连续章节','chapter_ids':[first,second]});bid=r.json()['id']
        assert c.post('/api/production/batches/'+bid+'/start').status_code==200
        batches=c.get(f'/api/production/projects/{pid}/batches').json();assert batches[0]['items'][0]['status']=='needs_human';assert batches[0]['items'][1]['status']=='queued'
        assert c.post('/api/production/batches/'+bid+'/pause').status_code==200
        plan_to_image(c,first);respond(c,first,{'image_url':image_upload(c)});respond(c,first,{'text':'{"passed":true,"issues":[],"score":95}'})
        assert task(c,first)['status']=='completed'
        b=c.get(f'/api/production/projects/{pid}/batches').json()[0];assert b['status']=='paused' and b['items'][1]['status']=='queued'
        c.post('/api/production/batches/'+bid+'/start');assert task(c,second)['status']=='needs_human'
    with TestClient(app) as c:
        b=c.get(f'/api/production/projects/{pid}/batches').json()[0];assert b['status']=='paused'
        original=task(c,second)['id'];c.post('/api/production/batches/'+bid+'/start');assert task(c,second)['id']==original
        assert c.post('/api/production/batches/'+bid+'/cancel').json()['status']=='cancelled'
        assert c.post('/api/production/batches/'+bid+'/start').status_code==409


def test_experiments_compare_without_overwriting_and_adopt():
    with TestClient(app) as c:
        pid,cid,url=seeded(c);original=task(c,cid)['id']
        variants=[{'width':1024,'height':1024,'style':s} for s in ['暖光漫画','冷色漫画']]
        r=c.post(f'/api/production/chapters/{cid}/experiments',json={'panel_index':0,'variants':variants});bid=r.json()['id']
        c.post('/api/production/batches/'+bid+'/start')
        for i in range(2):
            b=c.get(f'/api/production/projects/{pid}/batches').json()[0];item=b['items'][i]
            assert item['status']=='needs_human';assert task(c,cid)['id']==original
            jobs=c.get('/api/studio/jobs',params={'task_id':item['task_id']}).json();job=next(j for j in jobs if j['id']==item['pending_job_id'])
            assert job['images']==[url] and variants[i]['style'] in job['prompt']
            assert c.post('/api/studio/jobs/'+job['id']+'/reply',json={'image_url':image_upload(c)}).status_code==200
        batch=c.get(f'/api/production/projects/{pid}/batches').json()[0];assert batch['status']=='completed'
        assert all(i['candidate_url'] for i in batch['items'])
        assert c.get(f'/api/projects/{pid}/chapters/{cid}').json()['panels'][0]['image_url']==url
        assert c.post('/api/production/experiments/'+batch['items'][0]['task_id']+'/adopt',json={'expected_version':None}).status_code==200
        versions=c.get(f'/api/editing/{cid}/versions').json();assert any(v['label']=='采用实验候选前' for v in versions)


def test_non_destructive_effects_save_disable_and_rollback():
    with TestClient(app) as c:
        pid,cid,url=seeded(c);root=f'/api/production/chapters/{cid}/panels/0/effects/'
        layer={'id':'light','kind':'warm_glow','enabled':True,'opacity':.8,'x':0,'y':0,'width':50,'height':50}
        body={'layers':[layer],'expected_version':None}
        preview=c.post(root+'preview',json=body);assert preview.status_code==200,preview.text
        im=Image.open(local_image_path(preview.json()['image_url']));assert im.getpixel((100,100))==(255,0,0);assert im.getpixel((10,10))!=(255,0,0)
        assert Image.open(local_image_path(url)).getpixel((10,10))==(255,0,0)
        result=c.post(root+'save',json=body);assert result.status_code==200,result.text
        settings=c.get(f'/api/production/chapters/{cid}/effects').json();assert settings['effects']['0'][0]['kind']=='warm_glow'
        assert c.post(root+'save',json=body).status_code==409
        before=c.get(f'/api/editing/{cid}/versions').json();old=next(v for v in before if v['label']=='特效修改前')
        assert c.post(f'/api/editing/{cid}/versions/'+old['id']+'/restore',json={'expected_version':before[0]['id']}).status_code==200
        assert c.get(f'/api/production/chapters/{cid}/effects').json()['effects']=={}
        layer['enabled']=False
        preview=c.post(root+'preview',json={'layers':[layer]}).json()['image_url']
        assert ImageChops.difference(Image.open(local_image_path(preview)),Image.open(local_image_path(url))).getbbox() is None


def test_batch_retry_only_failed_item(monkeypatch):
    from app.services import production_queue
    from app.models.orm import Task,TaskStatus
    from app.db.session import AsyncSessionLocal
    async def fail_once(task_id):
        async with AsyncSessionLocal() as db:
            t=await db.get(Task,task_id);t.status=TaskStatus.FAILED;t.error_message='injected provider failure';await db.commit()
        await production_queue.schedule_batches()
    with TestClient(app) as c:
        pid,cid,url=seeded(c)
        r=c.post(f'/api/production/chapters/{cid}/experiments',json={'panel_index':0,'variants':[{'style':'A'},{'style':'B'}]});bid=r.json()['id']
        real=production_queue.run_experiment
        monkeypatch.setattr(production_queue,'run_experiment',fail_once)
        c.post('/api/production/batches/'+bid+'/start')
        b=c.get(f'/api/production/projects/{pid}/batches').json()[0];assert b['status']=='failed'
        assert b['items'][1]['status']=='queued'
        failed_id=b['items'][0]['task_id']
        monkeypatch.setattr(production_queue,'run_experiment',real)
        assert c.post('/api/production/batches/'+bid+'/retry').status_code==200
        b=c.get(f'/api/production/projects/{pid}/batches').json()[0]
        assert b['items'][0]['status']=='needs_human' and b['items'][0]['task_id']!=failed_id
        assert b['items'][1]['status']=='queued'
