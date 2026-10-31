import { useState, useEffect } from 'react'
import { Plus, BookOpen, Clock, ChevronRight, Sparkles } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import axios from 'axios'

interface Project {
  id: string
  name: string
  description: string
  status: string
  created_at: string
  chapters: number
}

function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetchProjects()
  }, [])

  async function fetchProjects() {
    try {
      setLoading(true)
      const response = await axios.get('/api/projects')
      setProjects(response.data)
    } catch {
      setError('无法加载项目，请检查服务连接。')
    } finally {
      setLoading(false)
    }
  }

  const statusConfig: Record<string, { label: string; color: string }> = {
    draft: { label: '草稿', color: 'bg-gray-500' },
    active: { label: '进行中', color: 'bg-green-500' },
    completed: { label: '已完成', color: 'bg-primary-500' },
    archived: { label: '已归档', color: 'bg-orange-500' },
  }

  return (
    <div className="space-y-6">
      {error && <p role="alert" className="error-box">{error}</p>}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">我的漫画项目</h1>
          <p className="text-gray-400 mt-1">管理和创作你的 AI 漫画作品</p>
        </div>
        <button
          onClick={() => navigate('/projects')}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 rounded-xl text-white font-semibold transition-all shadow-lg shadow-primary-500/20"
        >
          <Plus className="w-5 h-5" />
          创建新项目
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-48 bg-dark-800 rounded-xl border border-dark-600 animate-pulse"
            />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="w-24 h-24 rounded-full bg-dark-800 flex items-center justify-center mb-6">
            <Sparkles className="w-12 h-12 text-primary-500" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">开始创作你的第一部漫画</h2>
          <p className="text-gray-400 text-center max-w-md mb-6">
            输入灵感，AI 将为你生成完整的漫画剧情、分镜和画面
          </p>
          <button
            onClick={() => navigate('/projects')}
            className="flex items-center gap-2 px-6 py-3 bg-primary-600 hover:bg-primary-700 rounded-lg text-white font-medium transition-colors"
          >
            <Plus className="w-5 h-5" />
            开始创作
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="group bg-dark-800 rounded-xl border border-dark-600 p-6 hover:border-primary-500/50 hover:shadow-lg hover:shadow-primary-500/10 transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary-500/20 to-primary-700/20 flex items-center justify-center">
                  <BookOpen className="w-6 h-6 text-primary-400" />
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusConfig[project.status]?.color} text-white`}>
                  {statusConfig[project.status]?.label}
                </span>
              </div>

              <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-primary-400 transition-colors">
                {project.name}
              </h3>

              {project.description && (
                <p className="text-gray-400 text-sm mb-4 line-clamp-2">
                  {project.description}
                </p>
              )}

              <div className="flex items-center justify-between text-sm text-gray-500">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <BookOpen className="w-4 h-4" />
                    {project.chapters || 0} 章
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-500 group-hover:text-primary-400 group-hover:translate-x-1 transition-all" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default Dashboard