import { useState, useEffect, useCallback, useRef } from 'react'
import {
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useThreadRuntime,
  useMessageRuntime,
} from '@assistant-ui/react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useChatRuntimeContext, getScriptReady } from '@/features/chat/chat-runtime-context'
import { useUiStore } from '@/shared/store/ui-store'
import { api } from '@/shared/api/api'
import { Button } from '@/shared/ui/button'

function generateId(): string {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`
}

type AdoptStatus = 'idle' | 'adopting' | 'adopted' | 'error'
type CollectStatus = 'idle' | 'collecting' | 'collected' | 'error'

function MessageWithActions() {
  const { projectId } = useChatRuntimeContext()
  const jumpToScreenplay = useUiStore((s) => s.jumpToScreenplay)
  const queryClient = useQueryClient()
  const messageRuntime = useMessageRuntime()
  const [adoptStatus, setAdoptStatus] = useState<AdoptStatus>('idle')
  const [collectStatus, setCollectStatus] = useState<CollectStatus>('idle')
  const [alreadyCollected, setAlreadyCollected] = useState<boolean>(false)

  const getMessageText = useCallback(() => {
    const message = messageRuntime.getState()
    const parts = message.content as { type: string; text?: string }[]
    return parts
      .filter((p) => p.type === 'text' && p.text)
      .map((p) => p.text)
      .join('\n')
  }, [messageRuntime])

  const getMessageId = useCallback(() => {
    const message = messageRuntime.getState()
    return message.id as string
  }, [messageRuntime])

  // 检查是否已收藏
  useEffect(() => {
    const messageId = getMessageId()
    if (messageId && projectId) {
      fetch(`/api/v1/projects/${projectId}/idea-cards/check/${messageId}`)
        .then((res) => res.json())
        .then((data) => setAlreadyCollected(data.exists))
        .catch(() => setAlreadyCollected(false))
    }
  }, [getMessageId, projectId])

  // 获取 script_ready 状态
  const scriptReady = getScriptReady(getMessageId())

  const adoptMutation = useMutation({
    mutationFn: async () => {
      const text = getMessageText()
      if (!projectId || !text.trim()) return
      return api.adopt(projectId, {
        content: text,
        adopt_request_id: generateId(),
        document_id: 'screenplay',
      })
    },
    onSuccess: () => {
      setAdoptStatus('adopted')
      queryClient.invalidateQueries({ queryKey: ['revisions', projectId] })
    },
    onError: (error) => {
      console.error('Adopt failed:', error)
      setAdoptStatus('error')
    },
  })

  const collectMutation = useMutation({
    mutationFn: async () => {
      const text = getMessageText()
      const messageId = getMessageId()
      if (!projectId || !text.trim()) return
      const res = await fetch(`/api/v1/projects/${projectId}/idea-cards`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: text,
          source: { message_id: messageId, excerpt: text.slice(0, 100) },
          summary: text.slice(0, 50),
          created_from: 'manual',
        }),
      })
      if (!res.ok) throw new Error('Failed to collect')
      return res.json()
    },
    onSuccess: () => {
      setCollectStatus('collected')
      setAlreadyCollected(true)
      queryClient.invalidateQueries({ queryKey: ['idea-cards', projectId] })
    },
    onError: (error) => {
      console.error('Collect failed:', error)
      setCollectStatus('error')
    },
  })

  const handleAdopt = useCallback(() => {
    if (adoptStatus === 'adopted' || adoptStatus === 'adopting') return
    setAdoptStatus('adopting')
    adoptMutation.mutate()
  }, [adoptStatus, adoptMutation])

  const handleCollect = useCallback(() => {
    if (collectStatus === 'collected' || collectStatus === 'collecting' || alreadyCollected) return
    setCollectStatus('collecting')
    collectMutation.mutate()
  }, [collectStatus, alreadyCollected, collectMutation])

  return (
    <MessagePrimitive.Root className="mb-3 flex flex-col items-start">
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-secondary px-3 py-2 text-sm text-secondary-foreground">
        <MessagePrimitive.Parts />
      </div>
      <div className="mt-1 flex gap-1">
        {/* 收藏到创意仓库按钮 */}
        {collectStatus === 'collected' || alreadyCollected ? (
          <span className="text-xs text-muted-foreground">✓ 已收藏</span>
        ) : collectStatus === 'error' ? (
          <span className="text-xs text-destructive">收藏失败</span>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={handleCollect}
            disabled={collectStatus === 'collecting'}
          >
            {collectStatus === 'collecting' ? '收藏中...' : '收藏到创意仓库'}
          </Button>
        )}

        {/* 放入正文按钮 - 仅当 script_ready 为 true 时显示 */}
        {scriptReady && (
          adoptStatus === 'adopted' ? (
            <>
              <span className="text-xs text-muted-foreground">✓ 已放入正文</span>
              <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => jumpToScreenplay()}>
                查看剧本
              </Button>
            </>
          ) : adoptStatus === 'error' ? (
            <>
              <span className="text-xs text-destructive">放入失败</span>
              <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setAdoptStatus('idle')}>
                重试
              </Button>
            </>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={handleAdopt}
              disabled={adoptStatus === 'adopting'}
              data-adopt-btn
            >
              {adoptStatus === 'adopting' ? '处理中...' : '放入正文'}
            </Button>
          )
        )}
      </div>
    </MessagePrimitive.Root>
  )
}

function UserMessage() {
  return (
    <MessagePrimitive.Root className="mb-3 flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-primary px-3 py-2 text-sm text-primary-foreground">
        <MessagePrimitive.Parts />
      </div>
    </MessagePrimitive.Root>
  )
}

function ChatThread() {
  const threadRuntime = useThreadRuntime()
  const { hasMoreMessages, loadingMore, loadMoreMessages } = useChatRuntimeContext()
  const chatPrefill = useUiStore((s) => s.chatPrefill)
  const setChatPrefill = useUiStore((s) => s.setChatPrefill)
  const prefillApplied = useRef(false)

  // 处理预填内容
  useEffect(() => {
    if (chatPrefill && !prefillApplied.current) {
      // 设置输入框内容
      const composer = threadRuntime.composer
      if (composer) {
        composer.setText(chatPrefill)
        prefillApplied.current = true
        // 清除预填状态
        setChatPrefill(null)
      }
    }
  }, [chatPrefill, threadRuntime, setChatPrefill])

  // 当 chatPrefill 变化时重置 prefillApplied
  useEffect(() => {
    if (chatPrefill) {
      prefillApplied.current = false
    }
  }, [chatPrefill])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault()
      threadRuntime.composer.send()
    }
  }, [threadRuntime])

  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'A') {
        e.preventDefault()
        const buttons = document.querySelectorAll('[data-adopt-btn]')
        const lastBtn = buttons[buttons.length - 1] as HTMLButtonElement
        if (lastBtn && !lastBtn.disabled) {
          lastBtn.click()
        }
      }
    }
    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [])

  return (
    <ThreadPrimitive.Root className="flex h-full flex-col">
      <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto px-1 py-2">
        {/* Load More Button */}
        {hasMoreMessages && (
          <div className="mb-2 flex justify-center">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-3 text-xs text-muted-foreground hover:text-foreground"
              onClick={loadMoreMessages}
              disabled={loadingMore}
            >
              {loadingMore ? '加载中...' : '加载更早的消息'}
            </Button>
          </div>
        )}
        <ThreadPrimitive.Empty>
          <div className="flex h-full min-h-32 items-center justify-center text-sm text-muted-foreground">
            随便聊聊你的故事。我在听，不打断。
          </div>
        </ThreadPrimitive.Empty>
        <ThreadPrimitive.Messages
          components={{
            UserMessage: UserMessage,
            AssistantMessage: MessageWithActions,
          }}
        />
      </ThreadPrimitive.Viewport>
      <ComposerPrimitive.Root className="mt-2 flex items-end gap-2 rounded-md border border-border bg-card/70 p-2">
        <ComposerPrimitive.Input
          rows={1}
          autoFocus
          placeholder="写点什么……（Ctrl+Enter 发送）"
          className="flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-muted-foreground"
          onKeyDown={handleKeyDown}
        />
        <ComposerPrimitive.Send asChild>
          <Button size="sm">发送</Button>
        </ComposerPrimitive.Send>
      </ComposerPrimitive.Root>
    </ThreadPrimitive.Root>
  )
}

export function ChatPanel() {
  const { projectId } = useChatRuntimeContext()
  if (!projectId) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        请先选择或新建一个项目
      </div>
    )
  }
  return <ChatThread />
}

