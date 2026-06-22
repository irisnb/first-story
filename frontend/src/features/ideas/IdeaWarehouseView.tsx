import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/shared/api/api'
import { useUiStore } from '@/shared/store/ui-store'
import { Button } from '@/shared/ui/button'
import type { IdeaCard, IdeaCardRevision, IdeaCardStatus } from './idea-cards'

// 扩展 api 类型
declare module '@/shared/api/api' {
  interface api {
    listIdeaCards: (projectId: string) => Promise<{ cards: IdeaCard[]; revisions: IdeaCardRevision[] }>
    createIdeaCard: (projectId: string, content: string, source?: { message_id?: string; excerpt: string }) => Promise<{ card: IdeaCard; revision: IdeaCardRevision }>
    updateIdeaCard: (projectId: string, cardId: string, content: string) => Promise<{ card: IdeaCard; revision: IdeaCardRevision }>
    deleteIdeaCard: (projectId: string, cardId: string) => Promise<void>
    updateIdeaCardStatus: (projectId: string, cardId: string, status: IdeaCardStatus) => Promise<IdeaCard>
  }
}

// 临时扩展 api 对象（后端 API 实现后会移除）
const ideaApi = {
  listIdeaCards: async (projectId: string) => {
    const res = await fetch(`/api/v1/projects/${projectId}/idea-cards`)
    if (!res.ok) throw new ApiError(res.status, 'Failed to load cards', await res.text())
    return res.json()
  },
  createIdeaCard: async (
    projectId: string, 
    content: string, 
    source?: { message_id?: string; excerpt: string },
    summary?: string,
    created_from?: 'auto' | 'manual'
  ) => {
    const res = await fetch(`/api/v1/projects/${projectId}/idea-cards`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, source, summary, created_from }),
    })
    if (!res.ok) throw new ApiError(res.status, 'Failed to create card', await res.text())
    return res.json()
  },
  updateIdeaCard: async (projectId: string, cardId: string, content: string) => {
    const res = await fetch(`/api/v1/projects/${projectId}/idea-cards/${cardId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!res.ok) throw new ApiError(res.status, 'Failed to update card', await res.text())
    return res.json()
  },
  deleteIdeaCard: async (projectId: string, cardId: string) => {
    const res = await fetch(`/api/v1/projects/${projectId}/idea-cards/${cardId}`, {
      method: 'DELETE',
    })
    if (!res.ok && res.status !== 204) throw new ApiError(res.status, 'Failed to delete card', await res.text())
  },
  updateIdeaCardStatus: async (projectId: string, cardId: string, status: IdeaCardStatus) => {
    const res = await fetch(`/api/v1/projects/${projectId}/idea-cards/${cardId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    if (!res.ok) throw new ApiError(res.status, 'Failed to update status', await res.text())
    return res.json()
  },
}

export function IdeaWarehouseView() {
  const projectId = useUiStore((s) => s.currentProjectId)
  const queryClient = useQueryClient()
  const [editingCardId, setEditingCardId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [newCardContent, setNewCardContent] = useState('')
  const [selectedCards, setSelectedCards] = useState<Set<string>>(new Set()) // 勾选的卡片

  // 加载卡片列表
  const { data: cardsData, isLoading } = useQuery({
    queryKey: ['idea-cards', projectId],
    queryFn: () => ideaApi.listIdeaCards(projectId!),
    enabled: Boolean(projectId),
  })

  // 创建卡片
  const createMutation = useMutation({
    mutationFn: (content: string) => ideaApi.createIdeaCard(projectId!, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['idea-cards', projectId] })
      setNewCardContent('')
    },
  })

  // 更新卡片
  const updateMutation = useMutation({
    mutationFn: ({ cardId, content }: { cardId: string; content: string }) =>
      ideaApi.updateIdeaCard(projectId!, cardId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['idea-cards', projectId] })
      setEditingCardId(null)
      setEditContent('')
    },
  })

  // 删除卡片
  const deleteMutation = useMutation({
    mutationFn: (cardId: string) => ideaApi.deleteIdeaCard(projectId!, cardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['idea-cards', projectId] })
    },
  })

  // 更新状态
  const statusMutation = useMutation({
    mutationFn: ({ cardId, status }: { cardId: string; status: IdeaCardStatus }) =>
      ideaApi.updateIdeaCardStatus(projectId!, cardId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['idea-cards', projectId] })
    },
  })

  // 获取卡片内容
  const getCardContent = (cardId: string): string => {
    if (!cardsData) return ''
    const revision = cardsData.revisions.find((r: IdeaCardRevision) => r.revision_id === cardsData.cards.find((c: IdeaCard) => c.id === cardId)?.current_revision_id)
    return revision?.content ?? ''
  }

  // 发送给 ChatUI（预填输入框）
  const setChatPrefill = useUiStore((s) => s.setChatPrefill)
  const setView = useUiStore((s) => s.setView)

  const sendToChat = (content: string) => {
    setChatPrefill(content)
    setView('home') // 跳转到主界面（ChatUI）
  }

  if (!projectId) {
    return (
      <section className="view-shell" aria-labelledby="ideas-heading">
        <h2 id="ideas-heading" className="text-lg font-semibold">
          创意仓库
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">先选择或新建项目，再管理创意卡片。</p>
      </section>
    )
  }

  if (isLoading) {
    return (
      <section className="view-shell" aria-labelledby="ideas-heading">
        <h2 id="ideas-heading" className="text-lg font-semibold">
          创意仓库
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">加载中...</p>
      </section>
    )
  }

  const cards = cardsData?.cards ?? []
  const activeCards = cards.filter((c: IdeaCard) => c.status === 'active')
  const shelvedCards = cards.filter((c: IdeaCard) => c.status === 'shelved')

  return (
    <section className="view-shell flex flex-col" aria-labelledby="ideas-heading">
      <header className="mb-3">
        <h2 id="ideas-heading" className="text-lg font-semibold">
          创意仓库
        </h2>
        <p className="text-xs text-muted-foreground">
          {activeCards.length} 个待用创意 · {cards.length} 张卡片总计
        </p>
      </header>

      {/* 新建卡片 */}
      <div className="mb-4 rounded-md border border-border bg-card/60 p-3">
        <textarea
          value={newCardContent}
          onChange={(e) => setNewCardContent(e.target.value)}
          placeholder="记录一个新想法..."
          className="w-full resize-none border-none bg-transparent text-sm focus:outline-none"
          rows={2}
        />
        <div className="mt-2 flex justify-end">
          <Button
            size="sm"
            onClick={() => newCardContent.trim() && createMutation.mutate(newCardContent.trim())}
            disabled={!newCardContent.trim() || createMutation.isPending}
          >
            {createMutation.isPending ? '创建中...' : '新建卡片'}
          </Button>
        </div>
      </div>

      {/* 卡片列表 */}
      <div className="flex-1 space-y-2 overflow-auto">
        {/* 操作栏 */}
        {selectedCards.size > 0 && (
          <div className="flex items-center gap-2 p-2 bg-primary/10 rounded-md">
            <span className="text-sm">已选择 {selectedCards.size} 张卡片</span>
            <Button
              size="sm"
              onClick={() => {
                const selectedContents = cards
                  .filter((c: IdeaCard) => selectedCards.has(c.id))
                  .map((c: IdeaCard) => {
                    const content = getCardContent(c.id)
                    const summary = c.summary || content.slice(0, 50)
                    return `【${summary}】\n${content}`
                  })
                  .join('\n\n')
                setChatPrefill(`根据以下素材，生成第一场戏的剧本：\n\n${selectedContents}`)
                setView('home')
                setSelectedCards(new Set())
              }}
            >
              生成剧本草稿
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setSelectedCards(new Set())}
            >
              取消选择
            </Button>
          </div>
        )}

        {/* 待用卡片 */}
        {activeCards.map((card: IdeaCard) => {
          const content = getCardContent(card.id)
          const summary = card.summary || content.slice(0, 50)
          const isSelected = selectedCards.has(card.id)
          const isEditing = editingCardId === card.id

          return (
            <article
              key={card.id}
              className={`rounded-md border border-border bg-card/60 p-3 transition-colors hover:border-primary/30 ${isSelected ? 'border-primary bg-primary/5' : ''}`}
            >
              {isEditing ? (
                <div>
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full resize-none border-none bg-transparent text-sm focus:outline-none"
                    rows={3}
                  />
                  <div className="mt-2 flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setEditingCardId(null)
                        setEditContent('')
                      }}
                    >
                      取消
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => updateMutation.mutate({ cardId: card.id, content: editContent })}
                      disabled={updateMutation.isPending}
                    >
                      保存
                    </Button>
                  </div>
                </div>
              ) : (
                <div>
                  {/* 勾选框 + 摘要 */}
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        const newSet = new Set(selectedCards)
                        e.target.checked ? newSet.add(card.id) : newSet.delete(card.id)
                        setSelectedCards(newSet)
                      }}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{summary}</p>
                      <details className="mt-1">
                        <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                          查看完整内容
                        </summary>
                        <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
                      </details>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      {new Date(card.created_at).toLocaleDateString('zh-CN')}
                      {card.created_from === 'auto' && ' · 自动提取'}
                    </span>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => sendToChat(content)}
                        className="text-xs"
                      >
                        发送给 ChatUI
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setEditingCardId(card.id)
                          setEditContent(content)
                        }}
                        className="text-xs"
                      >
                        编辑
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => statusMutation.mutate({ cardId: card.id, status: 'shelved' })}
                        className="text-xs"
                      >
                        暂放
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => deleteMutation.mutate(card.id)}
                        className="text-xs text-destructive"
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </article>
          )
        })}

        {/* 暂放卡片 */}
        {shelvedCards.length > 0 && (
          <details className="group">
            <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
              {shelvedCards.length} 个暂放卡片
            </summary>
            <div className="mt-2 space-y-2">
              {shelvedCards.map((card: IdeaCard) => {
                const content = getCardContent(card.id)
                return (
                  <article
                    key={card.id}
                    className="rounded-md border border-border bg-muted/30 p-3 opacity-60"
                  >
                    <p className="text-sm">{content}</p>
                    <div className="mt-2 flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => statusMutation.mutate({ cardId: card.id, status: 'active' })}
                        className="text-xs"
                      >
                        恢复
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => statusMutation.mutate({ cardId: card.id, status: 'archived' })}
                        className="text-xs"
                      >
                        归档
                      </Button>
                    </div>
                  </article>
                )
              })}
            </div>
          </details>
        )}

        {/* 空状态 */}
        {cards.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-sm text-muted-foreground">还没有创意卡片</p>
            <p className="mt-1 text-xs text-muted-foreground">
              从 ChatUI 对话中提取，或直接创建
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
