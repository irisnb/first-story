import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ViewKey = 'home' | 'modules' | 'ideas' | 'screenplay' | 'settings'

interface UiState {
  activeView: ViewKey
  currentProjectId: string | null
  /** ChatUI 预填内容（从创意仓库发送） */
  chatPrefill: string | null
  setView: (view: ViewKey) => void
  setProject: (projectId: string | null) => void
  setChatPrefill: (content: string | null) => void
  /** 「直达剧本」：用户需要随时查看剧本，一键跳到编辑器 */
  jumpToScreenplay: () => void
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      activeView: 'home',
      currentProjectId: null,
      chatPrefill: null,
      setView: (view) => set({ activeView: view }),
      setProject: (projectId) => set({ currentProjectId: projectId }),
      setChatPrefill: (content) => set({ chatPrefill: content }),
      jumpToScreenplay: () => set({ activeView: 'screenplay' }),
    }),
    {
      name: 'project-storage',
    }
  )
)
