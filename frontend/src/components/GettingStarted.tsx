import { useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

type Check = { name: string; status: string; detail: string; fix: string }
export default function GettingStarted() {
  const navigate=useNavigate()
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [checks,setChecks]=useState<Check[]>([])
  async function sample() {
    setBusy(true);setError('')
    try { const r=await axios.post('/api/onboarding/sample');navigate('/projects/'+r.data.project_id) }
    catch(e){setError(axios.isAxiosError(e)?e.response?.data?.detail||'无法导入示例':'无法导入示例')}
    finally{setBusy(false)}
  }
  async function diagnose(){
    setBusy(true);setError('')
    try{setChecks((await axios.get('/api/onboarding/diagnostics')).data.checks)}
    catch{setError('环境检查失败，请查看启动窗口。')}
    finally{setBusy(false)}
  }
  return <section className="studio-card space-y-4"><h2 className="text-xl font-semibold">先体验，再接模型</h2>
    <p className="text-sm text-gray-400">导入《雨夜留灯》的六格预生成素材，在完整编辑器中改气泡、导出并回退。不调用模型、不产生模型费用；重复导入会打开已有示例，保留你的修改。</p>
    <div className="flex flex-wrap gap-3"><button className="primary-button" disabled={busy} onClick={sample}>{busy?'处理中…':'导入 / 打开可编辑示例'}</button><button className="secondary-button" disabled={busy} onClick={diagnose}>检查本机环境</button></div>
    {error&&<p role="alert" className="error-box">{error}</p>}
    {checks.length>0&&<ul className="space-y-3" aria-label="环境诊断结果">{checks.map(c=><li key={c.name} className="border border-dark-600 rounded-lg p-3 text-sm"><strong>{c.status==='ok'?'✓':c.status==='error'?'✗':'·'} {c.name}</strong><p className="text-gray-300">{c.detail}</p>{c.status!=='ok'&&<p className="text-gray-400">{c.fix}</p>}</li>)}</ul>}
  </section>
}
