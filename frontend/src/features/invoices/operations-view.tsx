"use client"

import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { FilterIcon } from "lucide-react"
import { useState } from "react"

import { AppSelect } from "@/components/common/app-select"
import { PageHeader } from "@/components/common/page-header"
import { PaginationBar } from "@/components/common/pagination-bar"
import { SearchInput } from "@/components/common/search-input"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { InvoiceDetailDialog } from "@/features/invoices/invoice-detail-dialog"
import { InvoiceTable } from "@/features/invoices/invoice-table"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { invoicesApi } from "@/lib/api/endpoints"
import type { InvoiceFilters, InvoiceType, PaymentStatus, UUID } from "@/lib/api/types"
import { rangeFor } from "@/lib/date-ranges"
import { INVOICE_TYPE_LABEL, PAYMENT_STATUS_LABEL } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

type All = "all"
const PAGE_SIZE = 15

const typeOptions = [
  { value: "all" as const, label: "Barchasi" },
  ...(Object.keys(INVOICE_TYPE_LABEL) as InvoiceType[]).map((t) => ({ value: t, label: INVOICE_TYPE_LABEL[t] })),
]
const paymentOptions = [
  { value: "all" as const, label: "Barchasi" },
  ...(Object.keys(PAYMENT_STATUS_LABEL) as PaymentStatus[]).map((s) => ({ value: s, label: PAYMENT_STATUS_LABEL[s] })),
]

interface QuickFilter {
  label: string
  apply: (state: FilterState) => FilterState
  isActive: (state: FilterState) => boolean
}

interface FilterState {
  from: string
  to: string
  type: InvoiceType | All
  payment: PaymentStatus | All
}

const quickFilters: QuickFilter[] = [
  ...(["today", "week", "month"] as const).map((preset) => ({
    label: { today: "Bugun", week: "Shu hafta", month: "Shu oy" }[preset],
    apply: (s: FilterState) => ({ ...s, ...rangeFor(preset) }),
    isActive: (s: FilterState) => s.from === rangeFor(preset).from && s.to === rangeFor(preset).to,
  })),
  {
    label: "To'lanmagan",
    apply: (s) => ({ ...s, payment: s.payment === "unpaid" ? "all" : "unpaid" }),
    isActive: (s) => s.payment === "unpaid",
  },
  {
    label: "Kirim",
    apply: (s) => ({ ...s, type: s.type === "kirim" ? "all" : "kirim" }),
    isActive: (s) => s.type === "kirim",
  },
  {
    label: "Chiqim",
    apply: (s) => ({ ...s, type: s.type === "chiqim" ? "all" : "chiqim" }),
    isActive: (s) => s.type === "chiqim",
  },
]

export function OperationsView() {
  const [state, setState] = useState<FilterState>({ ...rangeFor("month"), type: "all", payment: "all" })
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [openId, setOpenId] = useState<UUID | null>(null)
  const debouncedSearch = useDebouncedValue(search.trim())

  const update = (next: FilterState) => {
    setState(next)
    setPage(1)
  }

  const filters: InvoiceFilters = {
    type: state.type === "all" ? undefined : state.type,
    payment_status: state.payment === "all" ? undefined : state.payment,
    date_from: state.from || undefined,
    date_to: state.to || undefined,
    search: debouncedSearch || undefined,
    page,
    size: PAGE_SIZE,
  }
  const invoices = useQuery({
    queryKey: queryKeys.invoices.list(filters),
    queryFn: ({ signal }) => invoicesApi.list(filters, signal),
    placeholderData: keepPreviousData,
  })

  return (
    <>
      <PageHeader title="Operatsiyalar tarixi" subtitle="Ombor" />

      <div className="mb-4 flex flex-wrap gap-2">
        {quickFilters.map((filter) => (
          <Button
            key={filter.label}
            size="sm"
            variant="outline"
            className={cn("rounded-full", filter.isActive(state) && "border-primary bg-primary/10 text-primary")}
            onClick={() => update(filter.apply(state))}
          >
            {filter.label}
          </Button>
        ))}
      </div>

      <Card className="mb-4 gap-3 p-4">
        <p className="flex items-center gap-1.5 text-sm font-medium">
          <FilterIcon className="size-4" /> Filterlar
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="grid gap-1.5">
            <Label htmlFor="op-from">Boshlanish sanasi</Label>
            <Input id="op-from" type="date" value={state.from} onChange={(e) => update({ ...state, from: e.target.value })} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="op-to">Tugash sanasi</Label>
            <Input id="op-to" type="date" value={state.to} onChange={(e) => update({ ...state, to: e.target.value })} />
          </div>
          <div className="grid gap-1.5">
            <Label>Operatsiya turi</Label>
            <AppSelect value={state.type} options={typeOptions} onChange={(type) => update({ ...state, type })} />
          </div>
          <div className="grid gap-1.5">
            <Label>To&apos;lov holati</Label>
            <AppSelect value={state.payment} options={paymentOptions} onChange={(payment) => update({ ...state, payment })} />
          </div>
          <div className="grid gap-1.5 lg:col-span-2">
            <Label>Qidirish</Label>
            <SearchInput
              placeholder="Invoice raqami..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
            />
          </div>
        </div>
      </Card>

      <Card className="px-2 py-2">
        <InvoiceTable
          detailed
          invoices={invoices.data?.items}
          loading={invoices.isPending}
          onOpen={setOpenId}
          rowOffset={(page - 1) * PAGE_SIZE}
        />
        {invoices.data && (
          <PaginationBar page={invoices.data.page} pages={invoices.data.pages} total={invoices.data.total} onChange={setPage} />
        )}
      </Card>

      <InvoiceDetailDialog invoiceId={openId} onClose={() => setOpenId(null)} />
    </>
  )
}
