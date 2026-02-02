import { File, Folder, ChevronRight, ChevronDown } from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"
import type { GeneratedFile } from "@/types"

interface FileTreeProps {
  files: GeneratedFile[]
  selectedFile: string | null
  onSelectFile: (path: string) => void
}

interface TreeNode {
  name: string
  path: string
  type: "file" | "folder"
  children?: TreeNode[]
  file?: GeneratedFile
}

function buildTree(files: GeneratedFile[]): TreeNode[] {
  const root: TreeNode[] = []

  for (const file of files) {
    const parts = file.path.split("/")
    let current = root

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isFile = i === parts.length - 1
      const path = parts.slice(0, i + 1).join("/")

      let node = current.find((n) => n.name === part)

      if (!node) {
        node = {
          name: part,
          path,
          type: isFile ? "file" : "folder",
          children: isFile ? undefined : [],
          file: isFile ? file : undefined,
        }
        current.push(node)
      }

      if (!isFile && node.children) {
        current = node.children
      }
    }
  }

  return root
}

function TreeItem({
  node,
  depth,
  selectedFile,
  onSelectFile,
}: {
  node: TreeNode
  depth: number
  selectedFile: string | null
  onSelectFile: (path: string) => void
}) {
  const [isOpen, setIsOpen] = useState(true)
  const isFolder = node.type === "folder"
  const isSelected = selectedFile === node.path

  return (
    <div>
      <button
        className={cn(
          "flex w-full items-center gap-1 rounded-md px-2 py-1 text-sm hover:bg-muted",
          isSelected && "bg-muted"
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={() => {
          if (isFolder) {
            setIsOpen(!isOpen)
          } else {
            onSelectFile(node.path)
          }
        }}
      >
        {isFolder ? (
          <>
            {isOpen ? (
              <ChevronDown className="h-4 w-4 shrink-0" />
            ) : (
              <ChevronRight className="h-4 w-4 shrink-0" />
            )}
            <Folder className="h-4 w-4 shrink-0 text-blue-500" />
          </>
        ) : (
          <>
            <span className="w-4" />
            <File className="h-4 w-4 shrink-0 text-muted-foreground" />
          </>
        )}
        <span className="truncate">{node.name}</span>
      </button>

      {isFolder && isOpen && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeItem
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedFile={selectedFile}
              onSelectFile={onSelectFile}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function FileTree({ files, selectedFile, onSelectFile }: FileTreeProps) {
  const tree = buildTree(files)

  if (files.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-sm text-muted-foreground">
        No files generated yet
      </div>
    )
  }

  return (
    <div className="p-2">
      {tree.map((node) => (
        <TreeItem
          key={node.path}
          node={node}
          depth={0}
          selectedFile={selectedFile}
          onSelectFile={onSelectFile}
        />
      ))}
    </div>
  )
}
