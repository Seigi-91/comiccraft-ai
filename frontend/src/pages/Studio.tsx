import { useEffect, useState } from 'react'
import axios from 'axios'

type UpstreamSkill = {
  name: string; skillsmp_url?: string; github_url?: string; commit?: string; source_kind?: string
  installed_path: string; runtime_path: string; adaptation: string
}
type Agent = { id: string; name: string; instructions: string; skill: string; upstream_skills: UpstreamSkill[] }

export default function Studio() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [selected, setSelected] = useState('')
  const [config, setConfig] = useState<{ description: string; provider: string }>()
  const [error, setError] = useState('')
  const current = agents.find(a => a.id === selected)
  useEffect(() => {
    Promise.all([axios.get('/api/studio/agents'), axios.get('/api/studio/config')])
      .then(([a, c]) => { setAgents(a.data); setSelected(a.data[0]?.id); setConfig(c.data) })
      .catch(() => setError('无法连接创作服务，请检查后端是否启动。'))
  }, [])
  return <div className="space-y-6">
    <div><p className="eyebrow">YOUR CREATIVE TEAM</p><h1 className="text-3xl font-bold">创作团队与设置</h1>
      <p className="text-gray-400 mt-3">六个专业 agent，配备可追溯的上游技能与项目原创规则。</p></div>
    {error && <p role="alert" className="error-box">{error}</p>}
    <section className="studio-card"><h2 className="font-semibold mb-3">模型连接</h2>
      <span className="badge">{config?.provider === 'chatgpt_desktop' ? 'ChatGPT 协作模式' : 'HTTP 服务模式'}</span>
      <p className="text-gray-400 mt-3 text-sm">{config?.description}</p>
      <p className="text-gray-500 mt-2 text-sm">Skills 提供专业方法，不改变模型连接方式。角色表与相邻格会作为连续性参考交接。</p></section>
    <div className="grid md:grid-cols-[240px_minmax(0,1fr)] gap-5">
      <nav className="space-y-2" aria-label="Agent 列表">{agents.map((a, i) =>
        <button key={a.id} className={'chapter-button ' + (selected === a.id ? 'selected' : '')} onClick={() => setSelected(a.id)}>
          <span className="eyebrow">AGENT 0{i + 1}</span><strong className="block">{a.name}</strong>
          <span className="block text-xs text-gray-400 mt-2">{a.upstream_skills?.map(s => s.name).join(' · ')}</span>
        </button>)}</nav>
      <section className="studio-card min-w-0"><h2 className="font-semibold mb-2">{current?.name}</h2>
        <p className="text-xs text-primary-300 mb-4">{current?.skill}</p>
        {current?.upstream_skills?.map(skill => <article key={skill.name} className="bg-dark-900 border border-dark-600 rounded-xl p-4 mb-5">
          <div className="flex items-center flex-wrap gap-2"><strong>{skill.name}</strong><span className="badge">已安装并加载</span></div>
          <p className="text-sm text-gray-400 mt-3 leading-6">{skill.adaptation}</p>
          <div className="flex flex-wrap gap-4 text-sm text-primary-300 my-3">
            {skill.skillsmp_url && <a href={skill.skillsmp_url} target="_blank" rel="noreferrer">SkillsMP 来源 ↗</a>}
            {skill.github_url && <a href={skill.github_url} target="_blank" rel="noreferrer">GitHub 固定版本 ↗</a>}
          </div>
          <p className="text-xs text-gray-500 break-all">版本 {skill.source_kind==='project-authored'?'项目原创 · MIT':skill.commit?.slice(0, 12)} · {skill.installed_path}</p>
        </article>)}
        <details open><summary className="cursor-pointer text-sm text-gray-300 mb-4">实际运行提示词与技能章节</summary>
          <pre className="prompt-box">{current?.instructions}</pre></details>
      </section>
    </div>
  </div>
}
