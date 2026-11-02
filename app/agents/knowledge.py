"""Small, local, role-filtered lexical knowledge retrieval; no embedding service."""
import hashlib
import json
import re
from contextvars import ContextVar
from functools import lru_cache
from app.core.paths import ROOT

knowledge_trace=ContextVar('knowledge_trace',default=None)


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
        if any(s not in data['sources'] for s in card['sources']):
            raise ValueError('知识卡引用不存在的来源')
    return data


def corpus():
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
    def score(card):
        overlap=len(terms & tokens(card['title']+' '+card['content']))
        return overlap+sum(8 for tag in card['tags'] if tag.lower() in query.lower())
    ranked=sorted(cards,key=lambda c:(-score(c),c['id']))
    core=next(c for c in cards if c['core'])
    chosen=[core]+[c for c in ranked if c['id']!=core['id']][:max(0,min(limit,4)-1)]
    return [{**c,'score':score(c),'selection':'core' if c['core'] else ('lexical_match' if score(c)>0 else 'role_fallback')} for c in chosen]


def context(role,query=''):
    selected=retrieve(role,query)
    trace=knowledge_trace.get()
    if trace is not None:
        from app.tools.desktop_bridge import stage_context
        for card in selected:
            entry={'role':role,'id':card['id'],'sha256':card['sha256'],'selection':card['selection'],'score':card['score'],'stage':stage_context.get()}
            if entry not in trace:trace.append(entry)
    blocks=['专业知识参考（项目原创应用笔记；外部链接仅供核对与延伸阅读，并非全文转载）。按本次任务选择适用方法；服从用户约束与输出 Schema，不把惯例当作绝对法则。']
    for c in selected:
        refs='；'.join(s['title']+' '+s['url'] for s in c['source_details']) or '项目原创操作检查表'
        blocks.append(f"[{c['id']} sha256:{c['sha256'][:12]}] {c['title']}\n{c['content']}\n来源性质：原创应用笔记。延伸阅读：{refs}")
    return '\n\n'.join(blocks)
