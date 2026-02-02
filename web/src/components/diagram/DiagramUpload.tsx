import { useState, useCallback } from "react"
import { Upload, Loader2, Image as ImageIcon, ArrowRight } from "lucide-react"
import { DiagramPreview } from "./DiagramPreview"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import type { AzureService, IdentifiedService } from "@/types"

interface DiagramUploadProps {
  onServicesIdentified: (services: AzureService[]) => void
  onTabChange: (tab: string) => void
}

export function DiagramUpload({
  onServicesIdentified,
  onTabChange,
}: DiagramUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [identifiedServices, setIdentifiedServices] = useState<
    IdentifiedService[]
  >([])
  const [error, setError] = useState<string | null>(null)

  const handleFileSelect = useCallback((selectedFile: File) => {
    if (!selectedFile.type.startsWith("image/")) {
      setError("Please upload an image file")
      return
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("File size must be less than 10MB")
      return
    }

    setFile(selectedFile)
    setPreviewUrl(URL.createObjectURL(selectedFile))
    setError(null)
    setIdentifiedServices([])
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)

      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile) {
        handleFileSelect(droppedFile)
      }
    },
    [handleFileSelect]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      handleFileSelect(selectedFile)
    }
  }

  const handleRemove = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }
    setFile(null)
    setPreviewUrl(null)
    setIdentifiedServices([])
  }

  const handleAnalyze = async () => {
    if (!file) return

    setIsAnalyzing(true)
    setError(null)

    try {
      const response = await api.analyzeDiagram(file)
      if (response.success) {
        setIdentifiedServices(response.services)
      } else {
        setError(response.message || "Failed to analyze diagram")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze diagram")
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleContinueToServices = () => {
    const services: AzureService[] = identifiedServices.map((s) => ({
      id: s.name.toLowerCase().replace(/\s+/g, "-"),
      name: s.name,
      category: s.category,
      description: `Identified from diagram with ${Math.round(
        s.confidence * 100
      )}% confidence`,
    }))
    onServicesIdentified(services)
    onTabChange("services")
  }

  return (
    <div className="flex h-full flex-col p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold">Analyze Architecture Diagram</h2>
        <p className="text-sm text-muted-foreground">
          Upload an Azure architecture diagram to automatically identify
          services and generate Terraform code
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upload Area */}
        <div className="space-y-4">
          {!file ? (
            <div
              className={cn(
                "relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors",
                isDragging
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-primary/50"
              )}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              <input
                type="file"
                accept="image/*"
                onChange={handleFileInput}
                className="absolute inset-0 cursor-pointer opacity-0"
              />
              <div className="flex flex-col items-center gap-4 text-center">
                <div className="rounded-full bg-muted p-4">
                  <ImageIcon className="h-8 w-8 text-muted-foreground" />
                </div>
                <div>
                  <p className="font-medium">Drop your diagram here</p>
                  <p className="text-sm text-muted-foreground">
                    or click to browse
                  </p>
                </div>
                <p className="text-xs text-muted-foreground">
                  PNG, JPG, or SVG up to 10MB
                </p>
              </div>
            </div>
          ) : (
            <DiagramPreview
              file={file}
              previewUrl={previewUrl!}
              onRemove={handleRemove}
            />
          )}

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          {file && !isAnalyzing && identifiedServices.length === 0 && (
            <Button onClick={handleAnalyze} className="w-full gap-2">
              <Upload className="h-4 w-4" />
              Analyze Diagram
            </Button>
          )}

          {isAnalyzing && (
            <div className="flex items-center justify-center gap-2 py-4">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">
                Analyzing your diagram...
              </span>
            </div>
          )}
        </div>

        {/* Results */}
        <div className="space-y-4">
          <h3 className="font-medium">Identified Services</h3>
          {identifiedServices.length > 0 ? (
            <>
              <div className="grid gap-2">
                {identifiedServices.map((service, index) => (
                  <Card key={index}>
                    <CardContent className="flex items-center justify-between p-3">
                      <div>
                        <p className="font-medium">{service.name}</p>
                        <p className="text-xs text-muted-foreground capitalize">
                          {service.category}
                        </p>
                      </div>
                      <Badge
                        variant={
                          service.confidence > 0.8 ? "default" : "secondary"
                        }
                      >
                        {Math.round(service.confidence * 100)}%
                      </Badge>
                    </CardContent>
                  </Card>
                ))}
              </div>
              <Button
                onClick={handleContinueToServices}
                className="w-full gap-2"
              >
                Continue to Service Selection
                <ArrowRight className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
              <p className="text-sm text-muted-foreground">
                {file
                  ? "Click 'Analyze Diagram' to identify Azure services"
                  : "Upload a diagram to get started"}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
