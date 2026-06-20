import { useQuery } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { api } from '@/lib/api'
import type { StateResponse } from '@/lib/api-types'
import { useUiStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

// 五大模块（五兄弟）—— 画布只读查看。标签原样：世界观/角色/剧情/主题/结构。
// 标签源头在 App.tsx 的 STORY_MODULE_LABELS，此处与其一一对应。
const MODULES: { key: string; label: string; hint: string }[] = [
  { key: 'world', label: '世界观', hint: '设定、规则、科技水平' },
  { key: 'character', label: '角色', hint: '属性、关系、知识状态' },
  { key: 'plot', label: '剧情', hint: '因果链、激励事件、目标' },
  { key: 'theme', label: '主题', hint: '母题、表达、价值取向' },
  { key: 'structure', label: '结构', hint: '幕、节奏、转折点' },
]

function moduleCount(state: StateResponse | undefined, key: string): number | null {
  if (!state) return null
  const s = state.story
  switch (key) {
    case 'character':
      return s.characters?.length ?? 0
    case 'plot':
      return s.plot_events?.length ?? 0
    default:
      return null
  }
}

export function ModulesView() {
  const projectId = useUiStore((s) => s.currentProjectId)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['state', projectId],
    queryFn: () => api.getState(projectId!),
    enabled: Boolean(projectId),
  })

  return (
    <section className="view-shell" aria-labelledby="modules-heading">
      <header className="mb-4">
        <h2 id="modules-heading" className="text-lg font-semibold">
          五兄弟
        </h2>
        <p className="text-sm text-muted-foreground">
          世界观 · 角色 · 剧情 · 主题 · 结构 —— 只读查看，螺旋迭代，永不替你下定论。
        </p>
      </header>

      <div className="story-module-grid">
        {MODULES.map((m, i) => {
          const count = moduleCount(data, m.key)
          return (
            <motion.div
              key={m.key}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.24, delay: i * 0.04, ease: 'easeOut' }}
            >
              <Card className="h-full">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{m.label}</span>
                    {count !== null && (
                      <span className="text-xs font-normal text-muted-foreground">
                        {count} 条
                      </span>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{m.hint}</p>
                  {!projectId && (
                    <p className="mt-3 text-xs text-muted-foreground">先选择或新建项目</p>
                  )}
                  {projectId && isLoading && (
                    <p className="mt-3 text-xs text-muted-foreground">读取投影中…</p>
                  )}
                  {projectId && isError && (
                    <p className="mt-3 text-xs text-muted-foreground">暂无数据</p>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>
    </section>
  )
}
