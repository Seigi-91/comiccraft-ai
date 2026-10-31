import { useEffect, useState } from 'react'
import axios from 'axios'

type Value = string | number | boolean | null | Value[] | { [key: string]: Value }
type Doc = Record<string, unknown>
const labels: Record<string,string> = {title:'标题',world_view:'世界观',outline:'剧情段落',characters:'角色设定',name:'姓名',description:'描述',appearance:'外貌',personality:'性格',scene:'场景',summary:'情节摘要',content:'内容',panels:'分镜',index:'分镜索引',shot_type:'景别',perspective:'视角',composition:'构图',action:'动作',dialogue_ref:'台词关联',layout_type:'阅读版式',bubbles:'对白',panel_index:'所属分镜',text:'台词',character:'角色',bubble_type:'气泡类型',position:'位置',x:'横坐标',y:'纵坐标',background:'背景',foreground:'前景',main_subject:'主体',mood:'情绪',lighting:'光线',setting:'场景',conflict:'冲突',resolution:'结局',beat:'剧情节拍',purpose:'目的',event:'事件',emotion:'情绪',visual_description:'画面描述'}
function template(key: string): Value {
  if(key==='panels')return {index:0,shot_type:'中景',perspective:'平视',composition:{background:'',main_subject:''},action:'',dialogue_ref:null}
  if(key==='bubbles')return {panel_index:0,text:'',character:'',bubble_type:'speech',position:{x:50,y:50}}
  if(key==='characters')return {name:'新角色',appearance:'',personality:''}
  return {summary:'',scene:''}
}
function Fields({value,onChange,path='',disabled=false}:{value:Value;onChange:(v:Value)=>void;path?:string;disabled?:boolean}) {
  if(Array.isArray(value))return <div className="space-y-3">{value.map((item,i)=><fieldset key={i} className="rounded-xl border border-dark-600 p-4 space-y-3"><legend className="px-2 text-primary-300">{labels[path] || path} {i+1}</legend><Fields value={item} path={path} disabled={disabled} onChange={v=>onChange(value.map((x,n)=>n===i?v:x))}/><div className="flex gap-3"><button type="button" disabled={disabled || i===0} className="secondary-button" onClick={()=>{const a=[...value];[a[i-1],a[i]]=[a[i],a[i-1]];onChange(a)}}>上移</button><button type="button" disabled={disabled} className="secondary-button" onClick={()=>onChange(value.filter((_,n)=>n!==i))}>移除</button></div></fieldset>)}<button type="button" disabled={disabled} className="secondary-button" onClick={()=>onChange([...value,template(path)])}>＋ 添加{labels[path] || '条目'}</button></div>
  if(value!==null && typeof value==='object')return <div className="space-y-4">{Object.entries(value).filter(([k])=>k!=='index').map(([key,v])=><div key={key}><label className="text-sm text-gray-300 block mb-2">{labels[key] || key}</label><Fields value={v} path={key} disabled={disabled} onChange={next=>onChange({...value,[key]:next})}/></div>)}</div>
  if(path==='panel_index' && typeof value==='number')return <input aria-label="所属分镜" type="number" min={1} disabled={disabled} value={value+1} onChange={e=>onChange(Number(e.target.value)-1)}/>
  if(typeof value==='number')return <input aria-label={labels[path] || path} type="number" disabled={disabled} value={value} onChange={e=>onChange(Number(e.target.value))}/>
  if(typeof value==='boolean')return <input aria-label={labels[path] || path} type="checkbox" disabled={disabled} checked={value} onChange={e=>onChange(e.target.checked)}/>
  return <textarea aria-label={labels[path] || path} rows={path==='world_view'||path==='action'?3:2} disabled={disabled} value={value || ''} onChange={e=>onChange(e.target.value)}/>
}
type Version = {id:string;label:string;created_at:string;snapshot:{outline?:Doc;storyboard?:Doc;dialogues?:Doc;panels:{index:number;image_url:string}[]}}
export default function ChapterEditor({chapterId,section,content,disabled,onSaved,onDirty}:{chapterId:string;section:string;content?:Doc;disabled:boolean;onSaved:()=>Promise<void>;onDirty:(dirty:boolean)=>void}) {
  const [draft,setDraft]=useState<Value>({})
  const [dirty,setDirty]=useState(false)
  const [versions,setVersions]=useState<Version[]>([])
  const [selected,setSelected]=useState<Version>()
  const [history,setHistory]=useState(false)
  const [busy,setBusy]=useState(false)
  const [notice,setNotice]=useState('')
  const [confirm,setConfirm]=useState(false)
  const empty:Doc=section==='outline'?{title:'',world_view:'',outline:[],characters:[]}:section==='storyboard'?{panels:[],layout_type:'条漫'}:{bubbles:[]}
  useEffect(()=>{setDraft((content || empty) as Value);setDirty(false);setConfirm(false);setNotice('')},[chapterId,section,JSON.stringify(content)]) // Only replace drafts when persisted content changes.
  useEffect(()=>{let alive=true;axios.get('/api/editing/'+chapterId+'/versions').then(r=>{if(alive)setVersions(r.data)}).catch(()=>{if(alive)setNotice('版本记录加载失败，请重试')});return()=>{alive=false}},[chapterId,JSON.stringify(content)])
  useEffect(()=>{onDirty(dirty);const warn=(e:BeforeUnloadEvent)=>{if(dirty){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',warn);return()=>{window.removeEventListener('beforeunload',warn);onDirty(false)}},[dirty,onDirty])
  const changed=(v:Value)=>{setDraft(v);setDirty(true);setConfirm(false)}
  async function save(){
    setBusy(true);setNotice('')
    try{
      const doc=structuredClone(draft) as Record<string,Value>
      if(section==='storyboard' && Array.isArray(doc.panels))doc.panels=doc.panels.map((p,i)=>({...p as object,index:i}))
      await axios.put('/api/editing/'+chapterId+'/content',{section,content:doc,expected_version:versions[0]?.id || null})
      setDirty(false);setConfirm(false);await onSaved();setVersions((await axios.get('/api/editing/'+chapterId+'/versions')).data);setNotice('已保存，可点击“继续任务”使用编辑稿创作。')
    }catch(e){setNotice(axios.isAxiosError(e)?String(e.response?.data?.detail || e.message):String(e))}finally{setBusy(false)}
  }
  async function restore(){if(!selected)return;setBusy(true)
    try{await axios.post('/api/editing/'+chapterId+'/versions/'+selected.id+'/restore',{expected_version:versions[0]?.id || null});setDirty(false);setSelected(undefined);await onSaved();setVersions((await axios.get('/api/editing/'+chapterId+'/versions')).data);setNotice('已回退；回退前的内容也保存在历史中。')}
    catch(e){setNotice(axios.isAxiosError(e)?String(e.response?.data?.detail || e.message):String(e))}finally{setBusy(false)}}
  return <div className="space-y-5">
    <div className="flex justify-between flex-wrap gap-3"><p className="text-sm text-gray-400">{dirty?'有未保存的修改':'可直接修改内容；保存后从该阶段继续创作。'}</p><button className="secondary-button" onClick={()=>setHistory(!history)}>版本历史（{versions.length}）</button></div>
    {notice && <p role="status" className="rounded-lg p-3 bg-dark-700 text-sm whitespace-pre-wrap">{notice}</p>}
    {history && <section className="border border-dark-600 rounded-xl p-4 space-y-3"><h3>章节版本 · 大纲、分镜、台词与图片一起保存</h3>{versions.length===0?<p className="text-gray-400">首次编辑前将自动保存当前作品。</p>:<select aria-label="选择历史版本" value={selected?.id || ''} onChange={e=>setSelected(versions.find(v=>v.id===e.target.value))}><option value="">选择版本预览</option>{versions.map(v=><option key={v.id} value={v.id}>{new Date(v.created_at+'Z').toLocaleString()} · {v.label}</option>)}</select>}{selected && <div className="space-y-3"><p className="text-sm text-gray-400">回退将恢复整个章节，当前内容会自动备份。未保存的输入不会保留。</p><div className="flex overflow-x-auto gap-2">{selected.snapshot.panels.map(p=><img key={p.index} src={p.image_url} className="h-32 rounded" alt={'历史分镜 '+(p.index+1)}/>)}</div>{selected.snapshot[section as 'outline'] && <Fields value={selected.snapshot[section as 'outline'] as Value} onChange={()=>{}} disabled/>}<button disabled={busy || disabled} className="secondary-button" onClick={restore}>确认回退到此版本</button></div>}</section>}
    <Fields value={draft} onChange={changed} disabled={disabled || busy}/>
    <div className="bg-dark-800 border border-dark-600 rounded-xl p-4 space-y-3">{confirm && <p className="text-sm text-amber-300">保存将保留历史版本，并清除当前稿中受影响的下游内容（{section==='outline'?'分镜、台词和成稿':section==='storyboard'?'台词和成稿':'图片和成稿'}），继续任务时重新生成。</p>}<div className="flex gap-3"><button className="primary-button" disabled={!dirty || disabled || busy} onClick={()=>confirm?save():setConfirm(true)}>{busy?'保存中…':confirm?'确认保存并更新后续流程':'保存编辑稿'}</button><button className="secondary-button" disabled={!dirty || busy} onClick={()=>{setDraft((content || empty) as Value);setDirty(false);setConfirm(false)}}>撤销未保存修改</button></div></div>
  </div>
}
