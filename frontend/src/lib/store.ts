import { create } from 'zustand'

export type ViewKey = 'home' | 'modules' | 'manuscript' | 'settings'

interface UiState {
  activeView: ViewKey
  currentProjectId: string | null
  setView: (view: ViewKey) => void
  setProject: (projectId: string | null) => void
  /** 「直达正文」：用户需要随时查看正文，一键跳到编辑器 */
  jumpToManuscript: () => void
}

export const useUiStore = create<UiState>((set) => ({
  activeView: 'home',
  currentProjectId: null,
  setView: (view) => set({ activeView: view }),
  setProject: (projectId) => set({ currentProjectId: projectId }),
  jumpToManuscript: () => set({ activeView: 'manuscript' }),
}))
