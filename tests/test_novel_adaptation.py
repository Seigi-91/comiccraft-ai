"""Synthetic inputs exercise the existing graph; no real model quality claims."""
import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.novel_adaptation import normalize, split_novel, SEGMENT_SIZE
from tests.test_studio_workflow import pending, respond, task, image_upload


def create_source(c, text="第一章 灯下\n阿青把铜钥匙交给林舟。\n第二章 门外\n林舟没有开门。", count=1):
    pid=c.post('/api/projects',json={'name':'小说改编测试','inspiration':'保持水彩画风'}).json()['id']
    doc=c.post('/api/novels/projects/'+pid,json={'title':'钥匙','text':text}).json()
    base=f"/api/novels/projects/{pid}/{doc['id']}"
    r=c.post(base+'/segments/0/adapt',json={'title':'灯下','mode':'faithful','panel_count':count,'required_facts':'铜钥匙交给林舟，不改成金钥匙','notes':'水彩画风，保留悬念'})
    assert r.status_code==200,r.text
    return pid,doc,base,r.json()['chapter_id']


def test_segmentation_is_lossless_bounded_and_handles_headings():
    original='\ufeff前言🌧️\r\n# 第一章 灯下\r\n'+('甲'*7900+'\n')*3+'Chapter 2 Rain\n尾声\n完'
    text,segments=split_novel(original)
    assert text==normalize(original)
    assert ''.join(text[s['start']:s['end']] for s in segments)==text
    assert all(0<s['characters']<=SEGMENT_SIZE for s in segments)
    assert any(s['title']=='# 第一章 灯下' for s in segments)
    assert [s['index'] for s in segments]==list(range(len(segments)))
    with pytest.raises(ValueError):split_novel('第一章 标题\n'*201)
    for bad in ['', '  ', 'x'*300001, 'binary\x00data']:
        with pytest.raises(ValueError):split_novel(bad)


def test_import_upload_ownership_idempotency_and_cleanup():
    with TestClient(app) as c:
        r=c.post('/api/novels/preview-file',files={'file':('雨夜.txt','第一章 雨夜\n这是正文。'.encode('gb18030'),'text/plain')})
        assert r.status_code==200 and '这是正文' in r.json()['text']
        assert c.post('/api/novels/preview-file',files={'file':('bad.pdf',b'%PDF','application/pdf')}).status_code==422
        assert c.post('/api/novels/preview-file',files={'file':('huge.txt',b'a'*2000001,'text/plain')}).status_code==413
        pid,doc,base,cid=create_source(c)
        assert doc['model_calls']==0 and len(doc['segments'])==2
        r=c.post(base+'/segments/0/adapt',json={'title':'不要覆盖','mode':'free','panel_count':20})
        assert r.json()['chapter_id']==cid and r.json()['reused']
        assert len(c.get('/api/projects/'+pid+'/chapters').json())==1
        snapshot=c.get('/api/novels/chapters/'+cid+'/source').json()
        assert snapshot['settings']['panel_count']==1 and snapshot['settings']['mode']=='faithful'
        assert snapshot['source_text']=='第一章 灯下\n阿青把铜钥匙交给林舟。\n'
        assert c.get(base.replace(pid,'other-project')).status_code==404
        assert c.post(base+'/segments/55/adapt',json={'title':'无效'}).status_code==404
        assert c.post(base+'/segments/1/adapt',json={'title':'无效','panel_count':25}).status_code==422
        assert c.delete('/api/projects/'+pid).status_code==200
        assert c.get(base).status_code==404
        from app.db.session import AsyncSessionLocal
        from app.models.orm import NovelAdaptation,NovelDocument
        from sqlalchemy import select
        async def remaining():
            async with AsyncSessionLocal() as db:
                assert not (await db.execute(select(NovelDocument).where(NovelDocument.project_id==pid))).first()
                assert not (await db.execute(select(NovelAdaptation).where(NovelAdaptation.project_id==pid))).first()
        asyncio.run(remaining())


