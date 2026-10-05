"use client"

import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { CalendarIcon, CheckCircle2Icon, DollarSignIcon, FileTextIcon, MapPinIcon, PhoneIcon, ReceiptIcon } from "lucide-react"
import { useState } from "react"

import { AppSelect } from "@/components/common/app-select"
import { EmptyState } from "@/components/common/empty-state"
import { PageHeader } from "@/components/common/page-header"
import { PaginationBar } from "@/components/common/pagination-bar"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuth } from "@/features/auth/auth-provider"
import { BalanceText, DETAIL_PATH } from "@/features/counterparties/counterparty-list-view"
import { PaymentDialog } from "@/features/counterparties/payment-dialog"
import { InvoiceDetailDialog } from "@/features/invoices/invoice-detail-dialog"
import { InvoiceTable } from "@/features/invoices/invoice-table"
import { counterpartiesApi, invoicesApi, paymentsApi } from "@/lib/api/endpoints"
import type { Counterparty, InvoiceFilters, PaymentStatus, UUID } from "@/lib/api/types"
import {
  formatDateTime,
  formatMoney,
  formatNumber,
  initials,
  KIND_LABEL,
  PAYMENT_METHOD_LABEL,
  PAYMENT_STATUS_LABEL,
} from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"

const paymentOptions = [
  { value: "all" as const, label: "Barchasi" },
  ...(Object.keys(PAYMENT_STATUS_LABEL) as PaymentStatus[]).map((s) => ({ value: s, label: PAYMENT_STATUS_LABEL[s] })),
]
const PAGE_SIZE = 15

function HeaderCard({ counterparty, onPay, canWrite }: { counterparty: Counterparty; onPay: () => void; canWrite: boolean }) {
  const isSupplier = counterparty.kind === "supplier"
  return (
    <Card className="mb-6 flex-row flex-wrap items-center justify-between gap-4 p-5">
      <div className="flex items-center gap-4">
        <span className="flex size-16 items-center justify-center rounded-full bg-primary text-xl font-bold text-primary-foreground">
          {initials(counterparty.name)}
        </span>
        <div className="grid gap-0.5 text-sm">
          <p className="text-lg font-bold">{counterparty.name}</p>
          <p className="flex items-center gap-1.5 text-muted-foreground">
            <PhoneIcon className="size-3.5" /> {counterparty.phone ?? "—"}
          </p>
          <p className="flex items-center gap-1.5 text-muted-foreground">
            <MapPinIcon className="size-3.5" /> {counterparty.address ?? "—"}
          </p>
          <p className="flex items-center gap-1.5 text-muted-foreground">
            <CalendarIcon className="size-3.5" /> Qo&apos;shildi: {formatDateTime(counterparty.created_at)}
          </p>
        </div>
      </div>
      <div className="grid justify-items-end gap-2">
        <p className="text-xs text-muted-foreground">Joriy balans ({isSupplier ? "bizning qarz" : "bizdan qarz"})</p>
        <BalanceText value={counterparty.balance} className="text-3xl" />
        {canWrite && (
          <Button className="bg-success text-white hover:bg-success/90" size="lg" onClick={onPay}>
            <DollarSignIcon /> To&apos;lov qilish
          </Button>
        )}
      </div>
    </Card>
  )
}

function InvoicesTab({ counterparty, canWrite }: { counterparty: Counterparty; canWrite: boolean }) {
  const [payment, setPayment] = useState<PaymentStatus | "all">("all")
  const [from, setFrom] = useState("")
  const [to, setTo] = useState("")
  const [page, setPage] = useState(1)
  const [openId, setOpenId] = useState<UUID | null>(null)
  const [selecting, setSelecting] = useState(false)
  const [selected, setSelected] = useState<Set<UUID>>(new Set())
  const [payOpen, setPayOpen] = useState(false)

  const filters: InvoiceFilters = {
    counterparty_id: counterparty.id,
    payment_status: payment === "all" ? undefined : payment,
    date_from: from || undefined,
    date_to: to || undefined,
    page,
    size: PAGE_SIZE,
  }
  const invoices = useQuery({
    queryKey: queryKeys.invoices.list(filters),
    queryFn: ({ signal }) => invoicesApi.list(filters, signal),
    placeholderData: keepPreviousData,
  })

  const selectedInvoices = (invoices.data?.items ?? []).filter((i) => selected.has(i.id))
  const outstanding = selectedInvoices.reduce((sum, i) => sum + (i.total - i.paid_amount), 0)

  const toggle = (id: UUID) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  return (
    <>
      <div className="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="grid gap-1.5">
          <Label>To&apos;lov holati</Label>
          <AppSelect
            value={payment}
            options={paymentOptions}
            onChange={(v) => {
              setPayment(v)
              setPage(1)
            }}
          />
        </div>
        <div className="grid gap-1.5">
          <Label>Boshlanish</Label>
          <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label>Tugash</Label>
          <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </div>
      </div>
      {canWrite && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="rounded-full border-primary/50 text-primary"
            onClick={() => {
              setSelecting((v) => !v)
              setSelected(new Set())
            }}
          >
            <CheckCircle2Icon /> {selecting ? "Tanlashni bekor qilish" : "Invoicelar uchun to'lov"}
          </Button>
          {selecting && selected.size > 0 && (
            <Button size="sm" className="bg-success text-white hover:bg-success/90" onClick={() => setPayOpen(true)}>
              {selected.size} ta invoice · {formatMoney(outstanding)} to&apos;lash
            </Button>
          )}
        </div>
      )}
      <Card className="px-2 py-2">
        <InvoiceTable
          invoices={invoices.data?.items}
          loading={invoices.isPending}
          onOpen={setOpenId}
          selectable={selecting}
          selected={selected}
          onToggle={toggle}
        />
        {invoices.data && invoices.data.total > 0 && (
          <PaginationBar page={invoices.data.page} pages={invoices.data.pages} total={invoices.data.total} onChange={setPage} />
        )}
      </Card>
      <InvoiceDetailDialog invoiceId={openId} onClose={() => setOpenId(null)} />
      <PaymentDialog
        counterparty={counterparty}
        open={payOpen}
        onOpenChange={setPayOpen}
        invoiceIds={[...selected]}
        suggestedAmount={outstanding}
        onPaid={() => {
          setSelected(new Set())
          setSelecting(false)
        }}
      />
    </>
  )
}

