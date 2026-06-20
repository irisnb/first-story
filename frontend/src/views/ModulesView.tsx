import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { api } from '@/lib/api'
import type { StateResponse } from '@/lib/api-types'
import { useUiStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

// 五大模块（五兄弟）—— 画布只读查看。标签原样：世界观/角色/剧情/主题/结构。
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
    case 'world':
      return s.facts?.length ?? 0
    case 'character':
      return s.characters?.length ?? 0
    case 'plot':
      return s.plot_events?.length ?? 0
    default:
      return null
  }
}

// 角色详情组件
function CharacterList({ state }: { state: StateResponse | undefined }) {
  const characters = state?.story?.characters ?? []
  if (characters.length === 0) {
    return <p className="text-xs text-muted-foreground">暂无角色。在聊天中提到角色名，系统会自动识别。</p>
  }
  return (
    <ul className="space-y-2">
      {characters.map((char) => (
        <li
          key={char.id}
          className="rounded-md border border-border bg-card/50 p-2 text-sm"
        >
          <div className="flex items-center justify-between">
            <span className="font-medium">{char.name}</span>
            {char.acceptance_status === 'candidate' && (
              <span className="text-xs text-muted-foreground">（候选）</span>
            )}
          </div>
          {char.gender && (
            <p className="text-xs text-muted-foreground">性别：{char.gender}</p>
          )}
        </li>
      ))}
    </ul>
  )
}

// Facts 详情组件
function FactsList({ state }: { state: StateResponse | undefined }) {
  const facts = state?.story?.facts ?? []
  if (facts.length === 0) {
    return <p className="text-xs text-muted-foreground">暂无设定。</p>
  }
  return (
    <ul className="space-y-2 max-h-64 overflow-y-auto">
      {facts.slice(-10).reverse().map((fact) => (
        <li
          key={fact.id}
          className="rounded-md border border-border bg-card/50 p-2 text-sm"
        >
          <p>{fact.content}</p>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            {fact.acceptance_status === 'candidate' && (
              <span className="rounded bg-muted px-1">候选</span>
            )}
            {fact.about_character_names && fact.about_character_names.length > 0 && (
              <span>角色：{fact.about_character_names.join('、')}</span>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

// PlotEvents 详情组件
function PlotEventList({ state }: { state: StateResponse | undefined }) {
  const plotEvents = state?.story?.plot_events ?? []
  if (plotEvents.length === 0) {
    return <p className="text-xs text-muted-foreground">暂无情节事件。在聊天中描述关键情节，系统会自动识别。</p>
  }
  return (
    <ul className="space-y-2 max-h-64 overflow-y-auto">
      {plotEvents.slice(-10).reverse().map((pe) => (
        <li
          key={pe.id}
          className="rounded-md border border-border bg-card/50 p-2 text-sm"
        >
          <p className="font-medium">{pe.summary}</p>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            {pe.acceptance_status === 'candidate' && (
              <span className="rounded bg-muted px-1">候选</span>
            )}
            {pe.participant_character_names && pe.participant_character_names.length > 0 && (
              <span>参与：{pe.participant_character_names.join('、')}</span>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

export function ModulesView() {
  const projectId = useUiStore((s) => s.currentProjectId)
  const [expandedKey, setExpandedKey] = useState<string | null>(null)

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

      {!projectId && (
        <p className="text-sm text-muted-foreground">请先选择或新建一个项目</p>
      )}

      {projectId && isLoading && (
        <p className="text-sm text-muted-foreground">读取投影中…</p>
      )}

      {projectId && isError && (
        <p className="text-sm text-muted-foreground">加载失败，请重试</p>
      )}

      {projectId && data && (
        <div className="story-module-grid">
          {MODULES.map((m, i) => {
            const count = moduleCount(data, m.key)
            const isExpanded = expandedKey === m.key

            return (
              <motion.div
                key={m.key}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.24, delay: i * 0.04, ease: 'easeOut' }}
              >
                <Collapsible
                  open={isExpanded}
                  onOpenChange={(open) => setExpandedKey(open ? m.key : null)}
                >
                  <CollapsibleTrigger asChild>
                    <Card className="h-full cursor-pointer transition-colors hover:border-primary/50">
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
                        <p className="mt-2 text-xs text-primary">点击展开详情</p>
                      </CardContent>
                    </Card>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <Card className="mt-2 border-primary/30">
                      <CardContent className="pt-4">
                        {m.key === 'character' && <CharacterList state={data} />}
                        {m.key === 'world' && (
                          <FactsList state={data} />
                        )}
                        {m.key === 'plot' && (
                          <PlotEventList state={data} />
                        )}
                        {m.key === 'theme' && (
                          <p className="text-xs text-muted-foreground">
                            主题分析功能开发中…
                          </p>
                        )}
                        {m.key === 'structure' && (
                          <p className="text-xs text-muted-foreground">
                            结构分析功能开发中…
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  </CollapsibleContent>
                </Collapsible>
              </motion.div>
            )
          })}
        </div>
      )}
    </section>
  )
}
