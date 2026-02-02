import { X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface DiagramPreviewProps {
  file: File
  previewUrl: string
  onRemove: () => void
}

export function DiagramPreview({
  file,
  previewUrl,
  onRemove,
}: DiagramPreviewProps) {
  return (
    <div className="relative rounded-lg border bg-muted/50 p-2">
      <div className="relative aspect-video overflow-hidden rounded-md">
        <img
          src={previewUrl}
          alt="Architecture diagram preview"
          className="h-full w-full object-contain"
        />
      </div>
      <div className="mt-2 flex items-center justify-between">
        <div className="text-sm">
          <p className="font-medium truncate max-w-[200px]">{file.name}</p>
          <p className="text-xs text-muted-foreground">
            {(file.size / 1024 / 1024).toFixed(2)} MB
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onRemove}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
