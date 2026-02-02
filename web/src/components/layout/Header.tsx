import { Moon, Sun, Github } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useTheme } from "@/hooks/useTheme"

export function Header() {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4 md:px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <span className="text-sm font-bold">TF</span>
          </div>
          <span className="text-lg font-semibold">AVM Agent</span>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </Button>

          <a
            href="https://github.com/Azure/terraform-azure-modules"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
          >
            <Button variant="ghost" size="icon">
              <Github className="h-5 w-5" />
            </Button>
          </a>
        </div>
      </div>
    </header>
  )
}
