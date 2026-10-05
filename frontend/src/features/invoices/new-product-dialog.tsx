"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, type FormEvent } from "react"
import { toast } from "sonner"

import { AppSelect } from "@/components/common/app-select"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { productsApi } from "@/lib/api/endpoints"
import type { Product, ProductUnit } from "@/lib/api/types"
import { UNIT_LABEL } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"

const unitOptions = (Object.keys(UNIT_LABEL) as ProductUnit[]).map((u) => ({ value: u, label: UNIT_LABEL[u] }))

export function NewProductDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (product: Product) => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState("")
  const [unit, setUnit] = useState<ProductUnit>("dona")
  const [barcode, setBarcode] = useState("")
  const [minStock, setMinStock] = useState("0")

  const create = useMutation({
    mutationFn: productsApi.create,
    onSuccess: (product) => {
      toast.success(`"${product.name}" qo'shildi`)
      void queryClient.invalidateQueries({ queryKey: queryKeys.products.all })
      onCreated(product)
      onOpenChange(false)
      setName("")
      setBarcode("")
      setMinStock("0")
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    create.mutate({ name: name.trim(), unit, barcode: barcode.trim() || null, min_stock: Number(minStock) || 0 })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Yangi mahsulot</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="np-name">Nomi *</Label>
            <Input id="np-name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>Birlik</Label>
              <AppSelect value={unit} options={unitOptions} onChange={setUnit} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="np-min">Minimal qoldiq</Label>
              <Input id="np-min" type="number" min={0} step="any" value={minStock} onChange={(e) => setMinStock(e.target.value)} />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="np-barcode">Barcode</Label>
            <Input id="np-barcode" value={barcode} onChange={(e) => setBarcode(e.target.value)} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Bekor qilish
            </Button>
            <Button type="submit" disabled={create.isPending || !name.trim()}>
              Saqlash
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
