import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import axios from 'axios'
import Characters from '../components/Characters'
import ChapterEditor from '../components/ChapterEditor'
import BubbleEditor from '../components/BubbleEditor'
import PanelRepairEditor from '../components/PanelRepairEditor'
import ProductionWorkbench from '../components/ProductionWorkbench'
import { ArrowLeft, Plus, Play, Download, RefreshCw, Copy, Check, Upload, BookOpen } from 'lucide-react'

type Panel = { id?: string; index: number; image_url: string; status: string }
type Chapter = { id: string; title: string; phase: string; panels: Panel[]; outline?: Record<string, unknown>; storyboard?: Record<string, unknown>; dialogues?: Record<string, unknown> }
type Task = { id: string; status: string; error_message?: string; result?: { state?: { next_node?: string; events?: { node: string }[]; panels?: Panel[]; outline?: Record<string, unknown>; storyboard?: Record<string, unknown>; dialogues?: Record<string, unknown>; phase?: string }; pending_job_id?: string; final_comic?: { final_image_url: string } } }
type Job = { id: string; kind: string; stage: string; prompt: string; images: string[]; status: string }
const stages = [['generate_outline','剧情策划'],['generate_storyboard','分镜设计'],['generate_dialogue','台词创作'],['arbitrate_conflicts','交接检查'],['generate_panels','画面生成'],['review_panels','风格审核'],['final_layout','成稿排版']]
const statusText: Record<string,string> = {pending:'排队中',running:'处理中',needs_human:'等待协作',failed:'任务失败',completed:'创作完成'}
const phaseText: Record<string,string> = {planning:'待创作',storyboarding:'分镜中',dialogue:'台词中',panel_generation:'生图中',review:'审核中',layout:'排版中',completed:'已完成'}
function message(error: unknown) {
  if (axios.isAxiosError(error)) return typeof error.response?.data?.detail === 'string' ? error.response.data.detail : error.message
  return String(error)
}

