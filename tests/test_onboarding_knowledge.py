import asyncio
from copy import deepcopy
from fastapi.testclient import TestClient
from app.main import app
from app.agents.knowledge import retrieve,role_cards
from app.agents.skills import ROLES,instructions


def test_knowledge_role_routing_and_sources():
    for role in ROLES:
        cards=role_cards(role)
        assert len(cards)==4 and len({c['id'] for c in cards})==4
        assert all(c['role']==role and len(c['sha256'])==64 for c in cards)
        assert cards[0]['content'] in instructions(role)
    results=retrieve('storyboard_artist','两个人对话正反打，180度轴线和视线方向')
    assert any(c['id']=='board-axis' and c['selection']=='lexical_match' for c in results)
    assert len(results)==3
    assert all(c['role']=='storyboard_artist' for c in results)
    assert '[board-axis sha256:' in instructions('storyboard_artist','对话正反打，轴线')


def test_sample_import_edit_export_restore_and_no_overwrite(monkeypatch):
    import app.tools.llm_client as llm
    import app.tools.image_gen as image
    async def prohibited(*args,**kwargs):raise AssertionError('Sample must not call a model')
    monkeypatch.setattr(llm.LLMClient,'_request',prohibited)
    monkeypatch.setattr(image.ImageGeneratorClient,'generate_image',prohibited)
    with TestClient(app) as c:
        r=c.post('/api/onboarding/sample');assert r.status_code==200,r.text
        data=r.json();assert data['model_calls']==0
        cid=data['chapter_id'];pid=data['project_id']
        board=c.get(f'/api/projects/{pid}/chapters/{cid}').json()
        assert len(board['panels'])==6
        initial=c.get(f'/api/editing/{cid}/versions').json()[0]
        layout=c.get(f'/api/editing/{cid}/bubble-layout').json()
        bubbles=deepcopy(layout['dialogues']);bubbles['bubbles'][0]['text']='示例台词修改'
        response=c.put(f'/api/editing/{cid}/bubble-layout',json={'dialogues':bubbles,'expected_version':layout['expected_version']})
        assert response.status_code==200,response.text
        again=c.post('/api/onboarding/sample').json()
        assert again['project_id']==pid and again['reused']
        layout=c.get(f'/api/editing/{cid}/bubble-layout').json()
        assert layout['dialogues']['bubbles'][0]['text']=='示例台词修改'
        response=c.post(f'/api/editing/{cid}/versions/{initial["id"]}/restore',json={'expected_version':layout['expected_version']})
        assert response.status_code==200,response.text
        assert c.get(f'/api/editing/{cid}/bubble-layout').json()['dialogues']['bubbles'][0]['text']!='示例台词修改'


def test_diagnostics_and_knowledge_endpoints():
    with TestClient(app) as c:
        r=c.get('/api/onboarding/diagnostics')
        assert r.status_code==200 and r.json()['model_requests']==0
        assert 'api_key' not in r.text.lower()
        r=c.get('/api/studio/knowledge/storyboard_artist',params={'query':'动作接触手部道具'})
        assert r.status_code==200 and any(x['id']=='board-action' for x in r.json()['cards'])
        assert c.get('/api/studio/knowledge/not-a-role').status_code==404


def test_pending_task_contains_retrieved_knowledge_evidence():
    from tests.test_studio_workflow import pending
    with TestClient(app) as c:
        pid=c.post('/api/projects',json={'name':'知识接入验证','inspiration':'两人在雨夜对话，跨越视线轴线前先建立空间。'}).json()['id']
        cid=c.post(f'/api/projects/{pid}/chapters',json={'title':'分镜验证'}).json()['id']
        c.post('/api/tasks/generate-chapter',json={'project_id':pid,'chapter_id':cid})
        task,job=pending(c,cid)
        assert '[story-causality sha256:' in job['prompt']
        evidence=task['result']['state']['knowledge_evidence']
        assert evidence and all(e['role']=='story_planner' for e in evidence)


def test_deleting_and_reimporting_sample_cleans_database_children():
    with TestClient(app) as c:
        first=c.post('/api/onboarding/sample').json()
        r=c.delete('/api/projects/'+first['project_id']);assert r.status_code==200,r.text
        assert c.get('/api/projects/'+first['project_id']).status_code==404
        second=c.post('/api/onboarding/sample').json()
        assert not second['reused']
        assert len(c.get('/api/projects/'+second['project_id']+'/chapters').json())==1


def test_standalone_tool_and_knowledge_imports_without_main():
    import subprocess,sys
    result=subprocess.run([sys.executable,'-c','from app.agents.knowledge import role_cards; from app.tools import LLMClient; from app.services import GenerateService; assert len(role_cards("storyboard_artist")) == 4'],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
