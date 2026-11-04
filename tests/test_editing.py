"""Exercise editing against the actual API/graph, without external models."""
import json
from fastapi.testclient import TestClient
from app.main import app
from tests.test_studio_workflow import pending, respond, image_upload, task


OUTLINE = {"title": "编辑故事", "world_view": "雨夜", "outline": [{"scene": "街角", "event": "发现猫"}], "characters": [{"name": "小雨", "appearance": "红衣"}]}
BOARD = {"panels": [{"index": i, "shot_type": "中景", "perspective": "平视", "composition": {}, "action": "动作"} for i in range(2)], "layout_type": "条漫"}
DIALOGUE = {"bubbles": [{"panel_index": 0, "text": "别怕", "character": "小雨", "bubble_type": "speech", "position": {"x": 10, "y": 10}}]}


import pytest
pytestmark = pytest.mark.usefixtures("legacy_handoff_fixture")


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
        assert repack.json()['height']==1200 and repack.json()['layout_type']=='分页'
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
        version_id=c.get(base+'/versions').json()[0]['id']
        wrong_page={'regions':[{'panel_index':0,'x':0,'y':0,'width':70,'height':50},
                               {'panel_index':1,'x':25,'y':25,'width':50,'height':50}]}
        invalid_page=c.put(base+'/page-layout',json={'expected_version':version_id,'pages':[wrong_page]})
        assert invalid_page.status_code==422
        strip=c.put(base+'/page-layout',json={'expected_version':version_id,'pages':None})
        assert strip.status_code==200 and strip.json()['height']==732
        assert c.put(base+'/page-layout',json={'expected_version':version_id,'automatic':True}).status_code==409
        version_id=c.get(base+'/versions').json()[0]['id']
        auto_page=c.put(base+'/page-layout',json={'expected_version':version_id,'automatic':True})
        assert auto_page.status_code==200 and auto_page.json()['height']==1200
        assert [x['image_url'] for x in c.get(f"/api/projects/{p['id']}/chapters/{cid}").json()['panels']]==urls
        complete = c.get(base+'/versions').json()[0]
        assert complete['snapshot']['task_result']['final_comic']
        r = c.post(base+'/panels/1/revise', json={"instructions": "猫咪换个动作"})
        assert r.status_code == 200, r.text
        t,j = pending(c,cid)
        assert j['stage'] == 'panel_designer:1', j
        assert '猫咪换个动作' in j['prompt']
        replacement = image_upload(c)
        respond(c, cid, {"image_url": replacement})
        respond(c, cid, {"text": json.dumps({"passed": True, "issues": [], "score": 95})})
        assert task(c, cid)['result']['state']['review_history'][-1]['panel_reviews'][0]['reused_review'] is True
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

def test_paged_cover_fills_slot_and_preserves_original_bubble_coordinates():
    from io import BytesIO
    from PIL import Image, ImageColor
    from app.agents.layout_artist import LayoutArtistAgent
    from app.tools.media import local_image_path, save_image_bytes

    source = BytesIO()
    Image.new("RGB", (400, 400), "#295775").save(source, "PNG")
    url = save_image_bytes(source.getvalue())
    panel = {"index": 0, "status": "passed", "image_url": url}
    board = {"panels": [{"index": 0, "composition": {"focal_point": {"x": 50, "y": 60}}}],
             "pages": [{"regions": [{"panel_index": 0, "x": 10, "y": 10, "width": 80, "height": 40}]}]}
    bubble = {"panel_index": 0, "text": "Wait", "position": {"x": 42, "y": 55},
              "size": {"width": 26, "height": 12}, "tail": {"x": 65, "y": 75}}
    rendered = LayoutArtistAgent()._render([panel], {"bubbles": [bubble]}, storyboard=board)
    with Image.open(local_image_path(rendered["final_image_url"])) as page:
        assert page.getpixel((105, 125)) == ImageColor.getrgb("#295775")
        assert page.getpixel((895, 595)) == ImageColor.getrgb("#295775")
    geometry = rendered["bubble_geometry"][0]
    assert all(geometry[key] == bubble[key] for key in ("position", "size", "tail"))
    with Image.open(local_image_path(url)) as original:
        assert original.size == (400, 400)


def test_auto_page_gives_clue_less_space_and_can_preserve_protected_art():
    from PIL import Image
    from app.services.comic_plan import auto_pages, needs_page_rebalance, validate_pages
    from app.services.page_framing import frame_page_art

    shots = [
        {"index": index, "shot_type": "中景", "composition": {"page_role": role}}
        for index, role in enumerate(("anchor", "detail", "context", "anchor"))
    ]
    pages = auto_pages(shots)
    validate_pages(pages, range(4))
    assert len(pages) == 1 and pages[0]["height"] == 1440
    anchor, clue, context, payoff = pages[0]["regions"]
    assert anchor["width"] == payoff["width"] > context["width"] > clue["width"]
    assert clue["y"] == context["y"]
    equal_tiles = [{"regions": [{"panel_index": i, "x": 3+(i%2)*48, "y": 3+(i//2)*48,
                                  "width": 46, "height": 46} for i in range(4)]}]
    assert needs_page_rebalance(equal_tiles, shots)
    assert not needs_page_rebalance(pages, shots)
    art = Image.new("RGB", (400, 400), "#295775")
    keep_whole = {"crop_safe_area": {"x": 0, "y": 0, "width": 100, "height": 100}}
    _, _, _, visible = frame_page_art(art, (800, 480), keep_whole, [])
    assert visible == (160, 0, 640, 480)
