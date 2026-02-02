import { useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { GenerateRequest, GeneratedFile } from "@/types"

interface UseGenerateOptions {
  onSuccess?: (files: GeneratedFile[]) => void
  onError?: (error: Error) => void
}

export function useGenerate(options: UseGenerateOptions = {}) {
  const mutation = useMutation({
    mutationFn: async (request: GenerateRequest) => {
      const response = await api.generateTerraform(request)
      if (!response.success) {
        throw new Error(response.message || "Failed to generate Terraform")
      }
      return response.files
    },
    onSuccess: (files) => {
      options.onSuccess?.(files)
    },
    onError: (error: Error) => {
      options.onError?.(error)
    },
  })

  return {
    generate: mutation.mutate,
    generateAsync: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error,
    data: mutation.data,
    reset: mutation.reset,
  }
}
