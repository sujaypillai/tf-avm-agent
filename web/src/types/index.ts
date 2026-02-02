// Chat types
export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  isStreaming?: boolean
}

export interface ChatRequest {
  message: string
  sessionId?: string
}

export interface ChatResponse {
  message: string
  session_id: string
  generated_files?: GeneratedFile[]
}

// Service types
export interface AzureService {
  id: string
  name: string
  category: ServiceCategory
  description: string
  icon?: string
  moduleName?: string
}

export type ServiceCategory =
  | "compute"
  | "networking"
  | "storage"
  | "database"
  | "security"
  | "monitoring"
  | "containers"
  | "ai"
  | "integration"

export interface ServiceSelection {
  services: string[]
  projectName: string
  options?: GenerateOptions
}

export interface GenerateOptions {
  includeExamples?: boolean
  outputFormat?: "flat" | "modular"
  providerVersion?: string
}

// Generation types
export interface GenerateRequest {
  services: string[]
  projectName: string
  location?: string
  options?: GenerateOptions
}

export interface GenerateResponse {
  success: boolean
  files: GeneratedFile[]
  message?: string
}

export interface GeneratedFile {
  path: string
  content: string
  type: "terraform" | "tfvars" | "markdown" | "other"
}

// Diagram analysis types
export interface DiagramAnalysisRequest {
  image: File
}

export interface DiagramAnalysisResponse {
  success: boolean
  services: IdentifiedService[]
  suggestedArchitecture?: string
  message?: string
}

export interface IdentifiedService {
  name: string
  confidence: number
  category: ServiceCategory
  position?: {
    x: number
    y: number
    width: number
    height: number
  }
}

// Module types
export interface AVMModule {
  name: string
  description: string
  category: ServiceCategory
  version: string
  source: string
  documentation?: string
}

export interface ModuleSearchParams {
  category?: ServiceCategory
  search?: string
  limit?: number
  offset?: number
}

export interface ModuleListResponse {
  modules: AVMModule[]
  total: number
}

// WebSocket types
export interface WSMessage {
  type: "chat" | "status" | "error" | "complete"
  content: string
  metadata?: Record<string, unknown>
}

// Session types
export interface Session {
  id: string
  messages: ChatMessage[]
  createdAt: Date
  updatedAt: Date
}

// API Error
export interface APIError {
  message: string
  code?: string
  details?: Record<string, unknown>
}
