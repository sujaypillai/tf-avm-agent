import { MessageList } from "./MessageList"
import { ChatInput } from "./ChatInput"
import { useChat } from "@/hooks/useChat"
import type { GeneratedFile } from "@/types"

interface ChatContainerProps {
  onFilesGenerated?: (files: GeneratedFile[]) => void
}

export function ChatContainer({ onFilesGenerated }: ChatContainerProps) {
  const { messages, sendMessage, isLoading } = useChat({
    onFilesGenerated,
  })

  return (
    <div className="flex h-full flex-col">
      <MessageList messages={messages} />
      <ChatInput onSend={sendMessage} isLoading={isLoading} />
    </div>
  )
}
