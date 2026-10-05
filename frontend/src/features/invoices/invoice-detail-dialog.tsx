"use client"

import { useQuery } from "@tanstack/react-query"
import { PrinterIcon } from "lucide-react"

import { AcceptedBadge, BatchCode, InvoiceTypeBadge, PaymentStatusBadge } from "@/components/common/status-badges"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { invoicesApi } from "@/lib/api/endpoints"
import type { InvoiceDetail, UUID } from "@/lib/api/types"
import { formatDateTime, formatMoney, formatNumber, formatQuantity, UNIT_LABEL } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"

function parties(invoice: InvoiceDetail): { from: string; to: string } {
  const name = invoice.counterparty?.name ?? "—"
  switch (invoice.type) {
    case "kirim":
      return { from: name, to: "Bizning ombor" }
    case "chiqim":
      return { from: "Ombor", to: name }
    case "utilizatsiya":
      return { from: "Ombor", to: "Hisobdan chiqarildi" }
  }
}

function InfoBox({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border p-3">
      <p className="mb-1 text-xs text-muted-foreground">{label}</p>
      <div className="font-medium">{children}</div>
    </div>
  )
}

export function InvoiceDetailDialog({ invoiceId, onClose }: { invoiceId: UUID | null; onClose: () => void }) {
  const { data: invoice, isPending } = useQuery({
    queryKey: queryKeys.invoices.detail(invoiceId ?? ""),
    queryFn: () => invoicesApi.get(invoiceId!),
    enabled: Boolean(invoiceId),
  })

  return (
    <Dialog open={Boolean(invoiceId)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="print-area max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <div className="flex flex-wrap items-start justify-between gap-2 pr-8">
            <div>
              <DialogTitle className="text-lg">Invoice tafsilotlari</DialogTitle>
              <p className="font-mono text-xs text-muted-foreground">{invoice?.number}</p>
            </div>
            {invoice && (
              <div className="flex gap-1">
                <InvoiceTypeBadge type={invoice.type} />
                <AcceptedBadge />
              </div>
            )}
          </div>
        </DialogHeader>

        {isPending || !invoice ? (
          <div className="grid gap-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-32" />
          </div>
        ) : (
          <div className="grid gap-4">
            <div className="grid grid-cols-2 gap-3">
              <InfoBox label="Sana va vaqt">{formatDateTime(invoice.created_at)}</InfoBox>
              <InfoBox label="To'lov holati">
                <PaymentStatusBadge status={invoice.payment_status} />
              </InfoBox>
              <InfoBox label="Jo'natuvchi">{parties(invoice).from}</InfoBox>
              <InfoBox label="Qabul qiluvchi">{parties(invoice).to}</InfoBox>
            </div>

            <div>
              <p className="mb-2 font-semibold">Mahsulotlar</p>
              <Table>
                <TableHeader>
                  <TableRow className="text-xs uppercase">
                    <TableHead>#</TableHead>
                    <TableHead>Mahsulot</TableHead>
                    <TableHead>Partiya</TableHead>
                    <TableHead className="text-right">Narx</TableHead>
                    <TableHead className="text-right">Miqdor</TableHead>
                    <TableHead className="text-right">Jami</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoice.items.map((item, index) => (
                    <TableRow key={item.id}>
                      <TableCell>{index + 1}</TableCell>
                      <TableCell>
                        <div className="font-medium">{item.product_name}</div>
                        <div className="text-xs text-muted-foreground">{UNIT_LABEL[item.unit]}</div>
                      </TableCell>
                      <TableCell>
                        <BatchCode code={item.batch_code} />
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{formatNumber(item.unit_price)}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatQuantity(item.quantity)}</TableCell>
                      <TableCell className="text-right font-semibold tabular-nums">{formatNumber(item.line_total)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="grid gap-1 rounded-lg bg-primary/5 p-4">
              {invoice.discount_amount > 0 && (
                <>
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>Oraliq summa</span>
                    <span>{formatMoney(invoice.subtotal)}</span>
                  </div>
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>Chegirma ({invoice.discount_percent}%)</span>
                    <span>−{formatMoney(invoice.discount_amount)}</span>
                  </div>
                </>
              )}
              <div className="flex justify-between text-lg font-semibold">
                <span>Jami:</span>
                <span className="text-primary">{formatMoney(invoice.total)}</span>
              </div>
              {invoice.type !== "utilizatsiya" && invoice.paid_amount > 0 && (
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>To&apos;langan</span>
                  <span>{formatMoney(invoice.paid_amount)}</span>
                </div>
              )}
            </div>
            {invoice.note && <p className="text-sm text-muted-foreground">Izoh: {invoice.note}</p>}
          </div>
        )}

        <DialogFooter className="no-print">
          <Button variant="outline" onClick={onClose}>
            Yopish
          </Button>
          <Button onClick={() => window.print()} disabled={!invoice}>
            <PrinterIcon /> Chop etish
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