function PaymentsTab({ counterpartyId }: { counterpartyId: UUID }) {
  const [page, setPage] = useState(1)
  const payments = useQuery({
    queryKey: queryKeys.payments.list(counterpartyId, page),
    queryFn: () => paymentsApi.list({ counterparty_id: counterpartyId, page, size: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  })

  return (
    <Card className="px-2 py-2">
      <Table>
        <TableHeader>
          <TableRow className="text-xs uppercase">
            <TableHead>Summa</TableHead>
            <TableHead>Kassa</TableHead>
            <TableHead>To&apos;lov usuli</TableHead>
            <TableHead>Kim tomonidan</TableHead>
            <TableHead>Invoicelar</TableHead>
            <TableHead>Izoh</TableHead>
            <TableHead>Sana</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {payments.isPending && (
            <TableRow>
              <TableCell colSpan={7}>
                <Skeleton className="h-5" />
              </TableCell>
            </TableRow>
          )}
          {payments.data?.items.map((p) => (
            <TableRow key={p.id}>
              <TableCell className="font-semibold text-success tabular-nums">{formatNumber(p.amount)} so&apos;m</TableCell>
              <TableCell>{p.cash_register_name}</TableCell>
              <TableCell>
                <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[11px] font-semibold text-primary uppercase">
                  {PAYMENT_METHOD_LABEL[p.method]}
                </span>
              </TableCell>
              <TableCell>{p.created_by_name ?? "AI agent"}</TableCell>
              <TableCell className="text-xs">
                {p.allocations.length ? p.allocations.map((a) => a.invoice_number).join(", ") : "Umumiy to'lov"}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">{p.note ?? "—"}</TableCell>
              <TableCell className="text-sm whitespace-nowrap text-muted-foreground">{formatDateTime(p.created_at)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {payments.isSuccess && payments.data.items.length === 0 && <EmptyState icon={ReceiptIcon} title="To'lovlar hali yo'q" />}
      {payments.data && payments.data.total > 0 && (
        <PaginationBar page={payments.data.page} pages={payments.data.pages} total={payments.data.total} onChange={setPage} />
      )}
    </Card>
  )
}

export function CounterpartyDetailView({ id }: { id: UUID }) {
  const { canWrite } = useAuth()
  const [payOpen, setPayOpen] = useState(false)
  const { data: counterparty, isPending, isError } = useQuery({
    queryKey: queryKeys.counterparties.detail(id),
    queryFn: () => counterpartiesApi.get(id),
  })

  if (isError) return <EmptyState title="Kontragent topilmadi" />
  if (isPending || !counterparty) return <Skeleton className="h-40" />

  return (
    <>
      <PageHeader title={KIND_LABEL[counterparty.kind].one} backHref={DETAIL_PATH[counterparty.kind]} />
      <HeaderCard counterparty={counterparty} canWrite={canWrite} onPay={() => setPayOpen(true)} />

      <Tabs defaultValue="invoices">
        <TabsList variant="line">
          <TabsTrigger value="invoices">
            <FileTextIcon /> Invoicelar
          </TabsTrigger>
          <TabsTrigger value="payments">
            <ReceiptIcon /> To&apos;lovlar tarixi
          </TabsTrigger>
        </TabsList>
        <TabsContent value="invoices" className="pt-3">
          <InvoicesTab counterparty={counterparty} canWrite={canWrite} />
        </TabsContent>
        <TabsContent value="payments" className="pt-3">
          <PaymentsTab counterpartyId={counterparty.id} />
        </TabsContent>
      </Tabs>

      <PaymentDialog counterparty={counterparty} open={payOpen} onOpenChange={setPayOpen} />
    </>
  )
}
