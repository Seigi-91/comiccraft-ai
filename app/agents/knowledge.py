"""Small, local, role-filtered lexical knowledge retrieval; no embedding service."""
import hashlib
import json
import re
import math
from collections import Counter
from contextvars import ContextVar
from functools import lru_cache
from app.core.paths import ROOT

knowledge_trace=ContextVar('knowledge_trace',default=None)
knowledge_corpus=ContextVar('knowledge_corpus',default=None)


@lru_cache(maxsize=4)
def _read_cards(path, stamp):
    data=json.loads(path.read_text(encoding='utf-8'))
    ids=[c['id'] for c in data['cards']]
    if len(ids)!=len(set(ids)):
        raise ValueError('知识卡 id 不能重复')
    for role in {c['role'] for c in data['cards']}:
        if sum(bool(c.get('core')) for c in data['cards'] if c['role']==role)!=1:
            raise ValueError('每个角色必须有且仅有一张基础卡')
    for card in data['cards']:
        if data.get('version') == 2:
            required={'evidence','project_rules','applicability','limitations','examples','aliases','basis','review'}
            if not required.issubset(card) or not card['project_rules'] or not card['applicability'] or not card['limitations']:
                raise ValueError('知识卡缺少证据/适用条件/项目规则/限制')
            if set(card['examples'])!={'positive','negative','explanation'} or not all(card['examples'].values()):
                raise ValueError('知识卡须有正例、反例和解释')
            if card['basis'] not in {'source_and_project','project_rule'} or bool(card['evidence'])!=(card['basis']=='source_and_project'):
                raise ValueError('知识性质与证据不一致')
            for evidence in card['evidence']:
                source=data['sources'].get(evidence['source_id'],{})
                if source.get('access_status')!='verified_text' or not evidence.get('locator') or not evidence.get('claim') or evidence['source_id'] not in card['sources']:
                    raise ValueError('支持证据必须定位到已核对正文的来源')
        if any(s not in data['sources'] for s in card['sources']):
            raise ValueError('知识卡引用不存在的来源')
    return data


def corpus():
    if knowledge_corpus.get() is not None:
        return knowledge_corpus.get()
    path=ROOT/'knowledge/cards.json'
    return _read_cards(path,path.stat().st_mtime_ns)


def tokens(text):
    text=text.lower()
    words=set(re.findall(r'[a-z0-9]+',text))
    for part in re.findall(r'[\u4e00-\u9fff]+',text):
        words.update(part[i:i+2] for i in range(max(1,len(part)-1)))
    return words


def role_cards(role):
    result=[]
    data=corpus()
    for card in data['cards']:
        if card['role']!=role:continue
        payload={**card,'source_details':[data['sources'][s] for s in card['sources']]}
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        result.append({**payload,'sha256':digest})
    if not result:raise ValueError('未知知识库角色')
    return result


def retrieve(role, query='', limit=3):
    cards=role_cards(role);query=query[:12000];terms=tokens(query)
    # Weighted lexical ranking; role is a hard boundary. No embedding or persistent index.
    documents=[]
    for card in cards:
        counts=Counter(tokens(card['content']))
        for field,weight in [('title',3),('tags',4),('aliases',5)]:
            text=card[field] if isinstance(card[field],str) else ' '.join(card[field])
            for term in tokens(text):counts[term]+=weight
        documents.append(counts)
    df=Counter(t for doc in documents for t in doc)
    avg=sum(sum(doc.values()) for doc in documents)/max(1,len(documents))
    scores={};matches={}
    for card,doc in zip(cards,documents):
        found=sorted(terms & doc.keys());matches[card['id']]=found
        length=sum(doc.values());score=0.0
        for term in found:
            freq=doc[term];idf=math.log(1+(len(cards)-df[term]+.5)/(df[term]+.5))
            score+=idf*(freq*2.2)/(freq+1.2*(.25+.75*length/max(1,avg)))
        for phrase in [*card['tags'],*card.get('aliases',[])]:
            if len(phrase)>1 and phrase.lower() in query.lower():score+=3
        scores[card['id']]=round(score,4)
    core=next(c for c in cards if c['core'])
    ranked=sorted([c for c in cards if not c['core'] and scores[c['id']]>0],key=lambda c:(-scores[c['id']],c['id']))
    chosen=[core]+ranked[:max(0,min(limit,4)-1)]
    return [{**c,'score':scores[c['id']],'matched_terms':matches[c['id']][:12],
             'selection':'core' if c['core'] else 'lexical_match'} for c in chosen]


def context(role,query=''):
    selected=retrieve(role,query)
    trace=knowledge_trace.get()
    if trace is not None:
        from app.tools.desktop_bridge import stage_context,task_context
        for card in selected:
            entry={'role':role,'id':card['id'],'sha256':card['sha256'],'selection':card['selection'],'score':card['score'],'stage':stage_context.get(),'task_id':task_context.get(),'matched_terms':card.get('matched_terms',[]),'basis':card.get('basis'),'evidence_ids':[e['id'] for e in card.get('evidence',[])]}
            if entry not in trace:trace.append(entry)
    blocks=['创作知识参考：明确区分来源支持的原则和项目自定应用规则。只在适用条件内采用；服从用户约束和输出Schema。检索命中不是质量提升证明，不把例外/未知改成确定结论。']
    for c in selected:
        evidence=[]
        for e in c.get('evidence',[]):
            source=corpus()['sources'][e['source_id']]
            evidence.append(f"[{e['id']}] {e['claim']} 定位：{e['locator']}；{source['url']}。范围：{e['scope_limit']}")
        example=c.get('examples',{})
        blocks.append(f"[{c['id']} sha256:{c['sha256'][:12]}] {c['title']}\n{c['content']}\n适用："+'；'.join(c.get('applicability',[]))+
                      '\n来源支持：'+('；'.join(evidence) or '无外部原则背书；本卡为项目规则')+
                      '\n项目规则：'+'；'.join(c.get('project_rules',[]))+
                      '\n正例：'+example.get('positive','')+'\n反例：'+example.get('negative','')+
                      '\n限制：'+'；'.join(c.get('limitations',[])))
    return '\n\n'.join(blocks)
