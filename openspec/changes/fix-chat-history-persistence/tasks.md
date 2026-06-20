## 1. Backend API

- [x] 1.1 Add `GET /projects/{project_id}/chat/messages` endpoint in `backend/app/api/chat.py`
- [x] 1.2 Implement message filtering by event type `chat.message` in the endpoint
- [x] 1.3 Define response model `ChatMessageListResponse` with `messages` and `total` fields
- [ ] 1.4 Add unit tests for the new endpoint

## 2. Frontend API Client

- [x] 2.1 Add `ChatMessage` type definition in `frontend/src/lib/api-types.ts`
- [x] 2.2 Add `ChatMessageListResponse` type definition
- [x] 2.3 Add `getChatMessages(projectId)` method in `frontend/src/lib/api.ts`

## 3. Frontend Runtime Integration

- [x] 3.1 Add `toThreadMessageLike()` conversion function in `frontend/src/lib/chat-runtime-context.tsx`
- [x] 3.2 Add state for `initialMessages` and loading status in `ChatRuntimeInner`
- [x] 3.3 Add `useEffect` to fetch chat history on mount
- [x] 3.4 Pass `initialMessages` to `useLocalRuntime`
- [x] 3.5 Add loading state UI (show "加载聊天历史..." while fetching)
- [x] 3.6 Add error handling for fetch failure (show toast, allow empty history)

## 4. Testing & Verification

- [x] 4.1 Test: Refresh page preserves chat history
- [x] 4.2 Test: Switch project loads correct chat history
- [x] 4.3 Test: New project shows empty chat
- [x] 4.4 Test: Network failure during load doesn't block chatting
- [x] 4.5 Verify: Messages display in correct chronological order
