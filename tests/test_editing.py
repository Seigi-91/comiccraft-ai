"""Exercise editing against the actual API/graph, without external models."""
import json
from fastapi.testclient import TestClient
from app.main import app
from tests.test_studio_workflow import pending, respond, image_upload, task


OUTLINE = {"title": "编辑故事", "world_view": "雨夜", "outline": [{"scene": "街角", "event": "发现猫"}], "characters": [{"name": "小雨", "appearance": "红衣"}]}
BOARD = {"panels": [{"index": i, "shot_type": "中景", "perspective": "平视", "composition": {}, "action": "动作"} for i in range(2)], "layout_type": "条漫"}
DIALOGUE = {"bubbles": [{"panel_index": 0, "text": "别怕", "character": "小雨", "bubble_type": "speech", "position": {"x": 10, "y": 10}}]}


def test_edit_restore_and_single_panel_revision():
    with TestClient(app) as c:
        p = c.post('/api/projects', json={"name": "编辑测试"}).json()
        chapter = c.post(f"/api/projects/{p['id']}/chapters", json={"title": "第一章"}).json()
        cid = chapter['id']; base = '/api/editing/' + cid
        c.post('/api/tasks/generate-chapter', json={"project_id": p['id'], "chapter_id": cid})
        respond(c, cid, {"text": json.dumps(OUTLINE)})
        old_job = pending(c, cid)[1]
        edited = {**OUTLINE, "title": "修改后的故事"}
        r = c.put(base+'/content', json={"section": "outline", "content": edited})
        assert r.status_code == 200, r.text
        versions = c.get(base+'/versions').json()
        assert len(versions) == 2
        assert c.put(base+'/content', json={"section": "outline", "content": edited}).status_code == 409
        assert c.post('/api/studio/jobs/'+old_job['id']+'/reply', json={"text": json.dumps(BOARD)}).status_code == 409
        current = task(c, cid)
        assert current['result']['state']['next_node'] == 'generate_storyboard'
        c.post('/api/tasks/'+current['id']+'/resume')
        assert '修改后的故事' in pending(c, cid)[1]['prompt']
        respond(c, cid, {"text": json.dumps(BOARD)})
        respond(c, cid, {"text": json.dumps(DIALOGUE)})
        urls = [image_upload(c), image_upload(c)]
        for url in urls: respond(c, cid, {"image_url": url})
        for _ in urls: respond(c, cid, {"text": json.dumps({"passed": True, "issues": [], "score": 95})})
        assert task(c, cid)['status'] == 'completed'
        auto=c.post(base+'/auto-place-bubbles')
        assert auto.status_code==200,auto.text
        auto_task,auto_job=pending(c,cid)
        assert auto_job['stage']=='bubble_placement:0'
        assert auto_job['images']==[urls[0]]
        plan={'fits':True,'reason':'左上留白，保护右下区域','regions':[{'kind':'face','x':80,'y':80,'width':10,'height':10}],'placements':[{'id':0,'position':{'x':30,'y':22.5},'size':{'width':60,'height':45},'tail':{'x':75,'y':65}}]}
        import copy
        bad=copy.deepcopy(plan);bad['placements'][0]['position']={'x':70,'y':65}
        assert c.post('/api/studio/jobs/'+auto_job['id']+'/reply',json={'text':json.dumps(bad)}).status_code==422
        respond(c,cid,{'text':json.dumps(plan)})
        assert task(c,cid)['status']=='completed'
        assert task(c,cid)['result']['state']['bubble_placement_report'][0]['regions'][0]['kind']=='face'
        repack=c.post(base+'/recompose')
        assert repack.status_code==200,repack.text
        assert repack.json()['height']==732
        editable=c.get(base+'/bubble-layout').json()
        bubble=editable['dialogues']['bubbles'][0]
        bubble.update(text='回家吧',tail={'x':85,'y':75},bubble_type='thought',position={'x':30,'y':22.5},size={'width':60,'height':45},font_size=20)
        saved=c.put(base+'/bubble-layout',json={'dialogues':editable['dialogues'],'expected_version':editable['expected_version']})
        assert saved.status_code==200,saved.text
        geometry=saved.json()['bubble_geometry'][0]
        assert geometry['position']=={'x':30,'y':22.5}, geometry
        state=task(c,cid)['result']['state']
        assert state['dialogues']['bubbles'][0]['position']['x']==30
        assert state['dialogues']['bubbles'][0]['text']=='回家吧'
        assert state['dialogues']['bubbles'][0]['tail']=={'x':85,'y':75}
        assert state['dialogues']['bubbles'][0]['bubble_type']=='thought'
        assert task(c,cid)['result']['final_comic']['final_image_url']==saved.json()['final_image_url']
        assert [x['image_url'] for x in c.get(f"/api/projects/{p['id']}/chapters/{cid}").json()['panels']]==urls
        assert c.put(base+'/bubble-layout',json={'dialogues':editable['dialogues'],'expected_version':editable['expected_version']}).status_code==409
        newest=c.get(base+'/versions').json()[0]['id']
        bubble['size']['height']=4
        invalid=c.put(base+'/bubble-layout',json={'dialogues':editable['dialogues'],'expected_version':newest})
        assert invalid.status_code==422,invalid.text
        assert task(c,cid)['result']['final_comic']['final_image_url']==saved.json()['final_image_url']
        complete = c.get(base+'/versions').json()[0]
        assert complete['snapshot']['task_result']['final_comic']
        r = c.post(base+'/panels/1/revise', json={"instructions": "猫咪换个动作"})
        assert r.status_code == 200, r.text
        t,j = pending(c,cid)
        assert j['stage'] == 'panel_designer:1', j
        assert '猫咪换个动作' in j['prompt']
        replacement = image_upload(c)
        respond(c, cid, {"image_url": replacement})
        for _ in urls: respond(c, cid, {"text": json.dumps({"passed": True, "issues": [], "score": 95})})
        revised_panels=c.get(f"/api/projects/{p['id']}/chapters/{cid}").json()['panels']
        assert [x['image_url'] for x in revised_panels] == [urls[0], replacement]
        assert task(c,cid)['status']=='completed'
        assert c.post(base+'/panels/99/revise', json={"instructions": "修改"}).status_code == 422
        versions = c.get(base+'/versions').json()
        r=c.post(base+'/versions/'+complete['id']+'/restore', json={"expected_version": versions[0]['id']})
        assert r.status_code == 200, r.text
        restored = task(c,cid)
        assert restored['status'] == 'completed'
        assert restored['result']['final_comic'] == complete['snapshot']['task_result']['final_comic']
        restored_panels=c.get(f"/api/projects/{p['id']}/chapters/{cid}").json()['panels']
        assert [x['image_url'] for x in restored_panels] == urls
        assert c.post('/api/studio/jobs/'+j['id']+'/reply',json={"image_url":urls[0]}).status_code == 409
        latest=c.get(base+'/versions').json()[0]['id']
        bad={"bubbles":[{**DIALOGUE['bubbles'][0],"panel_index":99}]}
        assert c.put(base+'/content',json={"section":"dialogues","content":bad,"expected_version":latest}).status_code==422
        r=c.put(base+'/content',json={"section":"dialogues","content":DIALOGUE,"expected_version":latest})
        assert r.status_code==200,r.text
        assert task(c,cid)['result']['state']['next_node']=='arbitrate_conflicts'
        assert c.get(f"/api/projects/{p['id']}/chapters/{cid}").json()['panels']==[]


def test_version_is_scoped_to_chapter():
    with TestClient(app) as c:
        assert c.get('/api/editing/missing/versions').status_code == 404