def test_novel_review_edit_resume_comic_and_restore_preserve_source():
    with TestClient(app) as c:
        pid,doc,base,cid=create_source(c)
        source=c.get('/api/novels/chapters/'+cid+'/source').json()
        c.post('/api/tasks/generate-chapter',json={'project_id':pid,'chapter_id':cid})
        t,j=pending(c,cid)
        assert j['stage']=='generate_outline' and json.dumps(source['source_text'],ensure_ascii=False) in j['prompt']
        plain={'title':'灯下','world_view':'旧屋','outline':[{'event':'交接钥匙'}],'characters':[{'name':'阿青','appearance':'蓝衣'}]}
        assert c.post('/api/studio/jobs/'+j['id']+'/reply',json={'text':json.dumps(plain,ensure_ascii=False)}).status_code==422
        plain['adaptation']={'summary':'将交接钥匙改编为一格','kept_facts':['铜钥匙交给林舟'],'changes':[],'omissions':[],'open_questions':['林舟外貌原文未定']}
        respond(c,cid,{'text':json.dumps(plain,ensure_ascii=False)})
        review=task(c,cid)
        assert review['result']['waiting_for']=='adaptation_review'
        assert not review['result'].get('pending_job_id')
        assert review['result']['state']['next_node']=='generate_storyboard'
        assert not review['result']['state'].get('panels')
        versions=c.get('/api/editing/'+cid+'/versions').json();original_version=versions[0]['id']
        plain['adaptation']['changes']=['用近景突出钥匙交接']
        r=c.put('/api/editing/'+cid+'/content',json={'section':'outline','content':plain,'expected_version':original_version})
        assert r.status_code==200,r.text
        edited=task(c,cid)
        c.post('/api/tasks/'+edited['id']+'/resume')
        _,j=pending(c,cid)
        assert j['stage']=='generate_storyboard' and '用近景突出钥匙交接' in j['prompt'] and '铜钥匙交给林舟' in j['prompt']
        board={'panels':[{'index':0,'shot_type':'近景','perspective':'平视','composition':{},'action':'阿青递出铜钥匙'}],'layout_type':'条漫'}
        invalid={**board,'panels':board['panels']+[dict(board['panels'][0],index=1)]}
        assert c.post('/api/studio/jobs/'+j['id']+'/reply',json={'text':json.dumps(invalid,ensure_ascii=False)}).status_code==422
        respond(c,cid,{'text':json.dumps(board,ensure_ascii=False)})
        _,j=pending(c,cid);assert j['stage']=='generate_dialogue' and '铜钥匙交给林舟' in j['prompt']
        respond(c,cid,{'text':json.dumps({'bubbles':[{'panel_index':0,'text':'收好。','character':'阿青','bubble_type':'speech','position':{'x':15,'y':10}}]},ensure_ascii=False)})
        _,j=pending(c,cid);assert j['kind']=='image'
        respond(c,cid,{'image_url':image_upload(c)})
        respond(c,cid,{'text':'{"passed":true,"score":95,"issues":[]}'})
        finished=task(c,cid);assert finished['status']=='completed',finished
        assert c.get(finished['result']['final_comic']['final_image_url']).headers['content-type']=='image/png'
        versions=c.get('/api/editing/'+cid+'/versions').json()
        r=c.post('/api/editing/'+cid+'/versions/'+original_version+'/restore',json={'expected_version':versions[0]['id']})
        assert r.status_code==200,r.text
        restored=task(c,cid)
        assert restored['result']['state']['outline']['adaptation']['changes']==[]
        assert restored['result']['state']['novel_adaptation']==source
        assert c.get('/api/novels/chapters/'+cid+'/source').json()==source


def test_api_mode_also_stops_for_adaptation_review(monkeypatch):
    from app.core.config import settings
    from app.tools.llm_client import LLMClient
    calls=[]
    async def synthetic(self,prompt):
        calls.append(prompt)
        return {'title':'API合成测试','world_view':'旧屋','characters':[],'outline':[{'event':'交接钥匙'}],
                'adaptation':{'summary':'交接钥匙','kept_facts':['铜钥匙'],'changes':[],'omissions':[],'open_questions':[]}}
    monkeypatch.setattr(settings,'AI_PROVIDER','local_http')
    monkeypatch.setattr(LLMClient,'generate_json',synthetic)
    with TestClient(app) as c:
        pid,doc,base,cid=create_source(c)
        c.post('/api/tasks/generate-chapter',json={'project_id':pid,'chapter_id':cid})
        result=task(c,cid)
        assert result['result']['waiting_for']=='adaptation_review',result
        assert len(calls)==1 and '铜钥匙' in calls[0]
        assert result['result']['state']['next_node']=='generate_storyboard'
