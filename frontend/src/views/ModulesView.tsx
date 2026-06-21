import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { api } from '@/lib/api'
import { useUiStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import type { ModuleResponse, LockResponse } from '@/lib/api-types'

// 五大模块（五兄弟）
const MODULES: { key: string; label: string; hint: string }[] = [
  { key: 'world', label: '世界观', hint: '设定、规则、科技水平' },
  { key: 'characters', label: '角色', hint: '属性、关系、知识状态' },
  { key: 'plot', label: '情节', hint: '因果链、激励事件、目标' },
  { key: 'theme', label: '主题', hint: '母题、表达、价值取向' },
  { key: 'structure', label: '结构', hint: '幕、节奏、转折点' },
]

// Markdown 渲染器（简单版）
function MarkdownPreview({ content }: { content: string }) {
  const lines = content.split('\n')
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      {lines.map((line, i) => {
        if (line.startsWith('# ')) {
          return (
            <h1 key={i} className="text-lg font-bold">
              {line.slice(2)}
            </h1>
          )
        }
        if (line.startsWith('## ')) {
          return (
            <h2 key={i} className="text-base font-semibold mt-4 mb-2">
              {line.slice(3)}
            </h2>
          )
        }
        if (line.startsWith('- ')) {
          return (
            <li key={i} className="ml-4 text-sm">
              {line.slice(2)}
            </li>
          )
        }
        if (line.trim() === '') {
          return <br key={i} />
        }
        return (
          <p key={i} className="text-sm">
            {line}
          </p>
        )
      })}
    </div>
  )
}

// 模块编辑器组件
function ModuleEditor({
  projectId,
  moduleName,
  module,
  onClose,
}: {
  projectId: string
  moduleName: string
  module: ModuleResponse
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [content, setContent] = useState(module.content)
  const [lock, setLock] = useState<LockResponse | null>(null)
  const [lockError, setLockError] = useState<string | null>(null)

  // 获取锁
  const acquireLock = useMutation({
    mutationFn: () => api.acquireLock(projectId, moduleName),
    onSuccess: (data) => {
      setLock(data)
      setLockError(null)
    },
    onError: (err: Error) => {
      setLockError(err.message)
    },
  })

  // 释放锁
  const releaseLock = useMutation({
    mutationFn: () => api.releaseLock(projectId, moduleName),
    onSuccess: () => {
      setLock(null)
    },
  })

  // 更新模块
  const updateModule = useMutation({
    mutationFn: () =>
      api.updateModule(projectId, moduleName, {
        content,
        revision: module.revision,
        checksum: module.checksum,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['module', projectId, moduleName] })
      releaseLock.mutate()
      onClose()
    },
  })

  // 自动获取锁
  useEffect(() => {
    if (!lock) {
      acquireLock.mutate()
    }
  }, [])

  // 心跳续期
  useEffect(() => {
    if (!lock) return
    const interval = setInterval(() => {
      api.extendLock(projectId, moduleName).catch(() => {
        setLockError('锁已过期')
        setLock(null)
      })
    }, 30000)
    return () => clearInterval(interval)
  }, [lock, projectId, moduleName])

  // 清理：关闭时释放锁
  useEffect(() => {
    return () => {
      if (lock) {
        api.releaseLock(projectId, moduleName).catch(() => {})
      }
    }
  }, [])

  return (
    <div className="space-y-4">
      {lockError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-2 text-sm text-destructive">
          {lockError}
        </div>
      )}

      {!lock && !lockError && (
        <p className="text-sm text-muted-foreground">正在获取编辑锁...</p>
      )}

      {lock && (
        <>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold">
              编辑中
            </span>
            <span className="text-xs text-muted-foreground">
              修订 {module.revision} · {module.checksum.slice(0, 8)}
            </span>
          </div>

          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="min-h-[300px] w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm"
            placeholder="在此编辑 Markdown 内容..."
          />

          <div className="flex gap-2">
            <Button
              onClick={() => updateModule.mutate()}
              disabled={updateModule.isPending}
              size="sm"
            >
              {updateModule.isPending ? '保存中...' : '保存'}
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                releaseLock.mutate()
                onClose()
              }}
              size="sm"
            >
              取消
            </Button>
          </div>
        </>
      )}
    </div>
  )
}

// 模块卡片组件
function ModuleCard({
  projectId,
  moduleName,
  label,
  hint,
}: {
  projectId: string
  moduleName: string
  label: string
  hint: string
}) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['module', projectId, moduleName],
    queryFn: () => api.getModule(projectId, moduleName),
    enabled: expanded,
  })

  // 统计 section 数量
  const sectionCount = data?.sections
    ? Object.values(data.sections).filter((s) => s.trim()).length
    : 0

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded}>
      <CollapsibleTrigger asChild>
        <Card className="h-full cursor-pointer transition-colors hover:border-primary/50">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>{label}</span>
              {sectionCount > 0 && (
                <span className="text-xs font-normal text-muted-foreground">
                  {sectionCount} 个章节
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{hint}</p>
            <p className="mt-2 text-xs text-primary">点击查看详情</p>
          </CardContent>
        </Card>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <Card className="mt-2 border-primary/30">
          <CardContent className="pt-4">
            {isLoading && <p className="text-sm text-muted-foreground">加载中...</p>}
            {isError && (
              <p className="text-sm text-muted-foreground">加载失败，请重试</p>
            )}
            {data && !editing && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold">
                    修订 {data.revision}
                  </span>
                  <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                    编辑
                  </Button>
                </div>
                <MarkdownPreview content={data.content} />
              </div>
            )}
            {data && editing && (
              <ModuleEditor
                projectId={projectId}
                moduleName={moduleName}
                module={data}
                onClose={() => setEditing(false)}
              />
            )}
          </CardContent>
        </Card>
      </CollapsibleContent>
    </Collapsible>
  )
}

export function ModulesView() {
  const projectId = useUiStore((s) => s.currentProjectId)

  return (
    <section className="view-shell" aria-labelledby="modules-heading">
      <header className="mb-4">
        <h2 id="modules-heading" className="text-lg font-semibold">
          五兄弟
        </h2>
        <p className="text-sm text-muted-foreground">
          世界观 · 角色 · 情节 · 主题 · 结构 —— 可编辑的模块文档，螺旋迭代，永不替你下定论。
        </p>
      </header>

      {!projectId && (
        <p className="text-sm text-muted-foreground">请先选择或新建一个项目</p>
      )}

      {projectId && (
        <div className="story-module-grid">
          {MODULES.map((m, i) => (
            <motion.div
              key={m.key}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.24, delay: i * 0.04, ease: 'easeOut' }}
            >
              <ModuleCard
                projectId={projectId}
                moduleName={m.key}
                label={m.label}
                hint={m.hint}
              />
            </motion.div>
          ))}
        </div>
      )}
    </section>
  )
}
