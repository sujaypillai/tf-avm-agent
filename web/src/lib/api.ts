import axios, { AxiosInstance, AxiosError } from "axios"
import type {
  ChatRequest,
  ChatResponse,
  GenerateRequest,
  GenerateResponse,
  DiagramAnalysisResponse,
  ModuleSearchParams,
  ModuleListResponse,
  APIError,
  WSMessage,
} from "@/types"

const API_BASE_URL = import.meta.env.VITE_API_URL || ""

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        "Content-Type": "application/json",
      },
    })

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<APIError>) => {
        const message =
          error.response?.data?.message || error.message || "An error occurred"
        return Promise.reject(new Error(message))
      }
    )
  }

  // Chat endpoints
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>("/api/chat", request)
    return response.data
  }

  // Generation endpoints
  async generateTerraform(request: GenerateRequest): Promise<GenerateResponse> {
    const response = await this.client.post<GenerateResponse>(
      "/api/generate",
      request
    )
    return response.data
  }

  // Diagram analysis endpoints
  async analyzeDiagram(file: File): Promise<DiagramAnalysisResponse> {
    const formData = new FormData()
    formData.append("file", file)

    const response = await this.client.post<DiagramAnalysisResponse>(
      "/api/analyze",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    )
    return response.data
  }

  // Module endpoints
  async listModules(params?: ModuleSearchParams): Promise<ModuleListResponse> {
    const response = await this.client.get<ModuleListResponse>("/api/modules", {
      params,
    })
    return response.data
  }

  async searchModules(query: string): Promise<ModuleListResponse> {
    return this.listModules({ search: query })
  }

  // WebSocket connection for streaming chat
  createChatWebSocket(
    sessionId: string,
    onMessage: (message: WSMessage) => void,
    onError: (error: Event) => void,
    onClose: () => void
  ): WebSocket {
    const wsUrl = API_BASE_URL.replace(/^http/, "ws")
    const ws = new WebSocket(`${wsUrl}/api/ws/chat?session=${sessionId}`)

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WSMessage
        onMessage(message)
      } catch {
        onMessage({ type: "chat", content: event.data })
      }
    }

    ws.onerror = onError
    ws.onclose = onClose

    return ws
  }
}

export const api = new ApiClient()

// Utility function for file downloads
export function downloadFile(content: string, filename: string): void {
  const blob = new Blob([content], { type: "text/plain" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// Utility function to download multiple files as zip
export async function downloadFilesAsZip(
  files: Array<{ path: string; content: string }>,
  _zipName: string
): Promise<void> {
  // For simplicity, we'll download files individually
  // In production, you'd want to use a library like JSZip
  for (const file of files) {
    downloadFile(file.content, file.path.split("/").pop() || file.path)
  }
}

// Copy to clipboard utility
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Fallback for older browsers
    const textArea = document.createElement("textarea")
    textArea.value = text
    textArea.style.position = "fixed"
    textArea.style.left = "-999999px"
    document.body.appendChild(textArea)
    textArea.select()
    try {
      document.execCommand("copy")
      return true
    } catch {
      return false
    } finally {
      document.body.removeChild(textArea)
    }
  }
}
