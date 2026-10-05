"use client"

import { keepPreviousData, useQuery } from "@tanstack/react-query"
import {
  ArrowDownCircleIcon,
  ArrowUpCircleIcon,
  Building2Icon,
  CalendarIcon,
  PackageIcon,
  RefreshCwIcon,
  Trash2Icon,
  TrendingUpIcon,
  UsersIcon,
  WalletIcon,
  type LucideIcon,
} from "lucide-react"
import { useState } from "react"

import { PageHeader } from "@/components/common/page-header"
import { StatCard } from "@/components/common/stat-card"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { statisticsApi } from "@/lib/api/endpoints"
import type { InvoiceType } from "@/lib/api/types"
import { matchPreset, RANGE_LABEL, rangeFor, type DateRange, type RangePreset } from "@/lib/date-ranges"
import { formatMoney, formatNumber, INVOICE_TYPE_LABEL } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

const OPERATION_ICON: Record<InvoiceType, { icon: LucideIcon; className: string }> = {
  kirim: { icon: ArrowDownCircleIcon, className: "text-success bg-success/15" },
  chiqim: { icon: ArrowUpCircleIcon, className: "text-primary bg-primary/10" },
  utilizatsiya: { icon: Trash2Icon, className: "text-amber-700 dark:text-warning bg-warning/15" },
}

export function StatisticsView() {
  const [range, setRange] = useState<DateRange>(rangeFor("today"))
  const activePreset = matchPreset(range)

  const stats = useQuery({
    queryKey: queryKeys.statistics(range.from, range.to),
    queryFn: () => statisticsApi.get({ date_from: range.from || undefined, date_to: range.to || undefined }),
    placeholderData: keepPreviousData,
  })
  const data = stats.data

  return (
    <>
      <PageHeader
        title="Statistika"
        subtitle="Ombor"
        actions={
          <Button variant="ghost" size="icon" onClick={() => stats.refetch()} aria-label="Yangilash">
            <RefreshCwIcon className={cn(stats.isFetching && "animate-spin")} />
          </Button>
        }
      />

      <Card className="mb-6 gap-3 p-4">
        <p className="flex items-center gap-2 font-medium">
          <CalendarIcon className="size-4 text-primary" /> Sana oralig&apos;i
        </p>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(RANGE_LABEL) as RangePreset[]).map((preset) => (
            <Button
              key={preset}
              size="sm"
              variant={activePreset === preset ? "default" : "outline"}
              className="rounded-full"
              onClick={() => setRange(rangeFor(preset))}
            >
              {RANGE_LABEL[preset]}
            </Button>
          ))}
        </div>
        <div className="grid gap-3 border-t pt-3 sm:grid-cols-2">
          <div className="grid gap-1.5">
            <Label htmlFor="st-from">Boshlanish</Label>
            <Input id="st-from" type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="st-to">Tugash</Label>
            <Input id="st-to" type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} />
          </div>
        </div>
      </Card>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Ta'minotchilar" value={data?.suppliers_count ?? 0} icon={Building2Icon} loading={!data} />
        <StatCard label="Klientlar" value={data?.clients_count ?? 0} icon={UsersIcon} loading={!data} />
        <StatCard label="Mahsulotlar" value={data?.products_count ?? 0} icon={PackageIcon} loading={!data} />
        <StatCard
          label="Foyda"
          value={formatNumber(data?.profit ?? 0)}
          hint={data ? `Tushum ${formatMoney(data.revenue)}` : undefined}
          icon={TrendingUpIcon}
          tone={(data?.profit ?? 0) > 0 ? "success" : (data?.profit ?? 0) < 0 ? "danger" : "default"}
          loading={!data}
        />
      </div>

      <h2 className="mb-3 text-xl font-semibold">Kassalar ({data?.cash_registers.length ?? 0})</h2>
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {!data && <Skeleton className="h-20" />}
        {data?.cash_registers.map((register) => (
          <Card key={register.id} className="gap-1 p-4">
            <p className="flex items-center gap-2 font-medium">
              <WalletIcon className="size-4 text-primary" /> {register.name}
            </p>
            <p className={cn("text-2xl font-bold tabular-nums", register.balance < 0 ? "text-destructive" : "text-success")}>
              {formatMoney(register.balance)}
            </p>
          </Card>
        ))}
      </div>

      <h2 className="mb-3 text-xl font-semibold">Operatsiyalar</h2>
      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        {data?.operations.map((op) => {
          const { icon: Icon, className } = OPERATION_ICON[op.type]
          return (
            <Card key={op.type} className="gap-2 p-4">
              <div className="flex items-center justify-between">
                <p className="flex items-center gap-2 font-medium">
                  <span className={cn("rounded-full p-1", className)}>
                    <Icon className="size-4" />
                  </span>
                  {INVOICE_TYPE_LABEL[op.type]}
                </p>
                <span className={cn("rounded px-1.5 py-0.5 text-xs font-semibold", className)}>{op.count} TA</span>
              </div>
              <p className="text-xl font-bold tabular-nums">{formatMoney(op.total)}</p>
            </Card>
          )
        })}
      </div>

      <h2 className="mb-3 text-xl font-semibold">Qarzdorlik</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <StatCard label="Klientlar bizga qarzdor" value={formatMoney(data?.receivables ?? 0)} tone="danger" loading={!data} />
        <StatCard label="Ta'minotchilarga qarzimiz" value={formatMoney(data?.payables ?? 0)} tone="primary" loading={!data} />
      </div>
    </>
  )
}
