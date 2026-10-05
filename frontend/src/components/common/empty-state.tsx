import { InfoIcon, type LucideIcon } from "lucide-react"

export function EmptyState({
  title,
  description,
  icon: Icon = InfoIcon,
}: {
  title: string
  description?: string
  icon?: LucideIcon
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <span className="rounded-full bg-muted p-3 text-muted-foreground">
        <Icon className="size-6" />
      </span>
      <p className="font-medium text-muted-foreground">{title}</p>
      {description && <p className="max-w-sm text-sm text-muted-foreground/80">{description}</p>}
    </div>
  )
}
