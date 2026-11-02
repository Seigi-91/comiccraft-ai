import { useEffect, useState } from 'react'
import axios from 'axios'

type Config = { image_provider: string; image_base_url: string; image_api_model: string; image_key_configured: boolean }
export default function ModelConnection() {
  const [config, setConfig] = useState<Config>()
  const [provider, setProvider] = useState('chatgpt_desktop')
  const [base, setBase] = useState('https://api.openai.com/v1')
  const [model, setModel] = useState('gpt-image-1')
  const [key, setKey] = useState('')
  const [clear, setClear] = useState(false)
  const [repairs, setRepairs] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const apply = (c: Config) => { setConfig(c); setProvider(c.image_provider); setBase(c.image_base_url); setModel(c.image_api_model) }
  useEffect(() => { axios.get('/api/studio/config').then(r => apply(r.data)).catch(() => setMessage('无法读取模型配置')) }, [])
  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setMessage('')
    try {
      const r = await axios.put('/api/studio/config', { image_provider: provider, image_base_url: base, image_model: model, api_key: key || null, clear_key: clear, use_for_repairs: repairs })
      apply(r.data); window.dispatchEvent(new Event('comiccraft-config-saved')); setKey(''); setClear(false); setMessage('已保存。新的图片任务使用此配置；尚未向模型发送付费请求。')
    } catch (error) { setMessage(axios.isAxiosError(error) ? error.response?.data?.detail || '保存失败' : '保存失败') }
    finally { setBusy(false) }
  }
  return <section className="studio-card"><h2 className="font-semibold mb-3">图片模型连接</h2>
    <p className="text-sm text-gray-400 mb-4">文字与图片可以使用不同服务。这里切换图片生成方式，不会改变文字 agent 的连接。</p>
    <form onSubmit={save} className="space-y-4">
      <label className="block">图片生成方式<select aria-label="图片生成方式" className="block w-full bg-dark-900 border border-dark-600 rounded-lg p-3 mt-2" value={provider} onChange={e => setProvider(e.target.value)}>
        <option value="chatgpt_desktop">本机 ChatGPT · 协作回填，无需 API Key</option><option value="codex_cli">官方 Codex · 内置生图（需实测）</option><option value="openai">图像模型 API · 自动生成</option>
      </select></label>
      {provider === 'chatgpt_desktop' ? <p className="text-sm text-gray-400">生成时在待办中复制提示词、下载参考图，交给你自己的 ChatGPT；将结果上传回填后继续创作。网站不会自动控制桌面客户端，也不读取登录凭据。</p> : provider === 'codex_cli' ? <p className="text-sm text-gray-400">通过官方CLI调用内置生图，使用ChatGPT账户额度，不发送图片API Key。须先在“服务验证”实测图片、参考图及蒙版能力；CLI/账号未提供工具时明确失败，不会生成占位图或自动改用API。图像尺寸和风格是提示词约束，未保证底层参数。</p> : <div className="space-y-4">
        <label className="block">API 基础地址<input aria-label="API 基础地址" type="url" required value={base} onChange={e => setBase(e.target.value)} /></label>
        <label className="block">图像模型名称<input aria-label="图像模型名称" required value={model} onChange={e => setModel(e.target.value)} /></label>
        <label className="block">API Key<input aria-label="API Key" type="password" autoComplete="off" value={key} placeholder={config?.image_key_configured ? '已配置；留空保留原密钥' : '填写你自己的服务密钥'} onChange={e => setKey(e.target.value)} /></label>
        <label className="flex gap-2"><input style={{width:'auto'}} type="checkbox" checked={clear} onChange={e => setClear(e.target.checked)} />清除已保存的密钥</label>
        <p className="text-xs text-gray-400">支持 OpenAI 兼容 /images/generations；角色参考图需要服务同时支持 multipart /images/edits。不同厂商的私有接口不能直接通用，费用由运行者承担。</p>
      </div>}
      <label className="flex gap-2"><input style={{width:'auto'}} type="checkbox" checked={repairs} onChange={e => setRepairs(e.target.checked)} />局部精修同时使用此服务</label>
      <button className="primary-button" disabled={busy || !config}>{busy ? '保存中…' : '保存模型设置'}</button>
      <p role="status" className="text-sm text-primary-300">{message}</p>
      <p className="text-xs text-gray-500">设置保存到运行服务器的 .env，仅允许本机访问。GitHub 展示页为静态介绍，请先在自己的电脑安装完整应用。</p>
    </form></section>
}
