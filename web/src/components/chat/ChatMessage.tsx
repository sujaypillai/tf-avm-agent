import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism"
import { Copy, Check, User, Bot } from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { copyToClipboard } from "@/lib/api"
import type { ChatMessage as ChatMessageType } from "@/types"

interface ChatMessageProps {
  message: ChatMessageType
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  const handleCopyCode = async (code: string) => {
    const success = await copyToClipboard(code)
    if (success) {
      setCopiedCode(code)
      setTimeout(() => setCopiedCode(null), 2000)
    }
  }

  const isUser = message.role === "user"

  return (
    <div
      className={cn(
        "flex gap-3 px-4 py-6",
        isUser ? "bg-background" : "bg-muted/50"
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-secondary"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className="flex-1 overflow-hidden">
        <div className="mb-1 text-sm font-medium">
          {isUser ? "You" : "TF AVM Agent"}
        </div>
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || "")
                const codeString = String(children).replace(/\n$/, "")

                if (match) {
                  return (
                    <div className="relative my-4 rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between bg-zinc-800 px-4 py-2 text-xs text-zinc-400">
                        <span>{match[1]}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-zinc-400 hover:text-white"
                          onClick={() => handleCopyCode(codeString)}
                        >
                          {copiedCode === codeString ? (
                            <Check className="h-3 w-3" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                      </div>
                      <SyntaxHighlighter
                        style={oneDark}
                        language={match[1]}
                        PreTag="div"
                        customStyle={{
                          margin: 0,
                          borderRadius: 0,
                          fontSize: "0.875rem",
                        }}
                      >
                        {codeString}
                      </SyntaxHighlighter>
                    </div>
                  )
                }

                return (
                  <code
                    className="rounded bg-muted px-1.5 py-0.5 text-sm"
                    {...props}
                  >
                    {children}
                  </code>
                )
              },
              pre({ children }) {
                return <>{children}</>
              },
              table({ children }) {
                return (
                  <div className="my-4 overflow-x-auto">
                    <table className="min-w-full border-collapse border border-border text-sm">
                      {children}
                    </table>
                  </div>
                )
              },
              thead({ children }) {
                return <thead className="bg-muted">{children}</thead>
              },
              th({ children }) {
                return (
                  <th className="border border-border px-4 py-2 text-left font-semibold">
                    {children}
                  </th>
                )
              },
              td({ children }) {
                return (
                  <td className="border border-border px-4 py-2">
                    {children}
                  </td>
                )
              },
              tr({ children }) {
                return <tr className="even:bg-muted/50">{children}</tr>
              },
            }}
          >
            {message.content}
          </ReactMarkdown>

          {message.isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse" />
          )}
        </div>
      </div>
    </div>
  )
}
