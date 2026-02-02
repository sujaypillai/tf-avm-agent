import { useState, useEffect } from "react"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism"
import { Download, FolderOpen } from "lucide-react"
import { FileTree } from "./FileTree"
import { CodeActions } from "./CodeActions"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { downloadFile } from "@/lib/api"
import type { GeneratedFile } from "@/types"

interface CodeViewerProps {
  files: GeneratedFile[]
}

function getLanguage(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase()
  switch (ext) {
    case "tf":
      return "hcl"
    case "tfvars":
      return "hcl"
    case "json":
      return "json"
    case "md":
      return "markdown"
    case "yaml":
    case "yml":
      return "yaml"
    default:
      return "plaintext"
  }
}

export function CodeViewer({ files }: CodeViewerProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  // Auto-select first file
  useEffect(() => {
    if (files.length > 0 && !selectedFile) {
      setSelectedFile(files[0].path)
    }
  }, [files, selectedFile])

  const currentFile = files.find((f) => f.path === selectedFile)

  const handleDownloadAll = () => {
    for (const file of files) {
      const filename = file.path.split("/").pop() || file.path
      downloadFile(file.content, filename)
    }
  }

  if (files.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <div className="rounded-full bg-muted p-4 mb-4">
          <FolderOpen className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-medium mb-2">No Generated Code</h3>
        <p className="text-sm text-muted-foreground text-center max-w-md">
          Use the Chat or Services tab to generate Terraform code. Your
          generated files will appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* File Tree Sidebar */}
      <div className="w-64 border-r flex flex-col">
        <div className="flex items-center justify-between border-b p-3">
          <h3 className="text-sm font-medium">Files</h3>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 text-xs"
            onClick={handleDownloadAll}
          >
            <Download className="h-3 w-3" />
            All
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <FileTree
            files={files}
            selectedFile={selectedFile}
            onSelectFile={setSelectedFile}
          />
        </ScrollArea>
      </div>

      {/* Code Panel */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {currentFile ? (
          <>
            <div className="flex items-center justify-between border-b px-4 py-2">
              <span className="text-sm font-medium">{currentFile.path}</span>
              <CodeActions
                content={currentFile.content}
                filename={currentFile.path.split("/").pop() || currentFile.path}
              />
            </div>
            <ScrollArea className="flex-1">
              <SyntaxHighlighter
                language={getLanguage(currentFile.path)}
                style={oneDark}
                customStyle={{
                  margin: 0,
                  borderRadius: 0,
                  fontSize: "0.875rem",
                  minHeight: "100%",
                }}
                showLineNumbers
              >
                {currentFile.content}
              </SyntaxHighlighter>
            </ScrollArea>
          </>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Select a file to view its contents
          </div>
        )}
      </div>
    </div>
  )
}
