"use client"

import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query"
import { ArrowDownIcon, ArrowUpIcon, DownloadIcon, PackageSearchIcon } from "lucide-react"
import { useMemo, useState } from "react"

import { EmptyState } from "@/components/common/empty-state"
import { PageHeader } from "@/components/common/page-header"
import { SearchInput } from "@/components/common/search-input"
import { StatCard } from "@/components/common/stat-card"
import { BatchCode, LowStockBadge } from "@/components/common/status-badges"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { stockApi } from "@/lib/api/endpoints"
import { formatNumber, formatQuantity, UNIT_LABEL } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

export function StockView() {
  const [search, setSearch] = useState("")
  const [lowOnly, setLowOnly] = useState(false)
  const [sortAsc, setSortAsc] = useState(true)
  const debouncedSearch = useDebouncedValue(search.trim())

  const summary = useQuery({ queryKey: queryKeys.stock.summary, queryFn: stockApi.summary })
  const rows = useQuery({
    queryKey: queryKeys.stock.list(debouncedSearch, lowOnly),
    queryFn: ({ signal }) => stockApi.list({ search: debouncedSearch || undefined, low_only: lowOnly }, signal),
    placeholderData: keepPreviousData,
  })
  const exportCsv = useMutation({ mutationFn: stockApi.exportCsv })

  const sorted = useMemo(() => {
    const data = [...(rows.data ?? [])]
    data.sort((a, b) => a.product_name.localeCompare(b.product_name) * (sortAsc ? 1 : -1))
    return data
  }, [rows.data, sortAsc])

  return (
    <>
      <PageHeader
        title="Ombordagi tovarlar qoldig'i"
        subtitle="Ombor"
        actions={
          <Button size="lg" onClick={() => exportCsv.mutate()} disabled={exportCsv.isPending}>
            <DownloadIcon /> Yuklab olish
          </Button>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Jami mahsulotlar" value={summary.data?.total_products ?? 0} loading={summary.isPending} />
        <StatCard label="Jami partiyalar" value={summary.data?.total_batches ?? 0} loading={summary.isPending} />
        <StatCard
          label="Umumiy qiymat"
          value={formatNumber(summary.data?.total_value ?? 0)}
          hint="so'm"
          tone="primary"
          loading={summary.isPending}
        />
        <StatCard
          label="Kam qolgan"
          value={summary.data?.low_stock_count ?? 0}
          tone={summary.data?.low_stock_count ? "danger" : "default"}
          loading={summary.isPending}
        />
      </div>

      <div className="mb-3 flex flex-wrap items-end gap-4">
        <div className="min-w-64 flex-1">
          <Label className="mb-1.5 block text-sm font-medium">Mahsulot qidirish</Label>
          <SearchInput placeholder="Mahsulot nomini kiriting..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <label className="flex h-9 items-center gap-2 text-sm">
          <Switch checked={lowOnly} onCheckedChange={setLowOnly} />
          Faqat kam qolganlar
        </label>
      </div>

      <Card className="py-0">
        <Table>
          <TableHeader>
            <TableRow className="text-xs uppercase">
              <TableHead>
                <button type="button" className="flex items-center gap-1 uppercase" onClick={() => setSortAsc((v) => !v)}>
                  Mahsulot {sortAsc ? <ArrowUpIcon className="size-3" /> : <ArrowDownIcon className="size-3" />}
                </button>
              </TableHead>
              <TableHead>Birlik</TableHead>
              <TableHead>Partiya</TableHead>
              <TableHead className="text-right">Xarid narxi</TableHead>
              <TableHead className="text-right">Sotuv narxi</TableHead>
              <TableHead className="text-right">Miqdor</TableHead>
              <TableHead className="text-right">Umumiy qiymat</TableHead>
              <TableHead>Barcode</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.isPending &&
              Array.from({ length: 6 }, (_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={8}>
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))}
            {sorted.map((row) => (
              <TableRow key={row.batch_id}>
                <TableCell className="font-medium">
                  <div>{row.product_name}</div>
                  {row.is_low && <LowStockBadge />}
                </TableCell>
                <TableCell>{UNIT_LABEL[row.unit]}</TableCell>
                <TableCell>
                  <BatchCode code={row.batch_code} tone={row.is_low ? "low" : "neutral"} />
                </TableCell>
                <TableCell className="text-right tabular-nums">{formatNumber(row.purchase_price)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatNumber(row.sale_price)}</TableCell>
                <TableCell className={cn("text-right tabular-nums", row.is_low && "font-semibold text-destructive")}>
                  {formatQuantity(row.quantity)}
                </TableCell>
                <TableCell className="text-right font-semibold text-primary tabular-nums">
                  {formatNumber(row.total_value)}
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">{row.barcode ?? "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {rows.isSuccess && sorted.length === 0 && (
          <EmptyState icon={PackageSearchIcon} title="Mahsulot topilmadi" description="Qidiruv shartini o'zgartiring yoki kirim qiling" />
        )}
      </Card>
    </>
  )
}
