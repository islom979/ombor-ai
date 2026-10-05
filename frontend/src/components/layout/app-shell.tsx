"use client"

import { Loader2Icon, MenuIcon, WarehouseIcon } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useState, type ReactNode } from "react"

import { AppSidebar } from "@/components/layout/app-sidebar"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet"
import { useAuth } from "@/features/auth/auth-provider"
import { cn } from "@/lib/utils"

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter()
  const { session, isLoading } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    if (!isLoading && !session) router.replace("/login")
  }, [isLoading, session, router])

  if (isLoading || !session) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        <Loader2Icon className="animate-spin" />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen">
      <div
        className={cn(
          "no-print sticky top-0 hidden h-screen shrink-0 border-r transition-[width] duration-200 md:block",
          collapsed ? "w-[72px]" : "w-60",
        )}
      >
        <AppSidebar collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
      </div>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 p-0" showCloseButton={false}>
          <SheetTitle className="sr-only">Menyu</SheetTitle>
          <AppSidebar onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print sticky top-0 z-30 flex items-center gap-2 border-b bg-background/90 px-4 py-2 backdrop-blur md:hidden">
          <Button variant="ghost" size="icon" onClick={() => setMobileOpen(true)} aria-label="Menyu">
            <MenuIcon />
          </Button>
          <WarehouseIcon className="size-5 text-primary" />
          <span className="font-semibold">Ombor AI</span>
        </header>
        <main className="mx-auto w-full max-w-[1400px] flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  )
}
