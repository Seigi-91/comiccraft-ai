import { create } from 'zustand'

interface Project {
  id: string
  name: string
  description: string
  inspiration: string
  status: string
  created_at: string
}

interface Chapter {
  id: string
  title: string
  phase: string
  created_at: string
}

interface ProjectStore {
  projects: Project[]
  selectedProject: Project | null
  chapters: Chapter[]
  selectedChapter: Chapter | null
  setProjects: (projects: Project[]) => void
  setSelectedProject: (project: Project | null) => void
  setChapters: (chapters: Chapter[]) => void
  setSelectedChapter: (chapter: Chapter | null) => void
  addProject: (project: Project) => void
  addChapter: (chapter: Chapter) => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  selectedProject: null,
  chapters: [],
  selectedChapter: null,

  setProjects: (projects) => set({ projects }),
  setSelectedProject: (project) => set({ selectedProject: project }),
  setChapters: (chapters) => set({ chapters }),
  setSelectedChapter: (chapter) => set({ selectedChapter: chapter }),

  addProject: (project) =>
    set((state) => ({ projects: [...state.projects, project] })),

  addChapter: (chapter) =>
    set((state) => ({ chapters: [...state.chapters, chapter] })),
}))