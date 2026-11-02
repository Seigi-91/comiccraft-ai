"""Reproducible local retrieval checks, not a model-quality leaderboard."""
import hashlib
import json
from pathlib import Path
from app.core.paths import ROOT
from app.agents.knowledge import corpus,retrieve,tokens


def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def legacy(corpus_data,role,query):
    cards=[c for c in corpus_data['cards'] if c['role']==role];terms=tokens(query)
    def score(c):return len(terms & tokens(c['title']+' '+c['content']))+sum(8 for tag in c['tags'] if tag.lower() in query.lower())
    core=next(c for c in cards if c['core'])
    return [core]+[c for c in sorted(cards,key=lambda c:(-score(c),c['id'])) if not c['core']][:2]


def evaluate_retrieval():
    suite=json.loads((ROOT/'benchmarks/knowledge-retrieval.json').read_text(encoding='utf-8'))
    frozen=json.loads((ROOT/'benchmarks/knowledge-v1-corpus.json').read_text(encoding='utf-8'));current=corpus()
    output={'scope':'maintainer-authored retrieval checks only; not generated-comic quality','dataset_sha256':digest(suite),'corpus_sha256':digest(current),'baseline_commit':suite['baseline_commit'],'variants':{}}
    for name,fn in [('v1_frozen',lambda c:legacy(frozen,c['role'],c['query'])),('legacy_on_v2',lambda c:legacy(current,c['role'],c['query'])),('v2',lambda c:retrieve(c['role'],c['query']))]:
        rows=[]
        for case in suite['cases']:
            found=fn(case);ids=[c['id'] for c in found];supp=[c['id'] for c in found if not c['core']]
            rows.append({'id':case['id'],'split':case['split'],'kind':case['kind'],'role':case['role'],'expected':case['expected'],'retrieved':ids,
                         'hit':bool(set(case['expected'])&set(ids)) if case['expected'] else None,
                         'irrelevant_supplement':bool(supp) if not case['expected'] else None})
        metrics={}
        for split in ['development','holdout','all']:
            selected=[r for r in rows if split=='all' or r['split']==split]
            relevant=[r for r in selected if r['kind']=='relevant'];neg=[r for r in selected if r['kind']=='out_of_domain']
            metrics[split]={'relevant_count':len(relevant),'hit_rate_at_3':round(sum(r['hit'] for r in relevant)/len(relevant),4) if relevant else None,
                            'negative_count':len(neg),'irrelevant_supplement_rate':round(sum(r['irrelevant_supplement'] for r in neg)/len(neg),4) if neg else None}
        output['variants'][name]={'metrics':metrics,'cases':rows}
    return output
