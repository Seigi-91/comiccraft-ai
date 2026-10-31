import { BookOpen, Plus, Settings } from 'lucide-react'
import { NavLink, Link } from 'react-router-dom'

export default function Header() {
 return <header className="border-b border-dark-600 bg-dark-800/95 sticky top-0 z-40 backdrop-blur"><div className="container mx-auto px-4 py-4 flex flex-wrap items-center justify-between gap-4">
 <Link to="/" className="flex gap-3 items-center"><span className="p-2 bg-primary-600 rounded-xl"><BookOpen size={24}/></span><div><strong className="text-lg">ComicCraft<span className="text-primary-400"> AI</span></strong><p className="text-xs text-gray-500">多智能体漫画创作工作室</p></div></Link>
 <nav className="flex gap-4 sm:gap-6 text-sm" aria-label="主导航"><NavLink to="/" className={({isActive})=>isActive?'text-primary-300':'text-gray-400'}>项目</NavLink><NavLink to="/studio" className={({isActive})=>'flex items-center gap-1 '+(isActive?'text-primary-300':'text-gray-400')}><Settings size={16}/>创作团队</NavLink><NavLink to="/projects" className="flex items-center gap-1 text-gray-300"><Plus size={16}/>新建项目</NavLink></nav>
 </div></header>
}
