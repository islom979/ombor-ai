import { ArrowLeftIcon } from "lucide-react"
import Link from "next/link"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"

interface PageHeaderProps {
  title: string
  subtitle?: string
  backHref?: string
  actions?: ReactNode
}

export function PageHeader({ title, subtitle, backHref, actions }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-center gap-2">
        {backHref && (
          <Button variant="ghost" size="icon" nativeButton={false} render={<Link href={backHref} aria-label="Orqaga" />}>
            <ArrowLeftIcon />
          </Button>
        )}
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{title}</h1>
          {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
