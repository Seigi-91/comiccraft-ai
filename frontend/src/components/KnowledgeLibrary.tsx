import { useEffect, useState } from 'react'
import axios from 'axios'
export type KnowledgeCard={id:string;title:string;content:string;tags:string[];sha256:string;selection?:string;matched_terms?:string[];basis:string;applicability:string[];limitations:string[];project_rules:string[];examples:{positive:string;negative:string;explanation:string};evidence:{relationship:string;id:string;source_id:string;locator:string;claim:string;scope_limit:string}[];source_details:{title:string;url:string;use:string;publisher:string;access_status:string}[]}
export default function KnowledgeLibrary({role,cards}:{role:string;cards:KnowledgeCard[]}) {
  const [query,setQuery]=useState(''),[results,setResults]=useState(cards),[busy,setBusy]=useState(false),[error,setError]=useState('')
  useEffect(()=>{setQuery('');setResults(cards);setError('')},[role,cards])
  async function search(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');try{setResults((await axios.get('/api/studio/knowledge/'+role,{params:{query}})).data.cards)}catch{setError('知识检索失败，请重试。')}finally{setBusy(false)}}
  return <section className="border border-dark-600 rounded-xl p-4 mb-5 space-y-4"><h3 className="font-semibold">可核查知识库 · {cards.length} 张知识卡</h3><p className="text-xs text-gray-400">基础卡必读，专项卡采用本地中英词汇加权检索；没有命中时不补无关卡。原则证据与项目规则分开；实际效果需通过评测，不能由引用数量推断。</p>
    <form onSubmit={search} className="flex flex-wrap gap-2"><input aria-label="知识库检索" className="flex-1 min-w-0" maxLength={2000} value={query} onChange={e=>setQuery(e.target.value)} placeholder="例如：对话正反打，视线轴线"/><button className="secondary-button" disabled={busy}>检索知识</button></form>
    {error&&<p role="alert">{error}</p>}{results.length===1&&results[0]?.selection==='core'&&<p className="text-xs text-gray-400">未命中专项知识，仅保留角色基础卡。</p>}
    {results.map(c=><details key={c.id} className="border-t border-dark-600 pt-3"><summary className="cursor-pointer">{c.title} {c.selection==='core'&&'· 基础必读'}</summary><p className="text-xs text-primary-300 mt-3">{c.basis==='project_rule'?'项目自定规则，无外部原则背书':c.evidence.every(e=>e.relationship==='engineering_precedent')?'同行工程参考 + 项目规则':'来源支持原则 + 项目应用'}</p><p className="text-sm text-gray-300 leading-7 mt-3">{c.content}</p>
      <p className="text-sm mt-3"><strong>适用：</strong>{c.applicability.join('；')}</p>
      {c.evidence.map(e=><article key={e.id} className="text-xs border-l-2 border-primary-400 pl-3 my-3"><strong>来源支持的范围</strong><p>{e.claim}</p><p>定位：{e.locator}</p><p className="text-gray-400">{e.scope_limit}</p></article>)}
      <p className="text-sm"><strong>本项目规则：</strong>{c.project_rules.join('；')}</p><div className="text-sm space-y-2 mt-3"><p><strong>正例：</strong>{c.examples.positive}</p><p><strong>反例：</strong>{c.examples.negative}</p><p className="text-gray-400">{c.examples.explanation}</p><p><strong>限制与例外：</strong>{c.limitations.join('；')}</p></div>
      <p className="text-xs text-gray-500 my-2 break-all">{c.tags.join(' · ')} · {c.id} · {c.sha256.slice(0,12)}</p>{c.matched_terms&&<p className="text-xs text-gray-500">命中词：{c.matched_terms.join('、')||'基础必读'}</p>}{c.source_details.map(s=><a key={s.url} href={s.url} target="_blank" rel="noreferrer" className="block text-xs text-primary-300 my-2">{s.publisher} · {s.title} ↗</a>)}</details>)}
  </section>
}