export default function ProjectDetail() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState<{name:string;description:string;inspiration:string}>()
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [task, setTask] = useState<Task | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [title, setTitle] = useState('')
  const [newChapter, setNewChapter] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState('art')
  const [reply, setReply] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [copied, setCopied] = useState(false)
  const [revision, setRevision] = useState('')
  const [panelIndex, setPanelIndex] = useState('0')
  const [revisionOpen,setRevisionOpen]=useState(false)
  const [bubbleOpen,setBubbleOpen]=useState(false)
  const [repairOpen,setRepairOpen]=useState(false)
  const [productionOpen,setProductionOpen]=useState(false)
  const [editorKey,setEditorKey]=useState(0)
  const [editorDirty,setEditorDirty]=useState(false)
  function mayLeave(){return !editorDirty || window.confirm('有未保存的编辑，确定放弃这些输入吗？')}
  async function reloadEditor(){await refresh(); const r=await axios.get('/api/studio/chapters/'+selectedId+'/task');setTask(r.data);setEditorKey(k=>k+1)}
  async function autoPlace(){setBusy(true);setError('');try{await axios.post('/api/editing/'+selectedId+'/auto-place-bubbles');await reloadEditor()}catch(e){setError(message(e))}finally{setBusy(false)}}
  async function recompose(){setBusy(true);setError('');try{await axios.post('/api/editing/'+selectedId+'/recompose');await reloadEditor()}catch(e){setError(message(e))}finally{setBusy(false)}}
  async function reviseImage(){setBusy(true);setError('');try{await axios.post('/api/editing/'+selectedId+'/panels/'+panelIndex+'/revise',{instructions:revision});setRevisionOpen(false);setRevision('');await reloadEditor()}catch(e){setError(message(e))}finally{setBusy(false)}}
  const selected = chapters.find(c => c.id === selectedId)
  const pending = jobs.find(j => j.id === task?.result?.pending_job_id && j.status === 'pending')
  const state = task?.result?.state
  const art = state?.panels?.length ? state.panels : selected?.panels || []
  const finalUrl = task?.result?.final_comic?.final_image_url
  const running = task?.status === 'running' || task?.status === 'pending'

  const refresh = useCallback(async () => {
    const [p,c] = await Promise.all([axios.get('/api/projects/'+projectId), axios.get('/api/projects/'+projectId+'/chapters')])
    setProject(p.data); setChapters(c.data)
    setSelectedId(id => id || c.data.find((ch:Chapter)=>ch.id===new URLSearchParams(window.location.search).get('chapter'))?.id || c.data[0]?.id || '')
  }, [projectId])

  useEffect(() => { refresh().catch(e=>setError(message(e))) }, [refresh])
  useEffect(() => {
    if (!selectedId) { setTask(null); return }
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const res = await axios.get('/api/studio/chapters/'+selectedId+'/task')
        if (!alive) return
        setTask(res.data)
        if (res.data) {
          const js = await axios.get('/api/studio/jobs', {params:{task_id:res.data.id}})
          if (alive) setJobs(js.data)
        } else setJobs([])
        await refresh()
      } catch(e) { if(alive) setError(message(e)) }
      if(alive) timer=setTimeout(poll, 1800)
    }
    setTask(null); setJobs([]); setReply(''); setImageUrl('');setRevisionOpen(false)
    poll()
    return () => { alive=false; clearTimeout(timer) }
  }, [selectedId, refresh])
  useEffect(() => { setReply(''); setImageUrl(''); setCopied(false) }, [pending?.id])

  async function createChapter(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError('')
    try {
      const res = await axios.post('/api/projects/'+projectId+'/chapters',{title:title.trim()})
      setSelectedId(res.data.id); setTitle(''); setNewChapter(false); await refresh()
    } catch(e) {setError(message(e))} finally {setBusy(false)}
  }
  async function generate() {
    if(!selected) return
    setBusy(true); setError('')
    try {
      const res = await axios.post('/api/tasks/generate-chapter',{project_id:projectId,chapter_id:selected.id})
      setTask(res.data)
    } catch(e) {setError(message(e))} finally {setBusy(false)}
  }
  async function resume() {
    if(!task) return
    setBusy(true);setError('')
    try {setTask((await axios.post('/api/tasks/'+task.id+'/resume')).data)}
    catch(e){setError(message(e))} finally {setBusy(false)}
  }
  async function upload(file?: File) {
    if(!file)return
    setBusy(true);setError('')
    try {
      const form=new FormData();form.append('file',file)
      setImageUrl((await axios.post('/api/studio/uploads',form)).data.url)
    }catch(e){setError(message(e))}finally{setBusy(false)}
  }
  async function submitReply() {
    if(!pending)return
    setBusy(true);setError('')
    try {
      await axios.post('/api/studio/jobs/'+pending.id+'/reply',{text:reply,image_url:imageUrl || null})
      setJobs(list=>list.map(j=>j.id===pending.id?{...j,status:'completed'}:j))
      if(task)setTask({...task,status:'pending'})
    }catch(e){setError(message(e))}finally{setBusy(false)}
  }
  async function fix() {
    if(!task)return
    setBusy(true);setError('')
    try {setTask((await axios.post('/api/tasks/'+task.id+'/human-fix',{panel_id:panelIndex,instructions:revision})).data);setRevision('')}
    catch(e){setError(message(e))}finally{setBusy(false)}
  }

  return <div className="space-y-6">
    <div className="flex items-start gap-4">
      <button aria-label="返回项目列表" className="icon-button" onClick={()=>navigate('/')}><ArrowLeft size={22}/></button>
      <div className="min-w-0"><p className="eyebrow">COMIC WORKSPACE</p><h1 className="text-3xl font-bold break-words">{project?.name || '加载创作空间…'}</h1><p className="text-gray-400 mt-2">{project?.description}</p></div>
    </div>
    <button className="secondary-button" disabled={!selectedId} onClick={()=>setProductionOpen(true)}>素材生产工作台：快照 / 批量 / 实验 / 特效</button>
    {productionOpen && projectId && selectedId && <ProductionWorkbench key={selectedId} projectId={projectId} chapterId={selectedId} chapters={chapters} panels={art} onSaved={reloadEditor} onClose={()=>setProductionOpen(false)}/>}
    {error && <div role="alert" className="error-box">{error}<button className="ml-4 underline" onClick={()=>setError('')}>关闭</button></div>}
    <div className="grid lg:grid-cols-[260px_minmax(0,1fr)] gap-6">
      <aside className="space-y-5">
        <section className="studio-card"><div className="flex items-center justify-between mb-4"><h2 className="font-semibold">章节</h2><button aria-label="创建章节" className="icon-button" onClick={()=>setNewChapter(!newChapter)}><Plus size={18}/></button></div>
          {newChapter && <form onSubmit={createChapter} className="space-y-3 mb-4"><label className="text-sm" htmlFor="chapter-title">章节标题</label><input id="chapter-title" autoFocus value={title} onChange={e=>setTitle(e.target.value)} placeholder="第一章：雨夜来信" required maxLength={200}/><button className="primary-button w-full" disabled={busy || !title.trim()}>创建章节</button></form>}
          {!chapters.length && <p className="text-gray-500 text-sm py-6">还没有章节，点击 + 创建。</p>}
          <div className="space-y-2">{chapters.map((c,i)=><button key={c.id} onClick={()=>{if(mayLeave())setSelectedId(c.id)}} className={'chapter-button '+(selectedId===c.id?'selected':'')}><span className="text-xs text-gray-500">CHAPTER {String(i+1).padStart(2,'0')}</span><strong className="block my-1">{c.title}</strong><span className="text-xs text-gray-400">{phaseText[c.phase] || c.phase}</span></button>)}</div>
        </section>
        <section className="studio-card"><h2 className="font-semibold mb-3">创作 brief</h2><p className="text-sm text-gray-400 whitespace-pre-wrap break-words">{project?.inspiration || '使用项目描述生成故事'}</p></section>
        {projectId && <Characters projectId={projectId}/>}
        <a href="/studio" className="block studio-card text-sm hover:border-primary-500">查看 agent 提示词与 skills →</a>
      </aside>
      <div className="space-y-5 min-w-0">
        <section className="studio-card">
          <div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-xl font-semibold">{selected?.title || '开始新的故事'}</h2><p className="text-sm text-gray-400 mt-1">{task ? statusText[task.status] || task.status : '从灵感到完整漫画，逐步协作创作'}</p></div>
            <div className="flex flex-wrap gap-2">
              {finalUrl && <a href={finalUrl} download className="secondary-button"><Download size={16}/>下载完整条漫</a>}
              {(task?.status==='failed' || (task?.status==='needs_human' && !task.result?.pending_job_id)) && <button disabled={busy} onClick={resume} className="secondary-button"><RefreshCw size={16}/>继续任务</button>}
              <button onClick={generate} disabled={!selected || busy || running || task?.status==='needs_human'} className="primary-button"><Play size={16}/>{running?'正在创作…':task?.status==='completed'?'重新创作':'生成漫画'}</button>
            </div>
          </div>
          <ol className="agent-steps">{stages.map(([key,label],i)=>{
            const done=state?.events?.some(e=>e.node===key)
            const current=state?.next_node===key || (i===0&&!state&&task)
            return <li key={key} className={done?'done':current?'current':''}><span>{done?<Check size={13}/>:i+1}</span><small>{label}</small></li>
          })}</ol>
          {task?.error_message && <p role="alert" className="error-box mt-4 whitespace-pre-wrap">{task.error_message}</p>}
        </section>
        {pending && <section className="studio-card border-primary-500/50">
          <div className="flex flex-wrap justify-between gap-3 mb-4"><div><p className="eyebrow">CHATGPT HANDOFF</p><h2 className="text-lg font-semibold">{pending.stage.startsWith('bubble_placement:')?'在 ChatGPT 识别人脸与气泡位置':pending.kind==='image'?'在 ChatGPT 生成这一格图片':pending.kind==='vision'?'在 ChatGPT 审核图片':'在 ChatGPT 完成当前创作任务'}</h2></div><span className="badge">需要回填结果</span></div>
          <p className="text-sm text-gray-400 mb-4">复制下方完整任务到本机 ChatGPT；有参考图时一并附上。完成后回填，流程会自动继续。此模式不直接控制桌面应用。</p>
          <div className="flex flex-wrap gap-3 mb-3"><button className="secondary-button" onClick={async()=>{try{await navigator.clipboard.writeText(pending.prompt);setCopied(true)}catch{setError('剪贴板不可用，请在任务框内手动复制')}}}><Copy size={15}/>{copied?'已复制':'复制完整任务'}</button><a className="secondary-button" href="chatgpt://" >打开本机 ChatGPT</a><a className="text-sm text-gray-400 self-center underline" href="https://chatgpt.com/" target="_blank" rel="noreferrer">网页版</a></div>
          <details><summary className="cursor-pointer text-sm text-gray-300">查看完整提示词与 skill</summary><pre className="prompt-box mt-3">{pending.prompt}</pre></details>
          {pending.images.length>0 && <div className="flex gap-3 overflow-x-auto my-4">{pending.images.map(url=><a href={url} target="_blank" rel="noreferrer" key={url} className="shrink-0"><img src={url} alt="需附给 ChatGPT 的参考图" className="h-32 rounded-lg"/><span className="text-xs text-primary-300">打开并保存参考图</span></a>)}</div>}
          {pending.kind==='image'?<div className="mt-4 space-y-3"><label className="secondary-button cursor-pointer"><Upload size={16}/>上传 ChatGPT 生成图片<input className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={e=>upload(e.target.files?.[0])}/></label>{imageUrl && <img src={imageUrl} alt="本次回填图片预览" className="max-h-64 rounded-lg"/>}</div>:<div className="mt-4"><label htmlFor="reply-json" className="text-sm block mb-2">粘贴 ChatGPT 返回的完整 JSON</label><textarea id="reply-json" rows={8} value={reply} onChange={e=>setReply(e.target.value)} placeholder='{"...": "..."}' spellCheck={false}/></div>}
          <button className="primary-button mt-4" onClick={submitReply} disabled={busy || (pending.kind==='image'?!imageUrl:!reply.trim())}>{busy?'处理中…':'提交结果并继续'}</button>
        </section>}
        {task?.status==='needs_human' && !pending && !task.result?.pending_job_id && state?.next_node==='done' && <section className="studio-card"><h2 className="font-semibold mb-2">审核需要人工修订</h2><p className="text-sm text-gray-400 mb-3">已到达自动重绘上限。输入需要改进的具体内容，再开始一轮修订。</p><label htmlFor="panel-index" className="text-sm">分镜索引（从 0 开始）</label><input id="panel-index" type="number" min="0" value={panelIndex} onChange={e=>setPanelIndex(e.target.value)}/><textarea aria-label="修订指令" value={revision} onChange={e=>setRevision(e.target.value)} placeholder="例如：第 0 格主角应穿红色外套"/><button className="primary-button mt-3" disabled={busy || !revision.trim()} onClick={fix}>提交修订</button></section>}
        {repairOpen && <PanelRepairEditor key={selectedId} chapterId={selectedId} panels={art} onSaved={reloadEditor} onClose={()=>setRepairOpen(false)}/>}
        {bubbleOpen && <BubbleEditor key={selectedId} chapterId={selectedId} onSaved={reloadEditor} onClose={()=>setBubbleOpen(false)}/>}
        {revisionOpen && <section className="studio-card" role="region" aria-label="图片修订"><h2 className="font-semibold">修订第 {Number(panelIndex)+1} 格</h2><p className="text-sm text-gray-400 my-3">当前版本将自动保存。修改指定格后重新审核与排版；审核若发现其他问题，也可能要求进一步修订。</p><textarea aria-label="图片修订要求" value={revision} onChange={e=>setRevision(e.target.value)} placeholder="例如：保持面部和场景不变，将雨衣改成红色"/><div className="flex gap-3 mt-3"><button className="primary-button" disabled={busy || running || !revision.trim()} onClick={reviseImage}>提交图片修订</button><button className="secondary-button" onClick={()=>setRevisionOpen(false)}>取消</button></div></section>}
        <section className="studio-card">
          <div className="flex gap-5 overflow-auto border-b border-dark-600 mb-5" role="tablist">{[['art','漫画预览'],['outline','剧情大纲'],['storyboard','分镜脚本'],['dialogues','台词']].map(([id,label])=><button key={id} role="tab" aria-selected={tab===id} onClick={()=>{if(mayLeave())setTab(id)}} className={'pb-3 whitespace-nowrap text-sm '+(tab===id?'text-primary-300 border-b-2 border-primary-400':'text-gray-400')}>{label}</button>)}</div>
          {tab==='art' ? finalUrl?<div className="space-y-5"><img src={finalUrl} alt="完整条漫成稿" className="w-full max-w-2xl mx-auto rounded-lg"/><button className="primary-button" disabled={busy || running} onClick={()=>setRepairOpen(true)}>圈选局部精修</button><button className="secondary-button" disabled={busy || running} onClick={autoPlace}>AI 识别留白并定位气泡</button><button className="primary-button" disabled={busy || running} onClick={()=>setBubbleOpen(true)}>拖动与编辑气泡</button><button className="secondary-button" disabled={busy || running} onClick={recompose}>重新排版为漫画气泡</button><p className="text-sm text-gray-400">按台词中横、纵坐标（0–100%）放置气泡，可在“台词”中查看位置。</p><h3>点击分镜修订</h3><div className="grid sm:grid-cols-3 gap-3">{art.map(p=><button key={p.index} disabled={running || busy} aria-label={'修订第 '+(p.index+1)+' 格'} onClick={()=>{setPanelIndex(String(p.index));setRevision('');setRevisionOpen(true)}}><img src={p.image_url} alt={'分镜 '+(p.index+1)} className="w-full rounded-lg"/><span>第 {p.index+1} 格 · 点击修订</span></button>)}</div></div>:art.length?<div className="grid sm:grid-cols-2 gap-4">{art.map(p=><figure key={p.index}><button disabled={running || busy} aria-label={'修订第 '+(p.index+1)+' 格'} onClick={()=>{setPanelIndex(String(p.index));setRevision('');setRevisionOpen(true)}}><img src={p.image_url} alt={'分镜 '+(p.index+1)} className="w-full rounded-lg"/><span className="text-sm text-primary-300">点击修订第 {p.index+1} 格</span></button><figcaption className="text-xs text-gray-400 mt-2">分镜 {p.index} · {p.status==='passed'?'审核通过':p.status==='failed'?'需修订':'待审核'}</figcaption></figure>)}</div>:<div className="text-center py-20 text-gray-500"><BookOpen className="mx-auto mb-4" size={40}/><p>故事还在等待第一笔</p><p className="text-sm mt-2">创建章节，点击生成漫画开始。</p></div>:<ChapterEditor key={selectedId+tab+editorKey} chapterId={selectedId} section={tab} content={state?.[tab as 'outline'|'storyboard'|'dialogues'] || selected?.[tab as 'outline'|'storyboard'|'dialogues']} disabled={running || busy} onSaved={reloadEditor} onDirty={setEditorDirty}/>}
        </section>
      </div>
    </div>
  </div>
}
