import { ChatPanel } from './ChatPanel'
import { EvidencePanel } from './EvidencePanel'
import { useUiStore } from '@/lib/store'
import { Button } from '@/components/ui/button'

export function HomeView() {
  const jumpToManuscript = useUiStore((s) => s.jumpToManuscript)

  return (
    <section className="view-shell flex flex-col" aria-labelledby="home-heading">
      <header className="mb-3 flex items-center justify-between">
        <div>
          <h2 id="home-heading" className="text-lg font-semibold">
            主界面
          </h2>
          <p className="text-xs text-muted-foreground">聊着聊着，故事就长出来了。</p>
        </div>
        {/* 直达正文：用户需要随时查看正文 */}
        <Button variant="outline" size="sm" onClick={jumpToManuscript}>
          直达正文
        </Button>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-[1fr_300px]">
        <div className="flex min-h-0 flex-col rounded-md border border-border bg-card/40 p-2">
          <ChatPanel />
        </div>
        <div className="min-h-0 overflow-y-auto">
          <EvidencePanel />
        </div>
      </div>
    </section>
  )
}
