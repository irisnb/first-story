import { Suspense, lazy } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/shared/ui/button'

const ChatFeature = lazy(() => import('@/features/chat'))
const EvidencePanelLazy = lazy(() => import('@/features/evidence').then(m => ({ default: m.EvidencePanel })))

export function HomeView() {
  const navigate = useNavigate()

  return (
    <section className="view-shell flex flex-col" aria-labelledby="home-heading">
      <header className="mb-3 flex items-center justify-between">
        <div>
          <h2 id="home-heading" className="text-lg font-semibold">
            主界面
          </h2>
          <p className="text-xs text-muted-foreground">聊着聊着，故事就长出来了。</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => navigate('/manuscript')}>
          直达正文
        </Button>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-[1fr_300px]">
        <div className="flex min-h-0 flex-col rounded-md border border-border bg-card/40 p-2">
          <Suspense fallback={<div className="p-3 text-sm text-muted-foreground">加载聊天...</div>}>
            <ChatFeature />
          </Suspense>
        </div>
        <div className="min-h-0 overflow-y-auto">
          <Suspense fallback={<div className="p-3 text-sm text-muted-foreground">加载证据...</div>}>
            <EvidencePanelLazy />
          </Suspense>
        </div>
      </div>
    </section>
  )
}
