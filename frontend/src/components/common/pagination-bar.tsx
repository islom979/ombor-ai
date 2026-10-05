import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"

import { Button } from "@/components/ui/button"

interface PaginationBarProps {
  page: number
  pages: number
  total: number
  onChange: (page: number) => void
}

export function PaginationBar({ page, pages, total, onChange }: PaginationBarProps) {
  return (
    <div className="flex items-center justify-between gap-2 px-1 pt-3 text-sm text-muted-foreground">
      <span>
        Sahifa {page} / {pages} · Jami: {total} ta
      </span>
      <div className="flex items-center gap-1">
        <Button variant="outline" size="icon-sm" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Oldingi">
          <ChevronLeftIcon />
        </Button>
        <Button
          variant="outline"
          size="icon-sm"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
          aria-label="Keyingi"
        >
          <ChevronRightIcon />
        </Button>
      </div>
    </div>
  )
}
