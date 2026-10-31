import { useEffect, useState } from 'react'
import axios from 'axios'
import CharacterModules, { Modules } from './CharacterModules'
type Character={modules?:Modules;id:string;name:string;appearance_description:string;reference_image_url?:string;is_confirmed:boolean}
export default function Characters({projectId}:{projectId:string}){
 const [characters,setCharacters]=useState<Character[]>([])
 const [name,setName]=useState('')
 const [appearance,setAppearance]=useState('')
 const [error,setError]=useState('')
 const [busy,setBusy]=useState(false)
 async function refresh(){setCharacters((await axios.get('/api/projects/'+projectId+'/characters')).data)}
 useEffect(()=>{refresh().catch(()=>setError('无法加载角色'))},[projectId])
 async function create(e:React.FormEvent){
  e.preventDefault();setBusy(true);setError('')
  try{await axios.post('/api/projects/'+projectId+'/characters',null,{params:{name,appearance_description:appearance}});setName('');setAppearance('');await refresh()}
  catch{setError('角色创建失败')}finally{setBusy(false)}
 }
 async function upload(character:Character,file?:File){
  if(!file)return
  setBusy(true);setError('')
  try{const form=new FormData();form.append('file',file);const image=(await axios.post('/api/studio/uploads',form)).data.url
   await axios.post('/api/projects/'+projectId+'/characters/'+character.id+'/reference',null,{params:{reference_image_url:image}})
   await refresh()
  }catch{setError('参考图上传失败')}finally{setBusy(false)}
 }
 return <section className="studio-card"><h2 className="font-semibold mb-3">角色设定</h2><p className="text-xs text-gray-500 mb-4">分模块编辑身份、性格、外貌与服装。新任务会继承保存的档案。</p>
 {error&&<p role="alert" className="text-red-300 text-xs mb-3">{error}</p>}
 {characters.map(c=><div key={c.id} className="border-b border-dark-600 pb-3 mb-3"><div className="flex gap-2">{c.reference_image_url&&<img src={c.reference_image_url} alt={c.name+'参考图'} className="w-12 h-12 object-cover rounded"/>}<div><strong className="text-sm">{c.name}</strong><p className="text-xs text-gray-400 break-words">{c.appearance_description}</p><p className="text-xs text-primary-300">当前服装：{c.modules?.outfits.find(o=>o.id===c.modules?.active_outfit_id)?.name || '沿用原设定'}</p></div></div><label className="text-xs text-primary-300 cursor-pointer block mt-2">{c.reference_image_url?'更换参考图':'上传参考图'}<input className="sr-only" type="file" accept="image/*" disabled={busy} onChange={e=>upload(c,e.target.files?.[0])}/></label><CharacterModules projectId={projectId} character={c} onSaved={refresh}/></div>)}
 <details><summary className="cursor-pointer text-sm text-primary-300">添加角色</summary><form onSubmit={create} className="space-y-2 mt-3"><input aria-label="角色姓名" placeholder="角色姓名" value={name} onChange={e=>setName(e.target.value)} required/><textarea aria-label="角色外貌" placeholder="发型、服装、道具与性格" value={appearance} onChange={e=>setAppearance(e.target.value)} rows={3}/><button className="secondary-button w-full" disabled={busy || !name.trim()}>保存角色</button></form></details></section>
}
