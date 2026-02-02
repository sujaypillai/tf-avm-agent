import { useEffect, useRef } from "react"
import { ChatMessage } from "./ChatMessage"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { ChatMessage as ChatMessageType } from "@/types"

interface MessageListProps {
  messages: ChatMessageType[]
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="text-center max-w-md">
          <h2 className="text-2xl font-semibold mb-2">
            Welcome to TF AVM Agent
          </h2>
          <p className="text-muted-foreground mb-6">
            I can help you generate Terraform code using Azure Verified Modules.
            Ask me about Azure services, describe your infrastructure needs, or
            upload an architecture diagram.
          </p>
          <div className="grid gap-2 text-sm text-left">
            <div className="rounded-lg border p-3">
              "Generate Terraform for a web app with Azure SQL database"
            </div>
            <div className="rounded-lg border p-3">
              "What AVM modules are available for networking?"
            </div>
            <div className="rounded-lg border p-3">
              "Create a hub-spoke network topology"
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <ScrollArea className="flex-1">
      <div className="divide-y">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
      </div>
      <div ref={bottomRef} />
    </ScrollArea>
  )
}
