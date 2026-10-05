"use client"

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "next-themes"
import { useState, type ReactNode } from "react"
import { toast } from "sonner"

import { Toaster } from "@/components/ui/sonner"
import { AuthProvider } from "@/features/auth/auth-provider"
import { ApiError, errorMessage } from "@/lib/api/client"

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        refetchOnWindowFocus: false,
        // 4xx xatolarda qayta urinish ma'nosiz.
        retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
      },
    },
    // Barcha mutatsiya xatolari bitta joyda ko'rsatiladi.
    mutationCache: new MutationCache({
      onError: (error) => toast.error(errorMessage(error)),
    }),
  })
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient)
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>{children}</AuthProvider>
        <Toaster richColors position="top-right" />
      </QueryClientProvider>
    </ThemeProvider>
  )
}
