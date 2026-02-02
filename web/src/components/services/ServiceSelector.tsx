import { useState } from "react"
import { Search, Loader2, Sparkles } from "lucide-react"
import { ServiceCard } from "./ServiceCard"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useGenerate } from "@/hooks/useGenerate"
import type { AzureService, GeneratedFile, ServiceCategory } from "@/types"

// Azure services data - IDs must match backend AVM module names
const AZURE_SERVICES: AzureService[] = [
  {
    id: "virtual_machine",
    name: "Virtual Machine",
    category: "compute",
    description: "Create and manage Windows or Linux virtual machines",
    moduleName: "avm-res-compute-virtualmachine",
  },
  {
    id: "kubernetes_cluster",
    name: "Azure Kubernetes Service",
    category: "containers",
    description: "Managed Kubernetes container orchestration service",
    moduleName: "avm-res-containerservice-managedcluster",
  },
  {
    id: "web_app",
    name: "App Service",
    category: "compute",
    description: "Build and host web apps, mobile backends, and RESTful APIs",
    moduleName: "avm-res-web-site",
  },
  {
    id: "function_app",
    name: "Azure Functions",
    category: "compute",
    description: "Event-driven serverless compute platform",
    moduleName: "avm-res-web-site",
  },
  {
    id: "virtual_network",
    name: "Virtual Network",
    category: "networking",
    description: "Private network in Azure for your resources",
    moduleName: "avm-res-network-virtualnetwork",
  },
  {
    id: "load_balancer",
    name: "Load Balancer",
    category: "networking",
    description: "High-performance, low-latency Layer 4 load balancer",
    moduleName: "avm-res-network-loadbalancer",
  },
  {
    id: "application_gateway",
    name: "Application Gateway",
    category: "networking",
    description: "Web traffic load balancer with WAF capabilities",
    moduleName: "avm-res-network-applicationgateway",
  },
  {
    id: "storage_account",
    name: "Storage Account",
    category: "storage",
    description: "Durable, highly available, and massively scalable storage",
    moduleName: "avm-res-storage-storageaccount",
  },
  {
    id: "sql_server",
    name: "Azure SQL Database",
    category: "database",
    description: "Managed relational SQL Database as a service",
    moduleName: "avm-res-sql-server",
  },
  {
    id: "cosmosdb",
    name: "Cosmos DB",
    category: "database",
    description: "Globally distributed, multi-model database service",
    moduleName: "avm-res-documentdb-databaseaccount",
  },
  {
    id: "key_vault",
    name: "Key Vault",
    category: "security",
    description: "Safeguard cryptographic keys and secrets",
    moduleName: "avm-res-keyvault-vault",
  },
  {
    id: "container_registry",
    name: "Container Registry",
    category: "containers",
    description: "Private Docker container registry",
    moduleName: "avm-res-containerregistry-registry",
  },
  {
    id: "log_analytics_workspace",
    name: "Azure Monitor",
    category: "monitoring",
    description: "Full observability into your applications and infrastructure",
    moduleName: "avm-res-operationalinsights-workspace",
  },
  {
    id: "cognitive_services",
    name: "Azure OpenAI",
    category: "ai",
    description: "Access to OpenAI models with Azure security",
    moduleName: "avm-res-cognitiveservices-account",
  },
  {
    id: "service_bus",
    name: "Service Bus",
    category: "integration",
    description: "Reliable cloud messaging as a service",
    moduleName: "avm-res-servicebus-namespace",
  },
  {
    id: "event_hub",
    name: "Event Hubs",
    category: "integration",
    description: "Big data streaming platform and event ingestion service",
    moduleName: "avm-res-eventhub-namespace",
  },
]

const CATEGORIES: ServiceCategory[] = [
  "compute",
  "networking",
  "storage",
  "database",
  "security",
  "monitoring",
  "containers",
  "ai",
  "integration",
]

interface ServiceSelectorProps {
  onSelect: (services: AzureService[]) => void
  selectedServices: AzureService[]
  onGenerate: (files: GeneratedFile[]) => void
}

export function ServiceSelector({
  onSelect,
  selectedServices,
  onGenerate,
}: ServiceSelectorProps) {
  const [search, setSearch] = useState("")
  const [activeCategory, setActiveCategory] = useState<ServiceCategory | "all">(
    "all"
  )
  const [projectName, setProjectName] = useState("my-infrastructure")

  const { generate, isLoading } = useGenerate({
    onSuccess: (files) => {
      onGenerate(files)
    },
  })

  const filteredServices = AZURE_SERVICES.filter((service) => {
    const matchesSearch =
      service.name.toLowerCase().includes(search.toLowerCase()) ||
      service.description.toLowerCase().includes(search.toLowerCase())
    const matchesCategory =
      activeCategory === "all" || service.category === activeCategory
    return matchesSearch && matchesCategory
  })

  const toggleService = (service: AzureService) => {
    const isSelected = selectedServices.some((s) => s.id === service.id)
    if (isSelected) {
      onSelect(selectedServices.filter((s) => s.id !== service.id))
    } else {
      onSelect([...selectedServices, service])
    }
  }

  const handleGenerate = () => {
    if (selectedServices.length === 0) return
    generate({
      services: selectedServices.map((s) => s.id),
      projectName,
    })
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">Select Azure Services</h2>
            <p className="text-sm text-muted-foreground">
              Choose the services you want to include in your infrastructure
            </p>
          </div>
          {selectedServices.length > 0 && (
            <Badge variant="secondary" className="text-sm">
              {selectedServices.length} selected
            </Badge>
          )}
        </div>

        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search services..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Input
            placeholder="Project name"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="w-48"
          />
        </div>

        {/* Category filters */}
        <div className="flex gap-2 mt-4 flex-wrap">
          <Button
            variant={activeCategory === "all" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setActiveCategory("all")}
          >
            All
          </Button>
          {CATEGORIES.map((category) => (
            <Button
              key={category}
              variant={activeCategory === category ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setActiveCategory(category)}
              className="capitalize"
            >
              {category}
            </Button>
          ))}
        </div>
      </div>

      {/* Service Grid */}
      <ScrollArea className="flex-1 p-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredServices.map((service) => (
            <ServiceCard
              key={service.id}
              service={service}
              selected={selectedServices.some((s) => s.id === service.id)}
              onToggle={() => toggleService(service)}
            />
          ))}
        </div>
      </ScrollArea>

      {/* Generate Button */}
      <div className="border-t p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            {selectedServices.length > 0 ? (
              <span>
                Selected:{" "}
                {selectedServices.map((s) => s.name).join(", ")}
              </span>
            ) : (
              <span>Select services to generate Terraform code</span>
            )}
          </div>
          <Button
            onClick={handleGenerate}
            disabled={selectedServices.length === 0 || isLoading}
            className="gap-2"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Generate Terraform
          </Button>
        </div>
      </div>
    </div>
  )
}
