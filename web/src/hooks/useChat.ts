import { useState, useCallback, useRef, useEffect } from "react"
import { api } from "@/lib/api"
import type { ChatMessage, GeneratedFile, WSMessage } from "@/types"

interface UseChatOptions {
  onFilesGenerated?: (files: GeneratedFile[]) => void
}

export function useChat(options: UseChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string>(() =>
    Math.random().toString(36).substring(7)
  )
  const wsRef = useRef<WebSocket | null>(null)
  const streamingMessageRef = useRef<string>("")

  // Load messages from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(`chat-${sessionId}`)
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        setMessages(
          parsed.map((m: ChatMessage) => ({
            ...m,
            timestamp: new Date(m.timestamp),
          }))
        )
      } catch {
        // Ignore parse errors
      }
    }
  }, [sessionId])

  // Save messages to localStorage
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(`chat-${sessionId}`, JSON.stringify(messages))
    }
  }, [messages, sessionId])

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        role: "user",
        content,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMessage])
      setIsLoading(true)
      streamingMessageRef.current = ""

      // Create placeholder for assistant message
      const assistantMessageId = Math.random().toString(36).substring(7)
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      }
      setMessages((prev) => [...prev, assistantMessage])

      try {
        // Try WebSocket first for streaming
        const wsUrl = import.meta.env.VITE_API_URL?.replace(/^http/, "ws") || ""

        if (wsUrl) {
          wsRef.current = api.createChatWebSocket(
            sessionId,
            (msg: WSMessage) => {
              if (msg.type === "chat") {
                streamingMessageRef.current += msg.content
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessageId
                      ? { ...m, content: streamingMessageRef.current }
                      : m
                  )
                )
              } else if (msg.type === "complete") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessageId
                      ? { ...m, isStreaming: false }
                      : m
                  )
                )
                setIsLoading(false)

                // Check for generated files in metadata
                if (msg.metadata?.files) {
                  options.onFilesGenerated?.(
                    msg.metadata.files as GeneratedFile[]
                  )
                }
              } else if (msg.type === "error") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessageId
                      ? {
                          ...m,
                          content:
                            streamingMessageRef.current ||
                            "An error occurred. Please try again.",
                          isStreaming: false,
                        }
                      : m
                  )
                )
                setIsLoading(false)
              }
            },
            () => {
              // On error, fall back to REST API
              fallbackToRest(content, assistantMessageId)
            },
            () => {
              setIsLoading(false)
            }
          )

          // Send message through WebSocket
          wsRef.current.onopen = () => {
            wsRef.current?.send(JSON.stringify({ message: content }))
          }
        } else {
          // No WebSocket URL, use REST API directly
          await fallbackToRest(content, assistantMessageId)
        }
      } catch (error) {
        await fallbackToRest(content, assistantMessageId)
      }

      async function fallbackToRest(
        message: string,
        messageId: string
      ) {
        try {
          const response = await api.sendMessage({
            message,
            sessionId,
          })

          setMessages((prev) =>
            prev.map((m) =>
              m.id === messageId
                ? { ...m, content: response.message, isStreaming: false }
                : m
            )
          )

          if (response.generated_files) {
            options.onFilesGenerated?.(response.generated_files)
          }
        } catch (err) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === messageId
                ? {
                    ...m,
                    content:
                      err instanceof Error
                        ? err.message
                        : "An error occurred. Please try again.",
                    isStreaming: false,
                  }
                : m
            )
          )
        } finally {
          setIsLoading(false)
        }
      }
    },
    [sessionId, options]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    localStorage.removeItem(`chat-${sessionId}`)
    setSessionId(Math.random().toString(36).substring(7))
  }, [sessionId])

  return {
    messages,
    sendMessage,
    clearMessages,
    isLoading,
    sessionId,
  }
}
