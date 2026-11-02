import { useEffect, useState } from 'react'
import axios from 'axios'
type Status={installed:boolean;chatgpt_logged_in:boolean;version:string|null;detail:string;model_requests:number}
export default function CodexConnection(){
 const [status,setStatus]=useState<Status>(),[busy,setBusy]=useState(false),[message,setMessage]=useState('')
 async function refresh(){setBusy(true);setMessage('');try{setStatus((await axios.get('/api/codex/status')).data)}catch{setMessage('无法检查连接器；此检查仅允许在后端本机访问。')}finally{setBusy(false)}}
 useEffect(()=>{refresh()},[])
 return <section className="studio-card space-y-3"><h2 className="font-semibold">官方 Codex 自动连接 · ChatGPT 登录</h2><p className="text-sm text-gray-400">安装官方CLI并登录自己的ChatGPT后，网站可自动提交文字、附图任务并接收结果。使用账户额度，模型仍在云端运行；这不是离线模型，也不操控聊天窗口。</p><p className="text-sm">{status?`${status.installed?'已安装':'未安装'} · ${status.version||'版本未知'} · ${status.chatgpt_logged_in?'ChatGPT已登录':'未确认ChatGPT登录'}`:'检查连接器中…'}</p><p className="text-sm text-gray-400">{status?.detail}</p><div className="flex gap-3 flex-wrap"><a className="secondary-button" href="/api/codex/installer">下载安装 / 登录助手 ZIP</a><button className="secondary-button" disabled={busy} onClick={refresh}>刷新连接器状态（不调用模型）</button></div><p className="text-xs text-gray-400">解压后Windows双击Install-Codex-Connector.cmd；macOS/Linux运行scripts/install_codex.sh。需要Node.js 20+及网络，登录由官方页面完成。安装成功不代表图片能力可用，请在下方选择Codex后显式验证文字、视觉和图片；失败不会自动切换到API或人工回填。</p><p role="status" className="text-sm text-primary-300">{message}</p></section>
}
