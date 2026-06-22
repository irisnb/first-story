import { createContext, useContext, useMemo, useState, useEffect, useCallback, type ReactNode } from 'react'
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
  type ThreadMessageLike,
} from '@assistant-ui/react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/api'
import { useUiStore } from '@/shared/store/ui-store'
import type { ChatMessage } from '@/shared/api/api-types'

// 存储 message_id -> script_ready 的映射
const scriptReadyMap = new Map<string, boolean>()

export function getScriptReady(messageId: string): boolean {
  return scriptReadyMap.get(messageId) ?? false
}

// 从 messages 提取最新用户文本
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

// 转换后端消息格式为 ThreadMessageLike
function toThreadMessageLike(msg: ChatMessage): ThreadMessageLike {
  // 存储 script_ready 信息
  if (msg.script_ready) {
    scriptReadyMap.set(msg.message_id, msg.script_ready)
  }
  return {
    role: msg.role,
    content: [{ type: 'text', text: msg.content }],
    id: msg.message_id,
    createdAt: msg.timestamp ? new Date(msg.timestamp) : undefined,
  }
}

// Context 值：当前 projectId + 分页状态
interface ChatRuntimeContextValue {
  projectId: string | null
  hasMoreMessages: boolean
  loadingMore: boolean
  loadMoreMessages: () => void
}

const ChatRuntimeContext = createContext<ChatRuntimeContextValue>({
  projectId: null,
  hasMoreMessages: false,
  loadingMore: false,
  loadMoreMessages: () => {},
})

export function useChatRuntimeContext() {
  return useContext(ChatRuntimeContext)
}

export function ChatRuntimeProvider({ children }: { children: ReactNode }) {
  const projectId = useUiStore((s) => s.currentProjectId)

  // 无项目时只提供 context，不创建 runtime
  if (!projectId) {
    return (
      <ChatRuntimeContext.Provider value={{ projectId: null, hasMoreMessages: false, loadingMore: false, loadMoreMessages: () => {} }}>
        {children}
      </ChatRuntimeContext.Provider>
    )
  }

  // 有项目时使用 ChatRuntimeInner 创建 runtime
  // key=projectId 确保切换项目时完全重建 runtime
  return <ChatRuntimeInnerWithProvider key={projectId} projectId={projectId}>{children}</ChatRuntimeInnerWithProvider>
}

// 包装组件：确保 Context Provider 和 Runtime Provider 在同一组件树中
function ChatRuntimeInnerWithProvider({ projectId, children }: { projectId: string; children: ReactNode }) {
  const { runtime, hasMoreMessages, loadingMore, loadMoreMessages, initialMessages, loadError } = useChatRuntime(projectId)

  // 等待历史加载完成
  if (initialMessages === null) {
    return (
      <ChatRuntimeContext.Provider value={{ projectId, hasMoreMessages: false, loadingMore: false, loadMoreMessages: () => {} }}>
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          {loadError ? '聊天历史加载失败，请刷新重试' : '加载聊天历史...'}
        </div>
      </ChatRuntimeContext.Provider>
    )
  }

  return (
    <ChatRuntimeContext.Provider value={{ projectId, hasMoreMessages: hasMoreMessages, loadingMore, loadMoreMessages }}>
      <AssistantRuntimeProvider runtime={runtime}>
        {children}
      </AssistantRuntimeProvider>
    </ChatRuntimeContext.Provider>
  )
}

// 自定义 hook：提取 runtime 创建逻辑
function useChatRuntime(projectId: string) {
  const queryClient = useQueryClient()
  const [initialMessages, setInitialMessages] = useState<ThreadMessageLike[] | null>(null)
  const [loadError, setLoadError] = useState<boolean>(false)
  const [hasMore, setHasMore] = useState<boolean>(false)
  const [loadingMore, setLoadingMore] = useState<boolean>(false)
  const [oldestMessageId, setOldestMessageId] = useState<string | null>(null)

  // 加载聊天历史
  useEffect(() => {
    setInitialMessages(null)
    setLoadError(false)
    setHasMore(false)
    setOldestMessageId(null)
    
    api.getChatMessages(projectId)
      .then((res) => {
        const messages = res.messages.map(toThreadMessageLike)
        setInitialMessages(messages)
        setHasMore(res.has_more)
        if (res.messages.length > 0) {
          setOldestMessageId(res.messages[0].message_id)
        }
      })
      .catch((err) => {
        console.error('Failed to load chat history:', err)
        setLoadError(true)
        setInitialMessages([])
      })
  }, [projectId])

  // 加载更多消息
  const loadMoreMessages = useCallback(() => {
    if (!oldestMessageId || loadingMore || !hasMore) return
    
    setLoadingMore(true)
    api.getChatMessages(projectId, oldestMessageId)
      .then((res) => {
        if (res.messages.length > 0) {
          const olderMessages = res.messages.map(toThreadMessageLike)
          // Prepend to existing messages
          setInitialMessages(prev => prev ? [...olderMessages, ...prev] : olderMessages)
          setHasMore(res.has_more)
          setOldestMessageId(res.messages[0].message_id)
        } else {
          setHasMore(false)
        }
      })
      .catch((err) => {
        console.error('Failed to load more messages:', err)
      })
      .finally(() => {
        setLoadingMore(false)
      })
  }, [projectId, oldestMessageId, loadingMore, hasMore])

  const adapter = useMemo<ChatModelAdapter>(
    () => ({
      async run({ messages, abortSignal }) {
        const message = latestUserText(messages)
        const res = await api.chat(projectId, { message })
        if (abortSignal.aborted) {
          return { content: [{ type: 'text', text: '' }] }
        }
        // 存储 script_ready 信息
        if (res.script_ready && res.message_id) {
          scriptReadyMap.set(res.message_id, res.script_ready)
        }
        // candidate 轮会在后台排队抽取 → 刷新证据/投影
        if (res.intent === 'candidate') {
          queryClient.invalidateQueries({ queryKey: ['state', projectId] })
          queryClient.invalidateQueries({ queryKey: ['idea-cards', projectId] })
          setTimeout(() => {
            queryClient.invalidateQueries({ queryKey: ['state', projectId] })
            queryClient.invalidateQueries({ queryKey: ['idea-cards', projectId] })
          }, 2000)
        }
        return { content: [{ type: 'text', text: res.reply }] }
      },
    }),
    [projectId, queryClient],
  )

  const runtime = useLocalRuntime(adapter, { initialMessages: initialMessages || [] })

  return { runtime, hasMoreMessages: hasMore, loadingMore, loadMoreMessages, initialMessages, loadError }
}


