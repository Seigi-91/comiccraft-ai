import { useEffect, useState } from 'react'
import axios from 'axios'
type Verification={id:string;kind:string;model:string;status:string;detail:string;checked_at:string;matches_current_config:boolean}
export default function ProviderChecks(){
  const [rows,setRows]=useState<Verification[]>([]),[kind,setKind]=useState('text'),[ack,setAck]=useState(false),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[cap,setCap]=useState(96)
  async function refresh(){setRows((await axios.get('/api/studio/verifications')).data)}
  useEffect(()=>{const load=()=>{Promise.all([refresh(),axios.get('/api/studio/config').then(r=>setCap(r.data.max_model_requests))]).catch(()=>setMessage('无法读取验证记录'))};load();window.addEventListener('comiccraft-config-saved',load);return()=>window.removeEventListener('comiccraft-config-saved',load)},[])
  async function probe(){setBusy(true);setMessage('');try{const r=await axios.post('/api/studio/probe',{kind,acknowledge_cost:ack});setMessage(r.data.detail);await refresh()}catch(e){setMessage(axios.isAxiosError(e)?e.response?.data?.detail||'验证失败':'验证失败')}finally{setBusy(false);setAck(false)}}
  async function saveCap(){setBusy(true);try{await axios.put('/api/studio/config',{max_model_requests:cap});setMessage('请求上限已保存；历史消耗不会清零。')}catch(e){setMessage(axios.isAxiosError(e)?e.response?.data?.detail||'保存失败':'保存失败')}finally{setBusy(false)}}
  return <section className="studio-card space-y-4"><h2 className="font-semibold">服务验证与请求上限</h2><p className="text-sm text-gray-400">每次验证执行一次适配器调用，可能消耗额度。Codex一次执行可能包含多轮底层推理/工具，不等于一次底层请求。通过只说明当时返回格式可解析，不保证画质；配置或密钥变化后旧记录会标为不匹配。</p>
    <label className="block">验证能力<select aria-label="验证能力" className="block bg-dark-900 p-2 border border-dark-600 rounded w-full" value={kind} onChange={e=>setKind(e.target.value)}>{[['text','文字 JSON'],['vision','视觉输入'],['image','文生图'],['reference','参考图生成'],['mask','蒙版精修']].map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label>
    <label className="flex gap-2"><input type="checkbox" style={{width:'auto'}} checked={ack} onChange={e=>setAck(e.target.checked)}/>我确认发送一次真实请求，可能消耗我的模型额度</label><button className="secondary-button" disabled={busy||!ack} onClick={probe}>验证所选接口</button>
    <div className="border-t border-dark-600 pt-4 space-y-2"><label>每个生成任务的最大自动模型请求预留数<input aria-label="模型请求上限" type="number" min={1} max={1000} value={cap} onChange={e=>setCap(Number(e.target.value))}/></label><p className="text-xs text-gray-400">持久计数，失败和中断的预留不退还，继续任务不会清零。这是次数保护，不是金额预算；不同请求价格可能不同，未知成本不填为零。Codex调用也计入上限，人工回填不计入。</p><button className="secondary-button" disabled={busy} onClick={saveCap}>保存请求上限</button></div>
    <p role="status" className="text-sm text-primary-300">{message}</p>
    {rows.map(r=><article key={r.id} className="border-t border-dark-600 pt-2 text-xs"><strong>{r.kind} · {r.model} · {r.status==='passed'?'协议通过':'未通过'}</strong><p>{r.detail}</p><p className="text-gray-400">{new Date(r.checked_at).toLocaleString()} · {r.matches_current_config?'对应当前配置':'历史配置，需重新验证'}</p></article>)}
  </section>
}
