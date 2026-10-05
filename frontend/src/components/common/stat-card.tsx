import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

interface StatCardProps {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: LucideIcon
  tone?: "default" | "primary" | "success" | "danger"
  loading?: boolean
}

const toneClass = {
  default: "text-foreground",
  primary: "text-primary",
  success: "text-success",
  danger: "text-destructive",
}

export function StatCard({ label, value, hint, icon: Icon, tone = "default", loading }: StatCardProps) {
  return (
    <Card className="gap-1 px-4 py-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</p>
        {Icon && (
          <span className="rounded-lg bg-muted p-2 text-muted-foreground">
            <Icon className="size-4" />
          </span>
        )}
      </div>
      {loading ? (
        <Skeleton className="h-8 w-24" />
      ) : (
        <p className={cn("text-2xl font-bold tabular-nums", toneClass[tone])}>{value}</p>
      )}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </Card>
  )
}
