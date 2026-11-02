import io
import json
import zipfile
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.agents import knowledge
from app.services.knowledge_evaluation import evaluate_retrieval,digest
from app.core.paths import ROOT


def test_evidence_metadata_and_restricted_source_rejection(tmp_path):
    data=deepcopy(knowledge.corpus())
    assert len(data['cards'])==24
    assert sum(bool(c['evidence']) for c in data['cards'])==18
    for card in data['cards']:
        assert card['applicability'] and card['limitations'] and all(card['examples'].values())
        for evidence in card['evidence']:
            assert data['sources'][evidence['source_id']]['access_status']=='verified_text'
    invalid=deepcopy(data);invalid['cards'][0]['sources']=['pixar-story'];invalid['cards'][0]['evidence'][0]['source_id']='pixar-story'
    path=tmp_path/'invalid.json';path.write_text(json.dumps(invalid),encoding='utf-8')
    with pytest.raises(ValueError,match='支持证据'):knowledge._read_cards(path,path.stat().st_mtime_ns)


def test_snapshot_context_and_no_irrelevant_supplements(monkeypatch):
    frozen=deepcopy(knowledge.corpus());original=knowledge.role_cards('storyboard_artist')[0]['sha256']
    changed=deepcopy(frozen);changed['cards'][4]['content']='changed knowledge in later edition'
    monkeypatch.setattr(knowledge,'_read_cards',lambda *args:changed)
    token=knowledge.knowledge_corpus.set(frozen)
    try:assert knowledge.role_cards('storyboard_artist')[0]['sha256']==original
    finally:knowledge.knowledge_corpus.reset(token)
    assert knowledge.role_cards('storyboard_artist')[0]['sha256']!=original
    assert len(knowledge.retrieve('layout_artist','PostgreSQL replication WAL checkpoint configuration'))==1


def test_retrieval_report_is_reproducible_and_not_quality_claim():
    report=evaluate_retrieval();saved=json.loads((ROOT/'benchmarks/knowledge-retrieval-report.json').read_text(encoding='utf-8'))
    assert report==saved
    assert 'not generated-comic quality' in report['scope']
    assert all(x['role']==next(c['role'] for c in knowledge.corpus()['cards'] if c['id']==cid) for x in report['variants']['v2']['cases'] for cid in x['retrieved'])


def test_manual_ablation_freezes_and_blinds_without_model_requests(monkeypatch):
    from app.tools.llm_client import LLMClient
    async def prohibited(*args,**kwargs):raise AssertionError('manual experiment must not call a model')
    monkeypatch.setattr(LLMClient,'_request',prohibited)
    with TestClient(app) as c:
        r=c.post('/api/knowledge-lab/experiments',json={'role':'storyboard_artist','task':'两个人在书店门口对话，请说明如何保持轴线和视线连续。'})
        assert r.status_code==200,r.text
        experiment=r.json();base='/api/knowledge-lab/experiments/'+experiment['id']
        assert experiment['model_requests']==0 and 'mapping' not in experiment
        assert sum('[board-intent sha256:' in p for p in experiment['prompts'].values())==1
        manifest=zipfile.ZipFile(io.BytesIO(c.get(base+'/bundle').content))
        frozen=json.loads(manifest.read('analyst/manifest.json'))
        assert digest(frozen['corpus'])==experiment['corpus_sha256']
        for label in ['A','B']:
            text=json.dumps({'plan':'合成测试输出，不是真实模型评测。','checks':['先建立空间关系'],'uncertainties':['未调用真实模型']},ensure_ascii=False)
            r=c.put(base+'/reply',json={'label':label,'text':text,'model_label':'synthetic fixture','session_note':'synthetic test, no ChatGPT session'})
            assert r.status_code==200,r.text
        blind=zipfile.ZipFile(io.BytesIO(c.get(base+'/bundle?reviewer_only=true').content))
        assert all('analyst' not in name and 'generator' not in name for name in blind.namelist())
        assert 'mapping' not in c.get(base).json()
        dimensions=['relevance','actionability','evidence_discipline','constraint_following']
        grades={label:{'scores':{d:3 for d in dimensions},'observations':{d:'测试夹具具体观察，仅用于验证数据流程' for d in dimensions}} for label in ['A','B']}
        grades['A']['scores']['relevance']=None
        body={'reviewer':'synthetic test','method':'model_assisted','blind_declared':False,'grades':grades}
        r=c.post(base+'/review',json=body);assert r.status_code==200 and 'mapping' not in r.json()
        grades['A']['scores']['relevance']=3
        r=c.post(base+'/review',json=body);assert r.status_code==200,r.text
        assert r.json()['status']=='reviewed' and r.json()['knowledge_minus_baseline']==0
        assert c.put(base+'/reply',json={'label':'A','text':text,'model_label':'fixture','session_note':'fixture'}).status_code==409
        assert c.get(base).json()['prompts']==experiment['prompts']


def test_scores_require_observations_and_legacy_scores_are_not_passed():
    from app.api.routes.consistency import PanelScore,summarize,DIMENSIONS
    with pytest.raises(ValueError):PanelScore(index=0,scores={k:2 for k in DIMENSIONS})
    assert not summarize([{'index':0,'scores':{k:2 for k in DIMENSIONS}}])['passed']


def test_inflight_generation_resumes_with_frozen_corpus(monkeypatch):
    from tests.test_studio_workflow import pending,respond
    original=deepcopy(knowledge.corpus())
    with TestClient(app) as c:
        pid=c.post('/api/projects',json={'name':'冻结知识回归','inspiration':'两个人在书店门口谈论小猫，保持对视方向。'}).json()['id']
        cid=c.post(f'/api/projects/{pid}/chapters',json={'title':'冻结测试'}).json()['id']
        c.post('/api/tasks/generate-chapter',json={'project_id':pid,'chapter_id':cid})
        first,job=pending(c,cid)
        changed=deepcopy(original)
        for card in changed['cards']:
            if card['core']:card['content']+=' NEVER_LEAK_NEW_CORPUS_INTO_RUNNING_TASK'
        monkeypatch.setattr(knowledge,'_read_cards',lambda *args:changed)
        respond(c,cid,{'text':json.dumps({'title':'冻结测试','world_view':'书店','outline':[{'beat':'相遇'}],'characters':[]},ensure_ascii=False)})
        second,next_job=pending(c,cid)
        assert second['id']==first['id'] and next_job['stage']=='generate_storyboard'
        assert 'NEVER_LEAK_NEW_CORPUS' not in next_job['prompt']
        assert second['result']['state']['knowledge_snapshot']==first['result']['state']['knowledge_snapshot']
