import { ChatRuntimeProvider, useChatRuntimeContext } from './chat-runtime-context'
import { ChatPanel } from './ChatPanel'

function ChatFeature() {
  return (
    <ChatRuntimeProvider>
      <ChatPanel />
    </ChatRuntimeProvider>
  )
}

export default ChatFeature
export { ChatPanel, ChatRuntimeProvider, useChatRuntimeContext }
