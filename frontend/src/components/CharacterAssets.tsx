import { useEffect, useState } from 'react'
import axios from 'axios'
type Asset={revision_id:string|null;locked:boolean;revisions:{id:string;sha256:string;created_at:string}[]}
export default function CharacterAssets({projectId,characterId}:{projectId:string;characterId:string}){
 const [asset,setAsset]=useState<Asset>(),[busy,setBusy]=useState(false),[message,setMessage]=useState('')
 const base='/api/assets/projects/'+projectId+'/characters/'+characterId
 async function refresh(){setAsset((await axios.get(base+'/assets')).data)}
 useEffect(()=>{refresh().catch(()=>setMessage('无法读取角色版本'))},[base])
 async function action(name:string){setBusy(true);try{const r=await axios.post(base+'/'+name,{expected_revision:asset?.revision_id||null});setMessage(r.data.message);await refresh()}catch(e){setMessage(axios.isAxiosError(e)?e.response?.data?.detail||'操作失败':'操作失败')}finally{setBusy(false)}}
 return <div className="border border-dark-600 p-3 my-3 rounded space-y-2 text-xs"><p>角色资产：{asset?.locked?'审批版已锁定':asset?.revision_id?'草稿可编辑；生成仍用旧审批版':'尚未审批，沿用当前档案'}</p><p className="text-gray-400">先保存档案和参考图，再审批锁定。解锁后可编辑草稿；重新审批只影响新生成或显式修订，已有图像不自动改变。</p><div className="flex gap-2"><button className="secondary-button text-xs" disabled={busy||!asset||asset.locked} onClick={()=>action('approve')}>审批当前档案并锁定</button>{asset?.locked&&<button className="secondary-button text-xs" disabled={busy} onClick={()=>action('unlock')}>解锁编辑草稿</button>}</div><p role="status">{message}</p><details><summary>审批历史（{asset?.revisions.length||0}）</summary>{asset?.revisions.map(r=><p key={r.id} className="break-all">{new Date(r.created_at).toLocaleString()} · {r.id.slice(0,8)} · {r.sha256.slice(0,12)}</p>)}</details></div>
}
