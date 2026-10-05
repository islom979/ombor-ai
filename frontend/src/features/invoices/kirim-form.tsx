"use client"

import { useMutation } from "@tanstack/react-query"
import { CheckIcon, InfoIcon, PlusIcon, Trash2Icon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { EmptyState } from "@/components/common/empty-state"
import { PageHeader } from "@/components/common/page-header"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { useAuth } from "@/features/auth/auth-provider"
import { CounterpartySelect } from "@/features/counterparties/counterparty-select"
import { InvoiceDetailDialog } from "@/features/invoices/invoice-detail-dialog"
import { NewProductDialog } from "@/features/invoices/new-product-dialog"
import { ProductCatalogSheet, ProductSearch, TotalsCards } from "@/features/invoices/pickers"
import { useInvalidateWarehouse } from "@/features/invoices/use-invalidate-warehouse"
import { invoicesApi } from "@/lib/api/endpoints"
import type { Product, ProductUnit, UUID } from "@/lib/api/types"
import { formatNumber, UNIT_LABEL } from "@/lib/format"

interface KirimLine {
  productId: UUID
  name: string
  unit: ProductUnit
  previousPurchase: number | null
  previousSale: number
  purchasePrice: string
  salePrice: string
  quantity: string
}

type PickedProduct = Pick<Product, "id" | "name" | "unit" | "default_sale_price"> & { last_purchase_price?: number | null }

const toNumber = (value: string) => (Number.isFinite(Number(value)) ? Number(value) : 0)
const lineTotal = (line: KirimLine) => toNumber(line.purchasePrice) * toNumber(line.quantity)

export function KirimForm() {
  const { canWrite } = useAuth()
  const invalidate = useInvalidateWarehouse()
  const [supplierId, setSupplierId] = useState<UUID | null>(null)
  const [note, setNote] = useState("")
  const [lines, setLines] = useState<KirimLine[]>([])
  const [catalogOpen, setCatalogOpen] = useState(false)
  const [newProductOpen, setNewProductOpen] = useState(false)
  const [createdId, setCreatedId] = useState<UUID | null>(null)

  function addProduct(product: PickedProduct) {
    if (lines.some((line) => line.productId === product.id)) {
      toast.info(`"${product.name}" allaqachon ro'yxatda`)
      return
    }
    const purchase = product.last_purchase_price ?? null
    setLines((prev) => [
      ...prev,
      {
        productId: product.id,
        name: product.name,
        unit: product.unit,
        previousPurchase: purchase,
        previousSale: product.default_sale_price,
        purchasePrice: purchase !== null ? String(purchase) : "",
        salePrice: product.default_sale_price ? String(product.default_sale_price) : "",
        quantity: "1",
      },
    ])
  }

  const updateLine = (productId: UUID, patch: Partial<KirimLine>) =>
    setLines((prev) => prev.map((line) => (line.productId === productId ? { ...line, ...patch } : line)))

  const total = lines.reduce((sum, line) => sum + lineTotal(line), 0)
  const invalidLine = lines.find(
    (line) => toNumber(line.quantity) <= 0 || line.purchasePrice === "" || line.salePrice === "",
  )

  const submit = useMutation({
    mutationFn: invoicesApi.createKirim,
    onSuccess: (invoice) => {
      toast.success(`Kirim saqlandi: ${invoice.number}`)
      invalidate()
      setLines([])
      setNote("")
      setCreatedId(invoice.id)
    },
  })

  function handleSubmit() {
    if (!supplierId) return toast.error("Jo'natuvchini tanlang")
    if (invalidLine) return toast.error(`"${invalidLine.name}": narx va miqdorni to'ldiring`)
    submit.mutate({
      supplier_id: supplierId,
      note: note.trim() || null,
      items: lines.map((line) => ({
        product_id: line.productId,
        quantity: toNumber(line.quantity),
        purchase_price: toNumber(line.purchasePrice),
        sale_price: toNumber(line.salePrice),
      })),
    })
  }

  return (
    <>
      <PageHeader
        title="Omborga kirim"
        actions={
          <Button size="lg" onClick={() => setCatalogOpen(true)}>
            <PlusIcon /> Mahsulotlar
          </Button>
        }
      />

      <div className="grid gap-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-1.5">
            <Label htmlFor="supplier">
              Jo&apos;natuvchi <span className="text-destructive">*</span>
            </Label>
            <CounterpartySelect id="supplier" kind="supplier" value={supplierId} onChange={setSupplierId} />
          </div>
          <div className="grid gap-1.5">
            <Label>Qabul qiluvchi ombor</Label>
            <Input value="Ombor" disabled />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="kirim-note">Izoh (ixtiyoriy)</Label>
          <Textarea id="kirim-note" placeholder="Qo'shimcha ma'lumot..." value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label>Mahsulot qidirish</Label>
          <ProductSearch onPick={addProduct} />
        </div>

        {lines.length === 0 ? (
          <Card>
            <EmptyState
              icon={InfoIcon}
              title="Mahsulot tanlanmagan"
              description={`Mahsulot qidiring yoki "Mahsulotlar" tugmasidan tanlang`}
            />
          </Card>
        ) : (
          <>
            <TotalsCards count={lines.length} total={total} />
            <Card className="py-0">
              <Table>
                <TableHeader>
                  <TableRow className="text-xs uppercase">
                    <TableHead>Nomlanishi</TableHead>
                    <TableHead>Birlik</TableHead>
                    <TableHead>Narx (so&apos;m)</TableHead>
                    <TableHead>Sotuv narxi (so&apos;m)</TableHead>
                    <TableHead>Miqdor</TableHead>
                    <TableHead className="text-right">Jami (so&apos;m)</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lines.map((line) => (
                    <TableRow key={line.productId}>
                      <TableCell className="font-medium">{line.name}</TableCell>
                      <TableCell>{UNIT_LABEL[line.unit]}</TableCell>
                      <TableCell>
                        <Input
                          className="w-28"
                          type="number"
                          min={0}
                          step="any"
                          value={line.purchasePrice}
                          onChange={(e) => updateLine(line.productId, { purchasePrice: e.target.value })}
                        />
                        {line.previousPurchase !== null && (
                          <p className="mt-0.5 text-[11px] text-muted-foreground">Oldingi: {formatNumber(line.previousPurchase)}</p>
                        )}
                      </TableCell>
                      <TableCell>
                        <Input
                          className="w-28"
                          type="number"
                          min={0}
                          step="any"
                          value={line.salePrice}
                          onChange={(e) => updateLine(line.productId, { salePrice: e.target.value })}
                        />
                        {line.previousSale > 0 && (
                          <p className="mt-0.5 text-[11px] text-muted-foreground">Oldingi: {formatNumber(line.previousSale)}</p>
                        )}
                      </TableCell>
                      <TableCell>
                        <Input
                          className="w-24"
                          type="number"
                          min={0}
                          step="any"
                          value={line.quantity}
                          onChange={(e) => updateLine(line.productId, { quantity: e.target.value })}
                        />
                      </TableCell>
                      <TableCell className="text-right font-semibold text-primary tabular-nums">
                        {formatNumber(lineTotal(line))}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label="O'chirish"
                          onClick={() => setLines((prev) => prev.filter((l) => l.productId !== line.productId))}
                        >
                          <Trash2Icon className="text-destructive" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
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

      <ProductCatalogSheet
        open={catalogOpen}
        onOpenChange={setCatalogOpen}
        onPick={(product) => {
          addProduct(product)
          setCatalogOpen(false)
        }}
        onCreateNew={() => setNewProductOpen(true)}
      />
      <NewProductDialog
        open={newProductOpen}
        onOpenChange={setNewProductOpen}
        onCreated={(product) => {
          addProduct(product)
          setCatalogOpen(false)
        }}
      />
      <InvoiceDetailDialog invoiceId={createdId} onClose={() => setCreatedId(null)} />
    </>
  )
}
