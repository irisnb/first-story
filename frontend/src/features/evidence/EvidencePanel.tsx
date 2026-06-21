import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { useAutoAnimate } from '@formkit/auto-animate/react'
import { api } from '@/shared/api/api'
import type { ContinuityEvent } from '@/shared/api/api-types'
import { useUiStore } from '@/shared/store/ui-store'
import { Button } from '@/shared/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/shared/ui/collapsible'

// evidence-panel —— 系统只递证据、不下结论。中性面板，非告警红。
function continuityList(value: unknown): ContinuityEvent[] {
  if (Array.isArray(value)) return value as ContinuityEvent[]
  if (value && typeof value === 'object') {
    const maybe = (value as { events?: unknown }).events
    if (Array.isArray(maybe)) return maybe as ContinuityEvent[]
  }
  return []
}

export function EvidencePanel() {
  const projectId = useUiStore((s) => s.currentProjectId)
  const queryClient = useQueryClient()
  const [listRef] = useAutoAnimate<HTMLDivElement>()

  const { data } = useQuery({
    queryKey: ['state', projectId],
    queryFn: () => api.getState(projectId!),
    enabled: Boolean(projectId),
  })

  const events = continuityList(data?.story.continuity).filter(
    (e) => !e.status || e.status === 'open' || e.status === 'pending',
  )

  const ignoreMutation = useMutation({
    mutationFn: (eventId: string) =>
      api.ignoreContinuity(projectId!, eventId, { scope: 'single_finding' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['state', projectId] }),
  })

  const acceptMutation = useMutation({
    mutationFn: (eventId: string) => api.acceptContinuity(projectId!, eventId, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['state', projectId] }),
  })

  return (
    <aside className="evidence-panel" aria-labelledby="evidence-heading">
      <header className="mb-2">
        <h3 id="evidence-heading" className="text-sm font-semibold">
          证据
        </h3>
        <p className="text-xs text-muted-foreground">只列事实，判断权在你手里。</p>
      </header>

      {!projectId && <p className="text-xs text-muted-foreground">选择项目后，这里显示后台观察到的证据。</p>}
      {projectId && events.length === 0 && (
        <p className="text-xs text-muted-foreground">暂无需要你留意的事。安心写。</p>
      )}

      <div ref={listRef} className="flex flex-col gap-2">
        <AnimatePresence initial={false}>
          {events.map((event) => (
            <motion.div
              key={event.id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, transition: { duration: 0.15 } }}
              transition={{ duration: 0.24, ease: 'easeOut' }}
            >
              <Collapsible className="rounded-md border border-border bg-card/70 p-3">
                <CollapsibleTrigger className="flex w-full items-center justify-between text-left text-sm">
                  <span className="font-medium">
                    {event.type ?? '连续性观察'}
                    {event.severity && (
                      <span className="ml-2 text-xs text-muted-foreground">{event.severity}</span>
                    )}
                  </span>
                  <span className="text-xs text-muted-foreground">展开</span>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2 overflow-hidden data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up">
                  {/* 叠甲：先免责，再事实，不下结论 */}
                  <p className="text-xs text-muted-foreground">
                    按传统连续性的视角，这里有几处可能想确认一下（先锋写法可忽略）：
                  </p>
                  {event.evidence && event.evidence.length > 0 && (
                    <ul className="mt-2 list-disc pl-4 text-xs">
                      {event.evidence.map((ev, i) => (
                        <li key={i}>{ev}</li>
                      ))}
                    </ul>
                  )}
                  <div className="mt-3 flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => ignoreMutation.mutate(event.id)}
                      disabled={ignoreMutation.isPending}
                    >
                      忽略
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => acceptMutation.mutate(event.id)}
                      disabled={acceptMutation.isPending}
                    >
                      接受
                    </Button>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </aside>
  )
}

