"use client"

import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { BotIcon, FileClockIcon, MapPinIcon, RefreshCwIcon, UserIcon, UserXIcon } from "lucide-react"
import { useState } from "react"

import { EmptyState } from "@/components/common/empty-state"
import { PageHeader } from "@/components/common/page-header"
import { PaginationBar } from "@/components/common/pagination-bar"
import { SearchInput } from "@/components/common/search-input"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAuth } from "@/features/auth/auth-provider"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { auditApi } from "@/lib/api/endpoints"
import type { AuditCategory, AuditFilters, AuditLog } from "@/lib/api/types"
import { actionKind, actionLabel, actorName, countryFlag, deviceLabel, location } from "@/lib/audit-labels"
import { formatDateTime, ROLE_LABEL } from "@/lib/format"
import { cn } from "@/lib/utils"

const PAGE_SIZE = 30

const CATEGORIES: { value: AuditCategory | "all"; label: string }[] = [
  { value: "all", label: "Barchasi" },
  { value: "auth", label: "Kirish / chiqish" },
  { value: "write", label: "O'zgartirishlar" },
  { value: "read", label: "Ko'rishlar" },
  { value: "error", label: "Xatolar" },
]

const kindClass = {
  auth: "bg-primary/10 text-primary",
  write: "bg-warning/15 text-amber-700 dark:text-warning",
  read: "bg-muted text-muted-foreground",
}

function StatusPill({ code }: { code: number }) {
  const tone =
    code >= 500 ? "bg-destructive text-white"
    : code >= 400 ? "bg-destructive/10 text-destructive"
    : "bg-success/15 text-success"
  return <span className={cn("rounded px-1.5 py-0.5 font-mono text-[11px] font-semibold", tone)}>{code}</span>
}

function ActorIcon({ kind }: { kind: AuditLog["actor_kind"] }) {
  const Icon = kind === "agent" ? BotIcon : kind === "anonymous" ? UserXIcon : UserIcon
  return <Icon className={cn("size-3.5 shrink-0", kind === "anonymous" ? "text-destructive" : "text-muted-foreground")} />
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[130px_1fr] gap-2 border-b py-1.5 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="min-w-0 break-words">{children}</span>
    </div>
  )
}

