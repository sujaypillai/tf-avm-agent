import { Check } from "lucide-react"
import { cn } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"
import type { AzureService } from "@/types"

interface ServiceCardProps {
  service: AzureService
  selected: boolean
  onToggle: () => void
}

const categoryColors: Record<string, string> = {
  compute: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  networking: "bg-green-500/10 text-green-600 dark:text-green-400",
  storage: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  database: "bg-purple-500/10 text-purple-600 dark:text-purple-400",
  security: "bg-red-500/10 text-red-600 dark:text-red-400",
  monitoring: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400",
  containers: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
  ai: "bg-pink-500/10 text-pink-600 dark:text-pink-400",
  integration: "bg-orange-500/10 text-orange-600 dark:text-orange-400",
}

export function ServiceCard({ service, selected, onToggle }: ServiceCardProps) {
  return (
    <Card
      className={cn(
        "cursor-pointer transition-all hover:shadow-md",
        selected && "ring-2 ring-primary"
      )}
      onClick={onToggle}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-medium text-sm">{service.name}</h3>
              {selected && (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Check className="h-3 w-3" />
                </div>
              )}
            </div>
            <p className="text-xs text-muted-foreground line-clamp-2">
              {service.description}
            </p>
          </div>
        </div>
        <div className="mt-3">
          <span
            className={cn(
              "inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize",
              categoryColors[service.category] || "bg-gray-500/10 text-gray-600"
            )}
          >
            {service.category}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
