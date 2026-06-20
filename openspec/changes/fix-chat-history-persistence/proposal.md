## Why

聊天历史在切换项目、刷新网页时会丢失，严重影响用户体验。用户在 ChatUI 中的对话是创作过程的核心记录，丢失意味着用户无法回顾之前的讨论，也无法继续之前的创作思路。

当前问题：
- 切换项目 → 聊天历史丢失
- 刷新网页 → 聊天历史丢失
- 切换板块（如正文编辑器）→ 不丢失（组件未卸载）

根因：聊天历史只存在前端内存中（`useLocalRuntime`），没有持久化到后端。虽然后端已存储 `chat.message` 事件，但前端没有 API 获取历史，也没有在初始化时加载。

## What Changes

- 新增后端 API：`GET /projects/{project_id}/chat/messages` 获取聊天历史
- 前端 API 客户端：新增 `getChatMessages()` 方法
- 前端 ChatRuntime：初始化时加载历史消息，传递给 `useLocalRuntime` 的 `initialMessages` 参数
- 聊天历史格式转换：后端 `chat.message` 事件 → 前端 `ThreadMessageLike` 格式

## Capabilities

### New Capabilities

- `chat-history-persistence`: 聊天历史的持久化存储与加载，支持跨会话、跨项目切换时保留对话记录

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

**后端**：
- `backend/app/api/chat.py`：新增 `GET /projects/{project_id}/chat/messages` 端点
- `backend/app/services/event_log.py`：可能需要新增按事件类型过滤的方法

**前端**：
- `frontend/src/lib/api.ts`：新增 `getChatMessages()` 方法
- `frontend/src/lib/api-types.ts`：新增 `ChatMessage` 类型定义
- `frontend/src/lib/chat-runtime-context.tsx`：初始化时加载历史，传递 `initialMessages`

**数据格式**：
- 后端事件格式：`{ type: "chat.message", payload: { role, content, message_id, timestamp } }`
- 前端 runtime 格式：`{ role: "user" | "assistant", content: string | TextMessagePart[] }`
