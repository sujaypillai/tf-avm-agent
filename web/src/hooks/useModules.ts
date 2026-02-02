import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { ModuleSearchParams } from "@/types"

export function useModules(params?: ModuleSearchParams) {
  return useQuery({
    queryKey: ["modules", params],
    queryFn: () => api.listModules(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useModuleSearch(query: string) {
  return useQuery({
    queryKey: ["modules", "search", query],
    queryFn: () => api.searchModules(query),
    enabled: query.length >= 2,
    staleTime: 5 * 60 * 1000,
  })
}

export function useModulesByCategory(category: string) {
  return useModules({ category: category as ModuleSearchParams["category"] })
}
