## Context

**当前状态**：
- 后端已存储 `chat.message` 事件到事件日志（`events/*.jsonl`）
- 前端使用 `@assistant-ui/react` 的 `useLocalRuntime` 管理聊天状态
- `useLocalRuntime` 支持 `initialMessages` 参数，但当前未使用
- 聊天状态只存在前端内存中，页面刷新或项目切换时丢失

**约束**：
- 不改变现有事件日志结构
- 不影响现有聊天功能
- 加载历史时不能阻塞 UI

**利益相关者**：
- 用户：期望聊天历史跨会话保留
- 前端：需要简单的 API 获取历史
- 后端：需要提供高效的查询端点

## Goals / Non-Goals

**Goals**：
- 切换项目后，聊天历史从后端加载并恢复
- 刷新网页后，聊天历史从后端加载并恢复
- 加载过程不阻塞 UI，有 loading 状态
- 历史消息按时间顺序正确显示

**Non-Goals**：
- 不修改事件日志存储格式
- 不实现聊天历史的分页加载（V1 全量加载）
- 不实现聊天历史的搜索功能
- 不处理离线场景（需要网络才能加载历史）

## Decisions

### Decision 1: 后端 API 设计

**选择**：`GET /projects/{project_id}/chat/messages`

**理由**：
- 独立端点，职责清晰
- 可以专门针对聊天消息优化（过滤、排序）
- 未来可扩展分页参数

**替代方案**：
- 复用 `GET /projects/{project_id}/events` + 前端过滤
  - 缺点：返回所有事件，浪费带宽；前端需要额外过滤逻辑

**响应格式**：
```json
{
  "messages": [
    {
      "message_id": "msg_xxx",
      "role": "user",
      "content": "主角叫小红",
      "timestamp": "2026-06-21T00:00:00"
    },
    {
      "message_id": "msg_yyy",
      "role": "assistant",
      "content": "小红这个名字...",
      "timestamp": "2026-06-21T00:00:05"
    }
  ],
  "total": 2
}
```

### Decision 2: 前端初始化时机

**选择**：`ChatRuntimeInner` 组件 mount 时异步加载

**理由**：
- 组件 mount 时 `projectId` 已确定
- 异步加载不阻塞渲染
- 可以显示 loading 状态

**实现方式**：
```tsx
function ChatRuntimeInner({ projectId, children }) {
  const [initialMessages, setInitialMessages] = useState<ThreadMessageLike[] | null>(null)
  
  useEffect(() => {
    api.getChatMessages(projectId).then(res => {
      const messages = res.messages.map(toThreadMessageLike)
      setInitialMessages(messages)
    })
  }, [projectId])
  
  if (initialMessages === null) {
    return <LoadingState />
  }
  
  const runtime = useLocalRuntime(adapter, { initialMessages })
  // ...
}
```

### Decision 3: 消息格式转换

**选择**：前端负责格式转换

**理由**：
- 后端存储格式是事件日志格式，不应改变
- 前端 runtime 的格式是 `@assistant-ui/react` 定义，后端不应耦合
- 转换逻辑简单，前端处理更清晰

**转换函数**：
```typescript
function toThreadMessageLike(msg: ChatMessage): ThreadMessageLike {
  return {
    role: msg.role,  // "user" | "assistant"
    content: [{ type: "text", text: msg.content }],
    id: msg.message_id,
    createdAt: new Date(msg.timestamp),
  }
}
```

### Decision 4: Loading 状态处理

**选择**：显示骨架屏或 loading 文案

**理由**：
- 用户明确知道正在加载
- 避免空白状态造成困惑

**实现**：
```tsx
if (initialMessages === null) {
  return (
    <div className="flex h-full items-center justify-center">
      <span className="text-muted-foreground">加载聊天历史...</span>
    </div>
  )
}
```

## Risks / Trade-offs

**风险 1：大量历史消息导致加载慢**
→ 缓解：V1 假设聊天历史不会太长（< 100 条）；后续可加分页

**风险 2：网络失败导致无法聊天**
→ 缓解：加载失败时降级为空历史，允许用户继续聊天；显示 toast 提示

**风险 3：历史消息与实时消息冲突**
→ 缓解：`useLocalRuntime` 的 `initialMessages` 只在 mount 时使用，后续消息由 runtime 管理，不会冲突

**权衡：全量加载 vs 分页加载**
→ V1 选择全量加载，实现简单；分页加载留待后续优化
