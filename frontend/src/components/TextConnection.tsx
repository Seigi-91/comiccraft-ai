import { useEffect, useState } from 'react'
import axios from 'axios'

type TextConfig = { provider: string; text_base_url: string; text_model: string; vision_model: string; text_key_configured: boolean }
export default function TextConnection({ onSaved }: { onSaved?: () => void }) {
  const [config, setConfig] = useState<TextConfig>()
  const [provider, setProvider] = useState('chatgpt_desktop')
  const [base, setBase] = useState('https://api.openai.com/v1')
  const [model, setModel] = useState('')
  const [vision, setVision] = useState('')
  const [key, setKey] = useState('')
  const [clear, setClear] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const apply = (c: TextConfig) => { setConfig(c); setProvider(c.provider); setBase(c.text_base_url); setModel(c.text_model); setVision(c.vision_model) }
  useEffect(() => { axios.get('/api/studio/config').then(r => apply(r.data)).catch(() => setMessage('无法读取文字模型配置')) }, [])
  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setMessage('')
    try {
      const r = await axios.put('/api/studio/config', { text_provider: provider, text_base_url: base, text_model: model, vision_model: vision, text_api_key: key || null, clear_text_key: clear })
      apply(r.data); window.dispatchEvent(new Event('comiccraft-config-saved')); setKey(''); setClear(false); onSaved?.(); setMessage('文字设置已保存。新任务使用此连接，图片连接保持不变；尚未发送付费请求。')
    } catch (error) { setMessage(axios.isAxiosError(error) ? error.response?.data?.detail || '保存失败' : '保存失败') }
    finally { setBusy(false) }
  }
  return <section className="studio-card"><h2 className="font-semibold mb-3">文字与视觉模型连接</h2>
    <p className="text-sm text-gray-400 mb-4">控制大纲、分镜、台词、视觉审核与气泡定位，和图片生成连接分别保存。</p>
    <form onSubmit={save} className="space-y-4">
      <label className="block">文字生成方式<select aria-label="文字生成方式" className="block w-full bg-dark-900 border border-dark-600 rounded-lg p-3 mt-2" value={provider} onChange={e => setProvider(e.target.value)}>
        <option value="chatgpt_desktop">本机 ChatGPT · 协作回填</option><option value="local_http">文字模型 API · 自动生成</option>
      </select></label>
      {provider === 'chatgpt_desktop' ? <p className="text-sm text-gray-400">将待办提示词及参考图交给自己的 ChatGPT，再回填 JSON。切换不会删除已经生成的内容。</p> : <div className="space-y-4">
        <label className="block">文字 API 基础地址<input aria-label="文字 API 基础地址" type="url" required value={base} onChange={e => setBase(e.target.value)} /></label>
        <label className="block">文字模型名称<input aria-label="文字模型名称" required value={model} onChange={e => setModel(e.target.value)} /></label>
        <label className="block">视觉模型名称<input aria-label="视觉模型名称" required value={vision} onChange={e => setVision(e.target.value)} /></label>
        <label className="block">文字 API Key<input aria-label="文字 API Key" type="password" autoComplete="off" value={key} placeholder={config?.text_key_configured ? '已配置；留空保留原密钥' : '填写服务密钥；无鉴权的本地服务可留空'} onChange={e => setKey(e.target.value)} /></label>
        <label className="flex gap-2"><input style={{width:'auto'}} type="checkbox" checked={clear} onChange={e => setClear(e.target.checked)} />清除文字密钥</label>
        <p className="text-xs text-gray-400">接口需兼容 /chat/completions。视觉模型使用同一地址和密钥，须支持 image_url 图片输入；可填写与文字相同的多模态模型。模型须能遵循提示词返回 JSON，厂商私有协议需单独适配。</p>
      </div>}
      <button className="primary-button" disabled={busy || !config}>{busy ? '保存中…' : '保存文字设置'}</button>
      <p role="status" className="text-sm text-primary-300">{message}</p>
      <p className="text-xs text-gray-500">密钥只保存在运行者本机后端 .env，配置读取接口不会返回密钥。保存并不代表账户权限或额度已验证。</p>
    </form></section>
}
