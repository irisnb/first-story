import { useMemo } from 'react'
import {
  AssistantRuntimeProvider,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useLocalRuntime,
  type ChatModelAdapter,
} from '@assistant-ui/react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useUiStore } from '@/lib/store'
import { Button } from '@/components/ui/button'

// 把 assistant-ui 的消息转成纯文本（我们后端是单轮、非流式）
function latestUserText(messages: readonly { role: string; content: unknown }[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]
    if (m.role !== 'user') continue
    const parts = m.content as { type: string; text?: string }[]
    return parts
      .filter((p) => p.type === 'text' && p.text)
      .map((p) => p.text)
      .join('\n')
  }
  return ''
}

function ChatThread() {
  return (
    <ThreadPrimitive.Root className="flex h-full flex-col">
      <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto px-1 py-2">
        <ThreadPrimitive.Empty>
          <div className="flex h-full min-h-32 items-center justify-center text-sm text-muted-foreground">
            随便聊聊你的故事。我在听，不打断。
          </div>
        </ThreadPrimitive.Empty>
        <ThreadPrimitive.Messages
          components={{
            UserMessage: () => (
              <MessagePrimitive.Root className="mb-3 flex justify-end">
                <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-primary px-3 py-2 text-sm text-primary-foreground">
                  <MessagePrimitive.Parts />
                </div>
              </MessagePrimitive.Root>
            ),
            AssistantMessage: () => (
              <MessagePrimitive.Root className="mb-3 flex justify-start">
                <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-secondary px-3 py-2 text-sm text-secondary-foreground">
                  <MessagePrimitive.Parts />
                </div>
              </MessagePrimitive.Root>
            ),
          }}
        />
      </ThreadPrimitive.Viewport>

      <ComposerPrimitive.Root className="mt-2 flex items-end gap-2 rounded-md border border-border bg-card/70 p-2">
        <ComposerPrimitive.Input
          rows={1}
          autoFocus
          placeholder="写点什么……"
          className="flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-muted-foreground"
        />
        <ComposerPrimitive.Send asChild>
          <Button size="sm">发送</Button>
        </ComposerPrimitive.Send>
      </ComposerPrimitive.Root>
    </ThreadPrimitive.Root>
  )
}

export function ChatPanel() {
  const projectId = useUiStore((s) => s.currentProjectId)
  const queryClient = useQueryClient()

  const adapter = useMemo<ChatModelAdapter>(
    () => ({
      async run({ messages, abortSignal }) {
        if (!projectId) {
          return { content: [{ type: 'text', text: '请先选择或新建一个项目，我们再开始。' }] }
        }
        const message = latestUserText(messages)
        const res = await api.chat(projectId, { message })
        if (abortSignal.aborted) {
          return { content: [{ type: 'text', text: '' }] }
        }
        // candidate 轮会在后台排队抽取 → 刷新证据/投影
        if (res.intent === 'candidate') {
          queryClient.invalidateQueries({ queryKey: ['state', projectId] })
        }
        return { content: [{ type: 'text', text: res.reply }] }
      },
    }),
    [projectId, queryClient],
  )

  const runtime = useLocalRuntime(adapter)

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ChatThread />
    </AssistantRuntimeProvider>
  )
}
