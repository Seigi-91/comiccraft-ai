import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, Sparkles } from 'lucide-react'
import axios from 'axios'

function CreateProject() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [inspiration, setInspiration] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return

    setError('')
    setIsSubmitting(true)
    try {
      const response = await axios.post('/api/projects', {
        name: name.trim(),
        description: description.trim(),
        inspiration: inspiration.trim(),
      })
      navigate(`/projects/${response.data.id}`)
    } catch {
      setError('创建失败，请检查服务连接后重试。')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      {error && <p role="alert" className="error-box">{error}</p>}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/')}
          className="p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">创建新项目</h1>
          <p className="text-gray-400">输入灵感，开始你的漫画创作之旅</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="max-w-2xl space-y-6">
        <div className="bg-dark-800 rounded-xl border border-dark-600 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary-500/20 to-primary-700/20 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-primary-400" />
            </div>
            <div>
              <h2 className="font-semibold text-white">项目基本信息</h2>
              <p className="text-sm text-gray-400">为你的漫画项目设置基本信息</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                项目名称 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 transition-colors"
                placeholder="例如：AI漫画冒险"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                项目描述
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 transition-colors resize-none"
                rows={3}
                placeholder="简短描述你的漫画项目..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                创作灵感
              </label>
              <textarea
                value={inspiration}
                onChange={(e) => setInspiration(e.target.value)}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 transition-colors resize-none"
                rows={4}
                placeholder="输入你的创作灵感，AI 将根据这个生成完整的故事大纲..."
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-4">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-6 py-3 bg-dark-700 hover:bg-dark-600 rounded-lg text-white font-medium transition-colors"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !name.trim()}
            className="flex items-center gap-2 px-6 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-dark-600 disabled:text-gray-500 rounded-lg text-white font-medium transition-colors"
          >
            <Save className="w-5 h-5" />
            {isSubmitting ? '创建中...' : '创建项目'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default CreateProject