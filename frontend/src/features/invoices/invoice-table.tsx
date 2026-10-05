"use client"

import { EyeIcon, FileSearchIcon, SparklesIcon } from "lucide-react"

import { EmptyState } from "@/components/common/empty-state"
import { AcceptedBadge, InvoiceTypeBadge, PaymentStatusBadge } from "@/components/common/status-badges"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Invoice, UUID } from "@/lib/api/types"
import { formatDateTime, formatMoney } from "@/lib/format"

interface InvoiceTableProps {
  invoices: Invoice[] | undefined
  loading: boolean
  onOpen: (id: UUID) => void
  /** Operatsiyalar sahifasi uchun to'liq ko'rinish (tur, jo'natuvchi/qabul qiluvchi). */
  detailed?: boolean
  rowOffset?: number
  selectable?: boolean
  selected?: Set<UUID>
  onToggle?: (id: UUID) => void
}

function counterpartyColumns(invoice: Invoice): [string, string] {
  const name = invoice.counterparty?.name ?? "—"
  return invoice.type === "kirim" ? [name, "Ombor"] : ["Ombor", invoice.type === "chiqim" ? name : "Hisobdan chiqarildi"]
}

export function InvoiceTable({
  invoices,
  loading,
  onOpen,
  detailed = false,
  rowOffset = 0,
  selectable = false,
  selected,
  onToggle,
}: InvoiceTableProps) {
  const columns = detailed ? 10 : 6
  return (
    <>
      <Table>
        <TableHeader>
          <TableRow className="text-xs uppercase">
            {selectable && <TableHead className="w-8" />}
            {detailed && <TableHead>#</TableHead>}
            <TableHead>Invoice №</TableHead>
            {detailed && <TableHead>Turi</TableHead>}
            {!detailed && <TableHead>Summa</TableHead>}
            {!detailed && <TableHead>To&apos;lov holati</TableHead>}
            <TableHead>Sana</TableHead>
            {detailed && <TableHead className="text-right">Summa</TableHead>}
            {detailed && <TableHead>Status</TableHead>}
            {detailed && <TableHead>To&apos;lov</TableHead>}
            {detailed && <TableHead>Jo&apos;natuvchi</TableHead>}
            {detailed && <TableHead>Qabul qiluvchi</TableHead>}
            <TableHead className="text-right">Amallar</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading &&
            Array.from({ length: 5 }, (_, i) => (
              <TableRow key={i}>
                <TableCell colSpan={columns + (selectable ? 1 : 0)}>
                  <Skeleton className="h-5 w-full" />
                </TableCell>
              </TableRow>
            ))}
          {invoices?.map((invoice, index) => {
            const [from, to] = counterpartyColumns(invoice)
            const canSelect = selectable && invoice.payment_status !== "paid"
            return (
              <TableRow key={invoice.id} data-state={selected?.has(invoice.id) ? "selected" : undefined}>
                {selectable && (
                  <TableCell>
                    {canSelect && (
                      <input
                        type="checkbox"
                        className="size-4 accent-primary"
                        checked={selected?.has(invoice.id) ?? false}
                        onChange={() => onToggle?.(invoice.id)}
                        aria-label={`${invoice.number} ni tanlash`}
                      />
                    )}
                  </TableCell>
                )}
                {detailed && <TableCell>{rowOffset + index + 1}</TableCell>}
                <TableCell className="font-mono text-xs">
                  <span className="inline-flex items-center gap-1">
                    {invoice.number}
                    {invoice.source === "ai" && <SparklesIcon className="size-3 text-primary" aria-label="AI orqali" />}
                  </span>
                </TableCell>
                {detailed && (
                  <TableCell>
                    <InvoiceTypeBadge type={invoice.type} />
                  </TableCell>
                )}
                {!detailed && <TableCell className="font-medium tabular-nums">{formatMoney(invoice.total)}</TableCell>}
                {!detailed && (
                  <TableCell>
                    <PaymentStatusBadge status={invoice.payment_status} />
                  </TableCell>
                )}
                <TableCell className="text-sm whitespace-nowrap text-muted-foreground">{formatDateTime(invoice.created_at)}</TableCell>
                {detailed && (
                  <TableCell className="text-right font-semibold text-primary tabular-nums">{formatMoney(invoice.total)}</TableCell>
                )}
                {detailed && (
                  <TableCell>
                    <AcceptedBadge />
                  </TableCell>
                )}
                {detailed && (
                  <TableCell>
                    {invoice.type === "utilizatsiya" ? "—" : <PaymentStatusBadge status={invoice.payment_status} />}
                  </TableCell>
                )}
                {detailed && <TableCell className="text-sm">{from}</TableCell>}
                {detailed && <TableCell className="text-sm">{to}</TableCell>}
                <TableCell className="text-right">
                  {detailed ? (
                    <Button variant="ghost" size="icon-sm" onClick={() => onOpen(invoice.id)} aria-label="Ko'rish">
                      <EyeIcon className="text-primary" />
                    </Button>
                  ) : (
                    <Button variant="outline" size="xs" onClick={() => onOpen(invoice.id)}>
                      Batafsil
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      {!loading && invoices?.length === 0 && <EmptyState icon={FileSearchIcon} title="Invoicelar topilmadi" />}
    </>
  )
}
