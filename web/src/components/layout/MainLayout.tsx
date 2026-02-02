import { useState } from "react"
import { Header } from "./Header"
import { Sidebar, MobileNav } from "./Sidebar"
import { ChatContainer } from "@/components/chat/ChatContainer"
import { ServiceSelector } from "@/components/services/ServiceSelector"
import { DiagramUpload } from "@/components/diagram/DiagramUpload"
import { CodeViewer } from "@/components/code/CodeViewer"
import type { GeneratedFile, AzureService } from "@/types"

export function MainLayout() {
  const [activeTab, setActiveTab] = useState("chat")
  const [generatedFiles, setGeneratedFiles] = useState<GeneratedFile[]>([])
  const [selectedServices, setSelectedServices] = useState<AzureService[]>([])

  const handleFilesGenerated = (files: GeneratedFile[]) => {
    setGeneratedFiles(files)
    setActiveTab("code")
  }

  const handleServicesSelected = (services: AzureService[]) => {
    setSelectedServices(services)
  }

  const renderContent = () => {
    switch (activeTab) {
      case "chat":
        return <ChatContainer onFilesGenerated={handleFilesGenerated} />
      case "services":
        return (
          <ServiceSelector
            onSelect={handleServicesSelected}
            selectedServices={selectedServices}
            onGenerate={handleFilesGenerated}
          />
        )
      case "diagram":
        return (
          <DiagramUpload
            onServicesIdentified={handleServicesSelected}
            onTabChange={setActiveTab}
          />
        )
      case "code":
        return <CodeViewer files={generatedFiles} />
      default:
        return <ChatContainer onFilesGenerated={handleFilesGenerated} />
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
        <main className="flex-1 overflow-hidden pb-16 md:pb-0">
          {renderContent()}
        </main>
      </div>
      <MobileNav activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  )
}
