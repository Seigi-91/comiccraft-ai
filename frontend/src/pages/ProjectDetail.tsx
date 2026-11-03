import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import axios from 'axios'
import Characters from '../components/Characters'
import ShotPlanning from '../components/ShotPlanning'
import ChapterEditor from '../components/ChapterEditor'
import BubbleEditor from '../components/BubbleEditor'
import PanelRepairEditor from '../components/PanelRepairEditor'
import ProductionWorkbench from '../components/ProductionWorkbench'
import { ArrowLeft, Plus, Play, Download, RefreshCw, Check, BookOpen } from 'lucide-react'

const NovelAdaptation = lazy(() => import('../components/NovelAdaptation'))

type Panel = { id?: string; index: number; image_url: string; status: string }
type Chapter = { id: string; title: string; phase: string; panels: Panel[]; outline?: Record<string, unknown>; storyboard?: Record<string, unknown>; dialogues?: Record<string, unknown> }
type Task = { id: string; status: string; error_message?: string; result?: { state?: { next_node?: string; events?: { node: string }[]; panels?: Panel[]; characters?: {name:string; role?:string; appearance?:string; personality?:string; relationships?:string; source_facts?:string[]; adaptation_choices?:string[]}[]; outline?: Record<string, unknown>; storyboard?: Record<string, unknown>; dialogues?: Record<string, unknown>; phase?: string }; pending_job_id?: string; waiting_for?: string; final_comic?: { final_image_url: string } } }
type Job = { id: string; kind: string; stage: string; prompt: string; images: string[]; status: string }
const stages = [['generate_outline','剧情策划'],['generate_storyboard','分镜设计'],['generate_dialogue','台词创作'],['arbitrate_conflicts','交接检查'],['generate_panels','画面生成'],['review_panels','风格审核'],['final_layout','成稿排版']]
const statusText: Record<string,string> = {pending:'排队中',running:'处理中',needs_human:'等待确认或修订',failed:'任务失败',completed:'创作完成'}
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
  const [revision, setRevision] = useState('')
  const [panelIndex, setPanelIndex] = useState('0')
  const [revisionOpen,setRevisionOpen]=useState(false)
  const [bubbleOpen,setBubbleOpen]=useState(false)
  const [repairPanel, setRepairPanel] = useState<number | null>(null)
  const [productionOpen,setProductionOpen]=useState(false)
  const [novelOpen,setNovelOpen]=useState(false)
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
    setTask(null); setJobs([]); setRevisionOpen(false); setRepairPanel(null)
    poll()
    return () => { alive=false; clearTimeout(timer) }
  }, [selectedId, refresh])

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
  async function continueAutomatically(){
    if(!task)return;setBusy(true);setError('')
    try{setTask((await axios.post('/api/tasks/'+task.id+'/continue-automatic')).data)}catch(e){setError(message(e))}finally{setBusy(false)}
  }
  async function resume() {
    if(!task) return
    setBusy(true);setError('')
    try {setTask((await axios.post('/api/tasks/'+task.id+'/resume')).data)}
    catch(e){setError(message(e))} finally {setBusy(false)}
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
    <button className="secondary-button" onClick={()=>setNovelOpen(!novelOpen)}>小说改编 · 导入原著</button>
    {novelOpen && projectId && <Suspense fallback={<p>正在打开小说工作台…</p>}><NovelAdaptation projectId={projectId} chapterId={selectedId} onCreated={async id=>{if(mayLeave()){setSelectedId(id);setTab('outline');await refresh()}}}/></Suspense>}
    {state?.characters?.some(card => card.source_facts) && <details className="studio-card"><summary>小说角色卡 · 原著事实与漫画设定</summary><div className="grid gap-3 sm:grid-cols-2 mt-3">{state.characters.filter(card => card.source_facts).map(card => <article key={card.name} className="border border-dark-600 rounded p-3"><h3 className="font-semibold">{card.name} · {card.role}</h3><p>{card.appearance}</p><p>{card.personality} {card.relationships}</p><p className="text-sm text-gray-400">原著事实：{card.source_facts?.join('；')}</p><p className="text-sm text-gray-400">漫画设定：{card.adaptation_choices?.join('；')}</p></article>)}</div></details>}
    {task?.result?.waiting_for==='adaptation_review' && <section className="studio-card"><h2 className="font-semibold">小说改编方案待审阅</h2><p className="text-sm text-gray-400 my-3">先检查原著事实、改编调整、删减与待确认信息。可在大纲中编辑并保存，再点击“继续任务”生成分镜。此时尚未开始生图。</p><button className="secondary-button" onClick={()=>{if(mayLeave())setTab('outline')}}>查看并编辑改编大纲</button></section>}
    {selectedId && projectId && <ShotPlanning key={selectedId+':'+task?.id+':'+task?.result?.waiting_for} projectId={projectId} chapterId={selectedId} images={art} characterCards={state?.characters||[]} canRevise={Boolean(finalUrl)&&!running} onChanged={reloadEditor}/>}
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
              {(task?.status==='failed' || (task?.status==='needs_human' && !task.result?.pending_job_id && task.result?.waiting_for!=='storyboard_review')) && <button disabled={busy} onClick={resume} className="secondary-button"><RefreshCw size={16}/>继续任务</button>}
              <button onClick={generate} disabled={!selected || busy || running || task?.status==='needs_human'} className="primary-button"><Play size={16}/>{running?'正在创作…':task?.status==='completed'?'重新创作':'生成漫画'}</button>
            </div>
          </div>
          <ol className="agent-steps">{(state?.next_node === 'generate_character_cards' || state?.events?.some(event => event.node === 'generate_character_cards') || state?.characters?.some(card => card.source_facts) ? [['generate_character_cards', '原著角色卡'], ...stages] : stages).map(([key,label],i)=>{
            const done=state?.events?.some(e=>e.node===key)
            const current=state?.next_node===key || (i===0&&!state&&task)
            return <li key={key} className={done?'done':current?'current':''}><span>{done?<Check size={13}/>:i+1}</span><small>{label}</small></li>
          })}</ol>
          {running&&state?.panels?.length?<p className="text-sm text-primary-300 mt-3">已保存 {state.panels.length} 格进度；恢复时会核对输入与参考图，只复用仍匹配的已完成结果。</p>:null}
          {task?.error_message && <p role="alert" className="error-box mt-4 whitespace-pre-wrap">{task.error_message}</p>}
        </section>
        {pending && <section className="studio-card border-primary-500/50" aria-label="旧任务迁移"><h2 className="text-lg font-semibold">旧任务需要切换自动连接</h2><p className="text-sm text-gray-400 my-3">人工复制回填模式已停用。请先在设置中验证并启用当前阶段的官方 ChatGPT 连接器或模型 API，再继续这个任务。已有作品和生成进度保留，继续执行会消耗所选模型额度。</p><div className="flex gap-3"><button className="secondary-button" onClick={()=>navigate('/studio')}>配置自动连接</button><button className="primary-button" disabled={busy} onClick={continueAutomatically}>改用自动连接继续</button></div></section>}
        {task?.status==='needs_human' && !pending && !task.result?.pending_job_id && state?.next_node==='done' && <section className="studio-card"><h2 className="font-semibold mb-2">审核需要人工修订</h2><p className="text-sm text-gray-400 mb-3">已到达自动重绘上限。输入需要改进的具体内容，再开始一轮修订。</p><label htmlFor="panel-index" className="text-sm">分镜索引（从 0 开始）</label><input id="panel-index" type="number" min="0" value={panelIndex} onChange={e=>setPanelIndex(e.target.value)}/><textarea aria-label="修订指令" value={revision} onChange={e=>setRevision(e.target.value)} placeholder="例如：第 0 格主角应穿红色外套"/><button className="primary-button mt-3" disabled={busy || !revision.trim()} onClick={fix}>提交修订</button></section>}
        {repairPanel !== null && <PanelRepairEditor key={selectedId+":"+repairPanel} chapterId={selectedId} panels={art} initialPanel={repairPanel} canAccept={art.every(panel=>panel.status==='passed')} onSaved={reloadEditor} onClose={()=>setRepairPanel(null)}/>}
        {bubbleOpen && <BubbleEditor key={selectedId} chapterId={selectedId} onSaved={reloadEditor} onClose={()=>setBubbleOpen(false)}/>}
        {revisionOpen && <section className="studio-card" role="region" aria-label="图片修订"><h2 className="font-semibold">修订第 {Number(panelIndex)+1} 格</h2><p className="text-sm text-gray-400 my-3">当前版本将自动保存。修改指定格后重新审核与排版；审核若发现其他问题，也可能要求进一步修订。</p><textarea aria-label="图片修订要求" value={revision} onChange={e=>setRevision(e.target.value)} placeholder="例如：保持面部和场景不变，将雨衣改成红色"/><div className="flex gap-3 mt-3"><button className="primary-button" disabled={busy || running || !revision.trim()} onClick={reviseImage}>提交图片修订</button><button className="secondary-button" onClick={()=>setRevisionOpen(false)}>取消</button></div></section>}
        <section className="studio-card">
          <div className="flex gap-5 overflow-auto border-b border-dark-600 mb-5" role="tablist">{[['art','漫画预览'],['outline','剧情大纲'],['storyboard','分镜脚本'],['dialogues','台词']].map(([id,label])=><button key={id} role="tab" aria-selected={tab===id} onClick={()=>{if(mayLeave())setTab(id)}} className={'pb-3 whitespace-nowrap text-sm '+(tab===id?'text-primary-300 border-b-2 border-primary-400':'text-gray-400')}>{label}</button>)}</div>
          {tab==='art' ? finalUrl?<div className="space-y-5"><img src={finalUrl} alt="完整条漫成稿" className="w-full max-w-2xl mx-auto rounded-lg"/><button className="primary-button" disabled={busy || running} onClick={()=>setRepairPanel(0)}>圈选局部精修</button><button className="secondary-button" disabled={busy || running} onClick={autoPlace}>AI 识别留白并定位气泡</button><button className="primary-button" disabled={busy || running} onClick={()=>setBubbleOpen(true)}>拖动与编辑气泡</button><button className="secondary-button" disabled={busy || running} onClick={recompose}>重新排版为漫画气泡</button><p className="text-sm text-gray-400">按台词中横、纵坐标（0–100%）放置气泡，可在“台词”中查看位置。</p><h3>点击分镜修订</h3><div className="grid sm:grid-cols-3 gap-3">{art.map(p=><button key={p.index} disabled={running || busy} aria-label={'修订第 '+(p.index+1)+' 格'} onClick={()=>{setPanelIndex(String(p.index));setRevision('');setRevisionOpen(true)}}><img src={p.image_url} alt={'分镜 '+(p.index+1)} className="w-full rounded-lg"/><span>第 {p.index+1} 格 · 点击修订</span></button>)}</div></div>:art.length?<div className="grid sm:grid-cols-2 gap-4">{art.map((p, i)=><figure key={p.index}><button disabled={running || busy} aria-label={'修订第 '+(p.index+1)+' 格'} onClick={()=>{setPanelIndex(String(p.index));setRevision('');setRevisionOpen(true)}}><img src={p.image_url} alt={'分镜 '+(p.index+1)} className="w-full rounded-lg"/><span className="text-sm text-primary-300">点击修订第 {p.index+1} 格</span></button><figcaption className="text-xs text-gray-400 mt-2">分镜 {p.index} · {p.status==='passed'?'审核通过':p.status==='failed'?'需修订':'待审核'}</figcaption><button className="secondary-button mt-2" disabled={busy || running} aria-label={'圈选局部精修第 '+(p.index+1)+' 格'} onClick={()=>setRepairPanel(i)}>圈选局部精修</button></figure>)}</div>:<div className="text-center py-20 text-gray-500"><BookOpen className="mx-auto mb-4" size={40}/><p>故事还在等待第一笔</p><p className="text-sm mt-2">创建章节，点击生成漫画开始。</p></div>:<ChapterEditor key={selectedId+tab+editorKey} chapterId={selectedId} section={tab} content={state?.[tab as 'outline'|'storyboard'|'dialogues'] || selected?.[tab as 'outline'|'storyboard'|'dialogues']} disabled={running || busy} onSaved={reloadEditor} onDirty={setEditorDirty}/>}
        </section>
      </div>
    </div>
  </div>
}
