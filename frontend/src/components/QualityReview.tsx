import { useEffect, useState } from 'react'
import axios from 'axios'
const dimensions={identity:'身份',outfit:'服装',hands:'手部',props:'道具',space:'空间',lettering:'气泡遮挡'}
type Scores={index:number;scores:Record<string,number|null>}
type Report={id:string;percent:number|null;coverage:number;passed:boolean;matches_current_images:boolean;notes:string}
type Data={hashes:Record<string,string>;panels:{index:number;image_url:string}[];reports:Report[]}
export default function QualityReview({chapterId}:{chapterId:string}){
 const [data,setData]=useState<Data>(),[scores,setScores]=useState<Scores[]>([]),[notes,setNotes]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[evidence,setEvidence]=useState<unknown>()
 async function refresh(){const r=await axios.get('/api/quality/chapters/'+chapterId+'/consistency');setData(r.data);setScores(r.data.panels.map((p:{index:number})=>({index:p.index,scores:Object.fromEntries(Object.keys(dimensions).map(k=>[k,null]))})));setEvidence((await axios.get('/api/assets/chapters/'+chapterId+'/evidence')).data)}
 useEffect(()=>{refresh().catch(()=>setMessage('无法读取评测与调用记录'))},[chapterId])
 async function save(){setBusy(true);try{await axios.post('/api/quality/chapters/'+chapterId+'/consistency',{hashes:data?.hashes,panels:scores,notes});setMessage('人工评测已保存，未知项不计为通过。');await refresh()}catch(e){setMessage(axios.isAxiosError(e)?e.response?.data?.detail||'保存失败':'保存失败')}finally{setBusy(false)}}
 return <div className="space-y-4"><h3>一致性人工评测</h3><p className="text-xs text-gray-400">0=阻断/严重错误；1=轻微问题；2=符合要求；未知=尚未检查。只有全部检查、无0分且总分≥80%才通过。这不是模型自评分；评测记录绑定当前分镜及台词/特效状态，气泡维度请同时核对成稿。</p>
 {scores.map((p,i)=><fieldset className="border border-dark-600 p-3 rounded" key={p.index}><legend>第 {p.index+1} 格</legend><a href={data?.panels[i]?.image_url} target="_blank" rel="noreferrer"><img src={data?.panels[i]?.image_url} alt={'评测分镜 '+(p.index+1)} className="w-32 rounded mb-2"/></a><div className="grid grid-cols-2 md:grid-cols-3 gap-3">{Object.entries(dimensions).map(([k,t])=><label key={k} className="text-xs">{t}<select aria-label={'第'+(p.index+1)+'格'+t} className="block w-full bg-dark-900 p-2" value={p.scores[k]??''} onChange={e=>setScores(xs=>xs.map((x,n)=>n===i?{...x,scores:{...x.scores,[k]:e.target.value===''?null:Number(e.target.value)}}:x))}><option value="">未知</option><option value="0">0 · 严重</option><option value="1">1 · 轻微</option><option value="2">2 · 符合</option></select></label>)}</div></fieldset>)}
 <textarea aria-label="一致性评测备注" value={notes} onChange={e=>setNotes(e.target.value)} maxLength={4000} placeholder="记录具体格号与可见问题，注明所用服务及比较条件"/><button className="primary-button" disabled={busy||!scores.length} onClick={save}>保存人工评测</button><p role="status">{message}</p>
 {data?.reports.map(r=><p key={r.id} className="text-xs">{r.passed?'通过':'待检查 / 待修复'} · 已检查 {r.coverage}% · 已检查项得分 {r.percent===null?'未知':r.percent+'%'} · {r.matches_current_images?'当前原图':'历史原图'} · {r.notes}</p>)}
 <details><summary>查看调用次数、usage、角色版本与知识卡证据</summary><pre className="prompt-box">{JSON.stringify(evidence,null,2)}</pre></details></div>
}
