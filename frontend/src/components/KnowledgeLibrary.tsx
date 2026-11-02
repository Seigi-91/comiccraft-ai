import { useEffect, useState } from 'react'
import axios from 'axios'
export type KnowledgeCard={id:string;title:string;content:string;tags:string[];sha256:string;selection?:string;source_details:{title:string;url:string;use:string}[]}
export default function KnowledgeLibrary({role,cards}:{role:string;cards:KnowledgeCard[]}) {
  const [query,setQuery]=useState(''),[results,setResults]=useState(cards),[busy,setBusy]=useState(false),[error,setError]=useState('')
  useEffect(()=>{setQuery('');setResults(cards);setError('')},[role,cards])
  async function search(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');try{setResults((await axios.get('/api/studio/knowledge/'+role,{params:{query}})).data.cards)}catch{setError('知识检索失败，请重试。')}finally{setBusy(false)}}
  return <section className="border border-dark-600 rounded-xl p-4 mb-5 space-y-4"><h3 className="font-semibold">专业知识库 · {cards.length} 张原创知识卡</h3><p className="text-xs text-gray-400">任务执行时按角色筛选，始终带入基础知识，再按任务关键词检索相关条目。使用本地词汇匹配，不需要向量数据库或额外 API；引用链接是延伸阅读，不是转载教材。</p>
    <form onSubmit={search} className="flex flex-wrap gap-2"><input aria-label="知识库检索" className="flex-1 min-w-0" maxLength={2000} value={query} onChange={e=>setQuery(e.target.value)} placeholder="例如：对话正反打，视线轴线"/><button className="secondary-button" disabled={busy}>检索知识</button></form>
    {error&&<p role="alert">{error}</p>}
    {results.map(c=><details key={c.id} className="border-t border-dark-600 pt-3"><summary className="cursor-pointer">{c.title} {c.selection==='core'&&'· 基础必读'}</summary><p className="text-sm text-gray-300 leading-7 mt-3">{c.content}</p><p className="text-xs text-gray-500 my-2">{c.tags.join(' · ')} · {c.id} · {c.sha256.slice(0,12)}</p>{c.source_details.map(s=><a key={s.url} href={s.url} target="_blank" rel="noreferrer" className="block text-xs text-primary-300 my-2">{s.title} ↗</a>)}</details>)}
  </section>
}