function AuditDetail({ log, onClose }: { log: AuditLog | null; onClose: () => void }) {
  const hasCoords = log?.latitude != null && log?.longitude != null
  return (
    <Dialog open={Boolean(log)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        {log && (
          <>
            <DialogHeader>
              <DialogTitle>{actionLabel(log.action)}</DialogTitle>
              <p className="text-xs text-muted-foreground">#{log.id} · {formatDateTime(log.created_at)}</p>
            </DialogHeader>
            <div>
              <Field label="Bajaruvchi">
                {actorName(log)}
                {log.user_role && ` (${ROLE_LABEL[log.user_role]})`}
              </Field>
              <Field label="So'rov">
                <span className="font-mono text-xs">
                  {log.method} {log.path}
                  {log.query && `?${log.query}`}
                </span>
              </Field>
              <Field label="Natija">
                <StatusPill code={log.status_code} /> · {log.duration_ms} ms
              </Field>
              <Field label="IP manzil">
                <span className="font-mono">{log.ip ?? "—"}</span>
              </Field>
              <Field label="Joylashuv">
                {countryFlag(log.country)} {location(log)}
                {hasCoords && (
                  <a
                    className="ml-2 inline-flex items-center gap-0.5 text-primary hover:underline"
                    href={`https://www.openstreetmap.org/?mlat=${log.latitude}&mlon=${log.longitude}#map=11/${log.latitude}/${log.longitude}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <MapPinIcon className="size-3.5" /> xaritada
                  </a>
                )}
              </Field>
              <Field label="Qurilma">
                {deviceLabel(log.user_agent)}
                <span className="block text-xs text-muted-foreground">{log.user_agent}</span>
              </Field>
              {Object.keys(log.path_params).length > 0 && (
                <Field label="Obyekt">
                  <span className="font-mono text-xs">{JSON.stringify(log.path_params)}</span>
                </Field>
              )}
              {log.request_id && (
                <Field label="So'rov ID">
                  <span className="font-mono text-xs">{log.request_id}</span>
                </Field>
              )}
            </div>
            {log.request_body != null && (
              <div>
                <p className="mb-1 text-sm font-medium">Yuborilgan ma&apos;lumot</p>
                <pre className="max-h-64 overflow-auto rounded-md bg-muted p-2 font-mono text-[11px] whitespace-pre-wrap">
                  {JSON.stringify(log.request_body, null, 2)}
                </pre>
              </div>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export function AuditView() {
  const { isAdmin } = useAuth()
  const [category, setCategory] = useState<AuditCategory | "all">("all")
  const [search, setSearch] = useState("")
  const [ip, setIp] = useState("")
  const [from, setFrom] = useState("")
  const [to, setTo] = useState("")
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<AuditLog | null>(null)
  const debouncedSearch = useDebouncedValue(search.trim())
  const debouncedIp = useDebouncedValue(ip.trim())

  const filters: AuditFilters = {
    category: category === "all" ? undefined : category,
    search: debouncedSearch || undefined,
    ip: debouncedIp || undefined,
    date_from: from || undefined,
    date_to: to || undefined,
    page,
    size: PAGE_SIZE,
  }
  const logs = useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: ({ signal }) => auditApi.list(filters, signal),
    placeholderData: keepPreviousData,
    enabled: isAdmin,
  })

  if (!isAdmin) return <EmptyState title="Bu sahifa faqat admin uchun" />

  const resetPage = <T,>(setter: (v: T) => void) => (value: T) => {
    setter(value)
    setPage(1)
  }

  return (
    <>
      <PageHeader
        title="Loglar"
        subtitle="Tizimdagi har bir amal: kim, qachon, qayerdan"
        actions={
          <Button variant="ghost" size="icon" onClick={() => logs.refetch()} aria-label="Yangilash">
            <RefreshCwIcon className={cn(logs.isFetching && "animate-spin")} />
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        {CATEGORIES.map((c) => (
          <Button
            key={c.value}
            size="sm"
            variant="outline"
            className={cn("rounded-full", category === c.value && "border-primary bg-primary/10 text-primary")}
            onClick={() => resetPage(setCategory)(c.value)}
          >
            {c.label}
          </Button>
        ))}
      </div>

      <Card className="mb-4 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="grid gap-1.5">
          <Label>Qidirish</Label>
          <SearchInput placeholder="Email, yo'l yoki shahar..." value={search} onChange={(e) => resetPage(setSearch)(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="audit-ip">IP manzil</Label>
          <Input id="audit-ip" placeholder="213.230.100.7" value={ip} onChange={(e) => resetPage(setIp)(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="audit-from">Boshlanish</Label>
          <Input id="audit-from" type="date" value={from} onChange={(e) => resetPage(setFrom)(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="audit-to">Tugash</Label>
          <Input id="audit-to" type="date" value={to} onChange={(e) => resetPage(setTo)(e.target.value)} />
        </div>
      </Card>

      <Card className="px-2 py-2">
        <Table>
          <TableHeader>
            <TableRow className="text-xs uppercase">
              <TableHead>Vaqt</TableHead>
              <TableHead>Foydalanuvchi</TableHead>
              <TableHead>Amal</TableHead>
              <TableHead>Natija</TableHead>
              <TableHead>IP</TableHead>
              <TableHead>Joylashuv</TableHead>
              <TableHead>Qurilma</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs.isPending &&
              Array.from({ length: 8 }, (_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={7}>
                    <Skeleton className="h-5" />
                  </TableCell>
                </TableRow>
              ))}
            {logs.data?.items.map((log) => {
              const kind = actionKind(log)
              return (
                <TableRow key={log.id} className="cursor-pointer" onClick={() => setSelected(log)}>
                  <TableCell className="text-sm whitespace-nowrap text-muted-foreground">{formatDateTime(log.created_at)}</TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1.5 text-sm">
                      <ActorIcon kind={log.actor_kind} />
                      <span className="max-w-48 truncate">{actorName(log)}</span>
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className={cn("rounded px-1.5 py-0.5 text-xs font-medium", kindClass[kind])}>{actionLabel(log.action)}</span>
                    <span className="mt-0.5 block font-mono text-[11px] text-muted-foreground">
                      {log.method} {log.path}
                    </span>
                  </TableCell>
                  <TableCell>
                    <StatusPill code={log.status_code} />
                    <span className="mt-0.5 block text-[11px] text-muted-foreground">{log.duration_ms} ms</span>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{log.ip ?? "—"}</TableCell>
                  <TableCell className="text-sm whitespace-nowrap">
                    {countryFlag(log.country)} {log.city ?? log.country ?? "—"}
                  </TableCell>
                  <TableCell className="text-sm whitespace-nowrap">{deviceLabel(log.user_agent)}</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
        {logs.isSuccess && logs.data.items.length === 0 && <EmptyState icon={FileClockIcon} title="Loglar topilmadi" />}
        {logs.data && logs.data.total > 0 && (
          <PaginationBar page={logs.data.page} pages={logs.data.pages} total={logs.data.total} onChange={setPage} />
        )}
      </Card>

      <AuditDetail log={selected} onClose={() => setSelected(null)} />
    </>
  )
}
