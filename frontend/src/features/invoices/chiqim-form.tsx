"use client"

import { useMutation } from "@tanstack/react-query"
import { CheckIcon, InfoIcon, PlusIcon, Trash2Icon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { EmptyState } from "@/components/common/empty-state"
import { PageHeader } from "@/components/common/page-header"
import { BatchCode } from "@/components/common/status-badges"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { useAuth } from "@/features/auth/auth-provider"
import { CounterpartySelect } from "@/features/counterparties/counterparty-select"
import { InvoiceDetailDialog } from "@/features/invoices/invoice-detail-dialog"
import { BatchCatalogSheet, BatchSearch, TotalsCards } from "@/features/invoices/pickers"
import { useInvalidateWarehouse } from "@/features/invoices/use-invalidate-warehouse"
import { invoicesApi } from "@/lib/api/endpoints"
import type { StockRow, UUID } from "@/lib/api/types"
import { formatNumber, formatQuantity, UNIT_LABEL } from "@/lib/format"
import { cn } from "@/lib/utils"

interface ChiqimLine {
  batch: StockRow
  price: string
  quantity: string
}

const toNumber = (value: string) => (Number.isFinite(Number(value)) ? Number(value) : 0)
const lineTotal = (line: ChiqimLine) => toNumber(line.price) * toNumber(line.quantity)

export function ChiqimForm() {
  const { canWrite } = useAuth()
  const invalidate = useInvalidateWarehouse()
  const [clientId, setClientId] = useState<UUID | null>(null)
  const [note, setNote] = useState("")
  const [withDiscount, setWithDiscount] = useState(false)
  const [discount, setDiscount] = useState("0")
  const [lines, setLines] = useState<ChiqimLine[]>([])
  const [catalogOpen, setCatalogOpen] = useState(false)
  const [createdId, setCreatedId] = useState<UUID | null>(null)

  function addBatch(batch: StockRow) {
    if (lines.some((line) => line.batch.batch_id === batch.batch_id)) {
      toast.info(`"${batch.product_name}" (${batch.batch_code}) allaqachon ro'yxatda`)
      return
    }
    setLines((prev) => [...prev, { batch, price: String(batch.sale_price), quantity: "1" }])
  }

  const updateLine = (batchId: UUID, patch: Partial<ChiqimLine>) =>
    setLines((prev) => prev.map((line) => (line.batch.batch_id === batchId ? { ...line, ...patch } : line)))

  const subtotal = lines.reduce((sum, line) => sum + lineTotal(line), 0)
  const discountPercent = withDiscount ? Math.min(100, Math.max(0, toNumber(discount))) : 0
  const total = subtotal - (subtotal * discountPercent) / 100

  const overStock = lines.find((line) => toNumber(line.quantity) > line.batch.quantity)
  const invalidLine = lines.find((line) => toNumber(line.quantity) <= 0 || line.price === "")

  const submit = useMutation({
    mutationFn: invoicesApi.createChiqim,
    onSuccess: (invoice) => {
      toast.success(`Chiqim saqlandi: ${invoice.number}`)
      invalidate()
      setLines([])
      setNote("")
      setWithDiscount(false)
      setDiscount("0")
      setCreatedId(invoice.id)
    },
  })

  function handleSubmit() {
    if (!clientId) return toast.error("Qabul qiluvchini (mijozni) tanlang")
    if (invalidLine) return toast.error(`"${invalidLine.batch.product_name}": narx va miqdorni to'ldiring`)
    if (overStock) return toast.error(`"${overStock.batch.product_name}": omborda yetarli emas`)
    submit.mutate({
      client_id: clientId,
      note: note.trim() || null,
      discount_percent: discountPercent,
      items: lines.map((line) => ({
        product_id: line.batch.product_id,
        batch_id: line.batch.batch_id,
        quantity: toNumber(line.quantity),
        unit_price: toNumber(line.price),
      })),
    })
  }

  return (
    <>
      <PageHeader
        title="Ombordan chiqim"
        actions={
          <Button size="lg" onClick={() => setCatalogOpen(true)}>
            <PlusIcon /> Mahsulotlar
          </Button>
        }
      />

      <div className="grid gap-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-1.5">
            <Label htmlFor="client">
              Qabul qiluvchi (mijoz) <span className="text-destructive">*</span>
            </Label>
            <CounterpartySelect id="client" kind="client" value={clientId} onChange={setClientId} />
          </div>
          <div className="grid gap-1.5">
            <Label>Jo&apos;natuvchi ombor</Label>
            <Input value="Ombor" disabled />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="chiqim-note">Izoh (ixtiyoriy)</Label>
          <Textarea id="chiqim-note" placeholder="Qo'shimcha ma'lumot..." value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm font-medium">
            Chegirma qo&apos;llash
            <Switch checked={withDiscount} onCheckedChange={setWithDiscount} />
          </label>
          {withDiscount && (
            <div className="flex items-center gap-1">
              <Input
                className="w-24"
                type="number"
                min={0}
                max={100}
                step="any"
                value={discount}
                onChange={(e) => setDiscount(e.target.value)}
                aria-label="Chegirma foizi"
              />
              <span className="text-sm text-muted-foreground">%</span>
            </div>
          )}
        </div>
        <div className="grid gap-1.5">
          <Label>Mahsulot qidirish</Label>
          <BatchSearch onPick={addBatch} />
        </div>

        {lines.length === 0 ? (
          <Card>
            <EmptyState icon={InfoIcon} title="Mahsulot tanlanmagan" description={`Mahsulot qidiring yoki "Mahsulotlar" tugmasidan tanlang`} />
          </Card>
        ) : (
          <>
            <TotalsCards count={lines.length} total={total} />
            {discountPercent > 0 && (
              <p className="text-sm text-muted-foreground">
                Chegirmasiz: {formatNumber(subtotal)} so&apos;m · Chegirma {discountPercent}%: −
                {formatNumber(subtotal - total)} so&apos;m
              </p>
            )}
            <Card className="py-0">
              <Table>
                <TableHeader>
                  <TableRow className="text-xs uppercase">
                    <TableHead>Nomlanishi</TableHead>
                    <TableHead>Partiya</TableHead>
                    <TableHead>Omborda</TableHead>
                    <TableHead>Sotuv narxi (so&apos;m)</TableHead>
                    <TableHead>Miqdor</TableHead>
                    <TableHead>Birlik</TableHead>
                    <TableHead className="text-right">Jami (so&apos;m)</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lines.map((line) => {
                    const requested = toNumber(line.quantity)
                    const remaining = line.batch.quantity - requested
                    return (
                      <TableRow key={line.batch.batch_id}>
                        <TableCell className="font-medium">{line.batch.product_name}</TableCell>
                        <TableCell>
                          <BatchCode code={line.batch.batch_code} />
                        </TableCell>
                        <TableCell>
                          <p className={cn("text-sm font-medium", line.batch.is_low && "text-destructive")}>
                            {formatQuantity(line.batch.quantity)} {UNIT_LABEL[line.batch.unit]}
                          </p>
                          <p className={cn("text-[11px]", remaining < 0 ? "text-destructive" : "text-muted-foreground")}>
                            Qoladi: {formatQuantity(Math.max(remaining, 0))} {UNIT_LABEL[line.batch.unit]}
                          </p>
                        </TableCell>
                        <TableCell>
                          <Input
                            className="w-28"
                            type="number"
                            min={0}
                            step="any"
                            value={line.price}
                            onChange={(e) => updateLine(line.batch.batch_id, { price: e.target.value })}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            className={cn("w-24", remaining < 0 && "border-destructive")}
                            type="number"
                            min={0}
                            max={line.batch.quantity}
                            step="any"
                            value={line.quantity}
                            onChange={(e) => updateLine(line.batch.batch_id, { quantity: e.target.value })}
                          />
                        </TableCell>
                        <TableCell>{UNIT_LABEL[line.batch.unit]}</TableCell>
                        <TableCell className="text-right font-semibold text-primary tabular-nums">
                          {formatNumber(lineTotal(line))}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label="O'chirish"
                            onClick={() => setLines((prev) => prev.filter((l) => l.batch.batch_id !== line.batch.batch_id))}
                          >
                            <Trash2Icon className="text-destructive" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </Card>
            <div className="flex justify-end">
              <Button size="lg" onClick={handleSubmit} disabled={submit.isPending || !canWrite}>
                <CheckIcon /> Yakunlash
              </Button>
            </div>
          </>
        )}
      </div>

      <BatchCatalogSheet
        open={catalogOpen}
        onOpenChange={setCatalogOpen}
        onPick={(batch) => {
          addBatch(batch)
          setCatalogOpen(false)
        }}
      />
      <InvoiceDetailDialog invoiceId={createdId} onClose={() => setCreatedId(null)} />
    </>
  )
}
