import { useEffect, useState } from 'react'
import axios from 'axios'

type Anchor = {id:string; name:string; kind:string; image_url:string; sha256:string}
type Region = {x:number; y:number; width:number; height:number}
type Shot = {index:number; shot_type:string; perspective:string; action:string; character_positions?:{character:string;position:string}[]; composition:{arrangement?:string;focal_point?:{x:number;y:number};subshots?:{region?:Region; content?:string}[]}}
type Plan = {task_id:string; revision:string|null; waiting:boolean; previous_novel_context?:{title?:string;ending_action?:string;location?:string}; storyboard:{panels:Shot[];layout_type:string}|null; dialogues?:{bubbles:{panel_index:number;text:string;character?:string;position:{x:number;y:number}}[]}; bindings:Record<string,string[]>}

export default function ShotPlanning({projectId,chapterId,images,characterCards,canRevise,onChanged}:{projectId:string;chapterId:string;images:{index:number;image_url:string}[];characterCards:{name:string;appearance?:string;adaptation_choices?:string[]}[];canRevise:boolean;onChanged:()=>Promise<void>}) {
  const [plan,setPlan]=useState<Plan>()
  const [anchors,setAnchors]=useState<Anchor[]>([])
  const [kind,setKind]=useState('character')
  const [name,setName]=useState('')
  const [description,setDescription]=useState('')
  const [image,setImage]=useState('')
  const [index,setIndex]=useState(0)
  const [targets,setTargets]=useState<number[]>([])
  const [note,setNote]=useState('')
  const [busy,setBusy]=useState(false)
  const [message,setMessage]=useState('')
  const root='/api/assets/projects/'+projectId
  const planUrl='/api/assets/chapters/'+chapterId+'/shot-plan'
  const shot=plan?.storyboard?.panels.find(panel=>panel.index===index)
  const selected=plan?.bindings[index] || []
  const subshots = Array.isArray(shot?.composition.subshots) ? shot.composition.subshots : []
  const bubbles = plan?.dialogues?.bubbles || []
  function updateBubble(index: number, changes: Partial<(typeof bubbles)[number]>) {
    if (!plan) return
    setPlan({...plan, dialogues: {bubbles: bubbles.map((bubble, i) => i === index ? {...bubble, ...changes} : bubble)}})
  }

  async function refresh() {
    const [library,current]=await Promise.all([axios.get(root+'/visual-references'),axios.get(planUrl)])
    setAnchors(library.data);setPlan(current.data)
  }
  function errorText(error:unknown) {
    const detail=axios.isAxiosError(error)?error.response?.data?.detail:undefined
    return typeof detail==='string'?detail:'操作失败，请检查输入和连接后重试。'
  }
  useEffect(()=>{void refresh().catch(error=>setMessage(errorText(error)))},[projectId,chapterId])
  async function run(action:()=>Promise<void>) {
    setBusy(true);setMessage('')
    try { await action() } catch(error) { setMessage(errorText(error)) } finally { setBusy(false) }
  }
  function bind(id:string,checked:boolean) {
    if(!plan)return
    const ids=checked?[...selected,id]:selected.filter(current=>current!==id)
    if(ids.length<=3)setPlan({...plan,bindings:{...plan.bindings,[index]:ids}})
  }
  function updateSubshots(subshots:NonNullable<Shot['composition']['subshots']>) {
    if(!plan?.storyboard || !shot)return
    setPlan({...plan,storyboard:{...plan.storyboard,panels:plan.storyboard.panels.map(panel=>panel.index===index?{...panel,composition:{...panel.composition,subshots}}:panel)}})
  }
  async function savePlan(continueDrawing:boolean) {
    if(!plan?.storyboard)return
    const response=await axios.put(planUrl,{task_id:plan.task_id,expected_revision:plan.revision,storyboard:plan.storyboard,dialogues:plan.dialogues,bindings:plan.bindings})
    setPlan({...plan,revision:response.data.revision})
    if(continueDrawing) {
      await axios.post('/api/tasks/'+plan.task_id+'/resume')
      await onChanged();await refresh()
    }
    setMessage(continueDrawing?'已提交绘图。':'分镜和参考版本已保存。')
  }
  return <details className="studio-card" open={plan?.waiting || undefined}>
    <summary className="cursor-pointer font-semibold">视觉参考与分镜草图</summary>
    <div className="space-y-4 mt-4">
      <p className="text-sm text-gray-400">确认参考图后可以跨章节复用。每格最多选三张。新参考会创建新版本，旧分镜仍可引用原来的版本。</p>
      {plan?.previous_novel_context&&<details className="border border-dark-600 p-2 rounded"><summary>前章连续性资料 · {plan.previous_novel_context.title||'已完成章节'}</summary><p className="text-sm">{plan.previous_novel_context.ending_action}</p><p className="text-sm text-gray-400">{String(plan.previous_novel_context.location||'')}</p></details>}
      <fieldset disabled={busy} className="grid gap-3 sm:grid-cols-2">
        {characterCards.length>0&&<label className="sm:col-span-2">从角色卡带入设定<select aria-label="角色卡来源" value="" onChange={e=>{const card=characterCards.find(item=>item.name===e.target.value);if(card){setKind('character');setName(card.name);setDescription([card.appearance,...(card.adaptation_choices||[])].filter(Boolean).join('；').slice(0,1000))}}}><option value="">选择角色卡</option>{characterCards.map(card=><option key={card.name}>{card.name}</option>)}</select></label>}
        <label>参考类型<select aria-label="参考类型" value={kind} onChange={e=>setKind(e.target.value)}><option value="character">角色</option><option value="scene">场景</option><option value="prop">道具</option></select></label>
        <label>名称<input aria-label="参考名称" value={name} maxLength={100} onChange={e=>setName(e.target.value)}/></label>
        <label className="sm:col-span-2">画面设定<textarea aria-label="参考画面设定" value={description} maxLength={1000} onChange={e=>setDescription(e.target.value)}/></label>
        <label>沿用已有分镜<select aria-label="参考来源分镜" value={images.some(p=>p.image_url===image)?image:''} onChange={e=>setImage(e.target.value)}><option value="">选择已有图片</option>{images.map(p=><option key={p.index} value={p.image_url}>第 {p.index+1} 格</option>)}</select></label>
        <label>上传参考图<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>{const file=e.target.files?.[0];if(file)void run(async()=>{const form=new FormData();form.append('file',file);setImage((await axios.post('/api/studio/uploads',form)).data.url)})}}/></label>
      </fieldset>
      <div className="flex flex-wrap gap-2"><button className="secondary-button" disabled={busy||!name.trim()||!description.trim()} onClick={()=>run(async()=>setImage((await axios.post(root+'/visual-reference-candidate',{kind,name,description})).data.image_url))}>生成参考候选（消耗模型额度）</button><button className="primary-button" disabled={busy||!name.trim()||!image} onClick={()=>run(async()=>{const {data}=await axios.post(root+'/visual-references',{kind,name,description,image_url:image});setAnchors(previous=>[...previous,data]);setImage('');setMessage('已锁定参考版本，可在各格选择。')})}>确认并锁定参考</button></div>
      {image&&<img className="max-h-40 rounded" src={image} alt="待确认参考图"/>}
      {plan?.storyboard&&shot&&<>
        <label>查看分镜<select aria-label="草图分镜" value={index} onChange={e=>setIndex(Number(e.target.value))}>{plan.storyboard.panels.map(p=><option key={p.index} value={p.index}>第 {p.index+1} 格 · {p.shot_type}</option>)}</select></label>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="relative aspect-square bg-dark-900 border border-dark-600 rounded overflow-hidden" aria-label="分镜构图草图">
            <p className="absolute bottom-1 left-2 right-2 text-xs text-gray-300">{shot.shot_type} · {shot.perspective}</p>
            {shot.composition.focal_point&&<span title="视觉焦点" className="absolute text-primary-300 -translate-x-1/2 -translate-y-1/2" style={{left:`${shot.composition.focal_point.x}%`,top:`${shot.composition.focal_point.y}%`}}>＋</span>}
            {subshots.map((sub,i)=>sub.region&&<div key={i} className="absolute border border-primary-400 bg-indigo-950/50 text-xs overflow-hidden p-1" style={{left:`${sub.region.x}%`,top:`${sub.region.y}%`,width:`${sub.region.width}%`,height:`${sub.region.height}%`}}>{i+1}. {sub.content}</div>)}
            {plan.dialogues?.bubbles.filter(b=>b.panel_index===index).map((b,i)=><span key={i} title={b.text} className="absolute rounded-full bg-white px-2 py-1 text-xs text-black -translate-x-1/2 -translate-y-1/2" style={{left:`${Math.max(8,Math.min(92,b.position.x))}%`,top:`${Math.max(8,Math.min(92,b.position.y))}%`}}>{i+1}</span>)}
          </div>
          <div className="space-y-2"><label>本格动作<textarea aria-label="草图动作" readOnly={!plan.waiting} value={shot.action} onChange={e=>setPlan({...plan,storyboard:{...plan.storyboard!,panels:plan.storyboard!.panels.map(p=>p.index===index?{...p,action:e.target.value}:p)}})}/></label>{shot.composition.arrangement&&<p className="text-sm text-gray-400">{shot.composition.arrangement}</p>}{Array.isArray(shot.character_positions)&&shot.character_positions.map((person,i)=><p key={i} className="text-sm">{person.character} · {person.position}</p>)}{plan.dialogues?.bubbles.filter(b=>b.panel_index===index).map((b,i)=><p key={i} className="text-sm">{i+1}. {b.character||'旁白'} · {b.text}</p>)}</div>
        </div>
        {plan.waiting&&<details><summary>调整对白与预留位置</summary><div className="space-y-2 mt-2">{bubbles.map((bubble,i)=>bubble.panel_index===index&&<fieldset key={i} className="grid grid-cols-2 gap-2 border border-dark-600 rounded p-2"><legend>{bubble.character||'旁白'}</legend><label className="col-span-2">对白<input maxLength={60} value={bubble.text} onChange={e=>updateBubble(i,{text:e.target.value})}/></label><label>横坐标（%）<input type="number" min={0} max={100} value={bubble.position.x} onChange={e=>updateBubble(i,{position:{...bubble.position,x:Number(e.target.value)}})}/></label><label>纵坐标（%）<input type="number" min={0} max={100} value={bubble.position.y} onChange={e=>updateBubble(i,{position:{...bubble.position,y:Number(e.target.value)}})}/></label></fieldset>)}</div></details>}
        {plan.waiting&&<details><summary>调整格内子镜头</summary><div className="space-y-2 mt-2">{subshots.map((sub,i)=><fieldset key={i} className="grid gap-2 grid-cols-2 border border-dark-600 rounded p-2"><legend>子镜头 {i+1}</legend><label className="col-span-2">内容<input value={sub.content||''} onChange={e=>updateSubshots(subshots.map((item,j)=>j===i?{...item,content:e.target.value}:item))}/></label>{(['x','y','width','height'] as const).map(key=><label key={key}>{({x:'左边距',y:'上边距',width:'宽度',height:'高度'})[key]}（%）<input type="number" min={0} max={100} value={sub.region?.[key]??0} onChange={e=>updateSubshots(subshots.map((item,j)=>j===i?{...item,region:{x:0,y:0,width:25,height:25,...item.region,[key]:Number(e.target.value)}}:item))}/></label>)}<button className="secondary-button" onClick={()=>updateSubshots(subshots.filter((_,j)=>j!==i))}>移除子镜头</button></fieldset>)}<button className="secondary-button" disabled={subshots.length>=4} onClick={()=>updateSubshots([...subshots,{content:'局部特写',region:{x:65,y:8,width:28,height:26}}])}>添加嵌入小格</button></div></details>}
        <p className="text-sm">本格参考（{selected.length}/3）</p>
        <div className="grid gap-2 grid-cols-2 md:grid-cols-3">{anchors.map(anchor=><label key={anchor.id} className="border border-dark-600 rounded p-2 text-sm"><img src={anchor.image_url} alt="" className="h-20 w-full object-contain"/><input type="checkbox" style={{width:'auto'}} checked={selected.includes(anchor.id)} disabled={busy||(!selected.includes(anchor.id)&&selected.length>=3)} onChange={e=>bind(anchor.id,e.target.checked)}/> {anchor.name} <small>{anchor.sha256.slice(0,7)}</small></label>)}</div>
        {plan.waiting&&<div className="flex flex-wrap gap-2"><button className="secondary-button" disabled={busy} onClick={()=>run(()=>savePlan(false))}>保存草图</button><button className="primary-button" disabled={busy} onClick={()=>run(()=>savePlan(true))}>确认草图并绘图</button></div>}
        {canRevise&&<div className="space-y-2"><label className="block"><input type="checkbox" style={{width:'auto'}} checked={targets.includes(index)} onChange={e=>setTargets(previous=>e.target.checked?[...previous,index]:previous.filter(i=>i!==index))}/> 将第 {index+1} 格加入修订范围</label><p>已选格：{targets.map(i=>i+1).join('、')||'尚未选择'}</p><label>修订要求<textarea aria-label="按格修订要求" value={note} onChange={e=>setNote(e.target.value)}/></label><button className="primary-button" disabled={busy||!targets.length||!note.trim()} onClick={()=>run(async()=>{const [first,...rest]=[...targets].sort((a,b)=>a-b);await axios.post('/api/editing/'+chapterId+'/panels/'+first+'/revise',{instructions:note,additional_panels:rest,reference_ids:Object.fromEntries(targets.map(i=>[i,plan.bindings[i]||[]]))});await onChanged();await refresh();setTargets([]);setMessage('已提交所选分镜修订。')})}>只重绘所选格</button></div>}
      </>}
      <p role="status" className="text-sm text-primary-300">{busy?'处理中…':message}</p>
    </div>
  </details>
}
