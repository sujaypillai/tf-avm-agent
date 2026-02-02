import { MessageSquare, Grid3X3, Image, Code, Settings } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

interface SidebarProps {
  activeTab: string
  onTabChange: (tab: string) => void
}

const navItems = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "services", label: "Services", icon: Grid3X3 },
  { id: "diagram", label: "Diagram", icon: Image },
  { id: "code", label: "Output", icon: Code },
]

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <aside className="hidden md:flex w-16 lg:w-56 flex-col border-r bg-muted/40">
      <nav className="flex flex-col gap-1 p-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeTab === item.id

          return (
            <Button
              key={item.id}
              variant={isActive ? "secondary" : "ghost"}
              className={cn(
                "justify-start gap-3",
                "lg:px-3 lg:py-2",
                "w-full"
              )}
              onClick={() => onTabChange(item.id)}
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span className="hidden lg:inline">{item.label}</span>
            </Button>
          )
        })}
      </nav>

      <div className="mt-auto p-2">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3"
          onClick={() => onTabChange("settings")}
        >
          <Settings className="h-5 w-5 shrink-0" />
          <span className="hidden lg:inline">Settings</span>
        </Button>
      </div>
    </aside>
  )
}

// Mobile navigation
export function MobileNav({ activeTab, onTabChange }: SidebarProps) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex md:hidden border-t bg-background">
      {navItems.map((item) => {
        const Icon = item.icon
        const isActive = activeTab === item.id

        return (
          <button
            key={item.id}
            className={cn(
              "flex flex-1 flex-col items-center gap-1 py-2 text-xs",
              isActive
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
            onClick={() => onTabChange(item.id)}
          >
            <Icon className="h-5 w-5" />
            <span>{item.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
