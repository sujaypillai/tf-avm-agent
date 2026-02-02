import { Copy, Download, Check } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { copyToClipboard, downloadFile } from "@/lib/api"

interface CodeActionsProps {
  content: string
  filename: string
}

export function CodeActions({ content, filename }: CodeActionsProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    const success = await copyToClipboard(content)
    if (success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDownload = () => {
    downloadFile(content, filename)
  }

  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="sm"
        className="h-8 gap-1"
        onClick={handleCopy}
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5" />
            Copied
          </>
        ) : (
          <>
            <Copy className="h-3.5 w-3.5" />
            Copy
          </>
        )}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-8 gap-1"
        onClick={handleDownload}
      >
        <Download className="h-3.5 w-3.5" />
        Download
      </Button>
    </div>
  )
}
