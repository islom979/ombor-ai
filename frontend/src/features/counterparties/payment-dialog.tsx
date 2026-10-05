"use client"

import { useMutation, useQuery } from "@tanstack/react-query"
import { useState, type FormEvent } from "react"
import { toast } from "sonner"

import { AppSelect } from "@/components/common/app-select"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useInvalidateWarehouse } from "@/features/invoices/use-invalidate-warehouse"
import { paymentsApi } from "@/lib/api/endpoints"
import type { Counterparty, PaymentMethod, UUID } from "@/lib/api/types"
import { formatMoney, PAYMENT_METHOD_LABEL } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"

const methodOptions = (Object.keys(PAYMENT_METHOD_LABEL) as PaymentMethod[]).map((m) => ({
  value: m,
  label: PAYMENT_METHOD_LABEL[m],
}))

interface Props {
  counterparty: Counterparty | null
  open: boolean
  onOpenChange: (open: boolean) => void
  /** "Invoicelar uchun to'lov" rejimida tanlangan invoicelar va ularning qoldiq summasi. */
  invoiceIds?: UUID[]
  suggestedAmount?: number
  onPaid?: () => void
}

export function PaymentDialog(props: Props) {
  const { counterparty, open, onOpenChange } = props
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {/* Forma har ochilganda yangidan o'rnatiladi — boshlang'ich qiymatlar props'dan olinadi. */}
        {open && counterparty && <PaymentForm {...props} counterparty={counterparty} />}
      </DialogContent>
    </Dialog>
  )
}

function PaymentForm({
  counterparty,
  onOpenChange,
  invoiceIds,
  suggestedAmount,
  onPaid,
}: Props & { counterparty: Counterparty }) {
  const invalidate = useInvalidateWarehouse()
  const debt = Math.abs(counterparty.balance)
  const [amount, setAmount] = useState(String(suggestedAmount ?? (debt > 0 ? debt : "")))
  const [method, setMethod] = useState<PaymentMethod>("cash")
  const [chosenRegisterId, setRegisterId] = useState<UUID | null>(null)
  const [note, setNote] = useState("")

  const registers = useQuery({ queryKey: queryKeys.payments.registers, queryFn: paymentsApi.registers })
  const registerId = chosenRegisterId ?? registers.data?.[0]?.id ?? null

  const pay = useMutation({
    mutationFn: paymentsApi.create,
    onSuccess: (payment) => {
      const closed = payment.allocations.length
      toast.success(
        `To'lov qabul qilindi: ${formatMoney(payment.amount)}${closed ? ` · ${closed} ta invoicega taqsimlandi` : ""}`,
      )
      invalidate()
      onPaid?.()
      onOpenChange(false)
    },
  })

  const isSupplier = counterparty.kind === "supplier"

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const value = Number(amount)
    if (!(value > 0)) return toast.error("Summani to'g'ri kiriting")
    pay.mutate({
      counterparty_id: counterparty.id,
      amount: value,
      method,
      cash_register_id: registerId ?? undefined,
      invoice_ids: invoiceIds?.length ? invoiceIds : undefined,
      note: note.trim() || null,
    })
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>To&apos;lov qilish</DialogTitle>
        <DialogDescription>
          {counterparty.name} ·{" "}
          {isSupplier ? "Ta'minotchiga to'lov (kassadan chiqim)" : "Klientdan to'lov (kassaga kirim)"}
          {invoiceIds?.length ? ` · ${invoiceIds.length} ta invoice uchun` : ""}
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="grid gap-3">
        <div className="grid gap-1.5">
          <Label htmlFor="pay-amount">Summa (so&apos;m) *</Label>
          <Input
            id="pay-amount"
            type="number"
            min={0}
            step="any"
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">Joriy balans: {formatMoney(counterparty.balance)}</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="grid gap-1.5">
            <Label>To&apos;lov usuli</Label>
            <AppSelect value={method} options={methodOptions} onChange={setMethod} />
          </div>
          <div className="grid gap-1.5">
            <Label>Kassa</Label>
            <AppSelect
              value={registerId}
              options={(registers.data ?? []).map((r) => ({ value: r.id, label: r.name }))}
              onChange={setRegisterId}
              placeholder="Kassa..."
            />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="pay-note">Izoh</Label>
          <Textarea id="pay-note" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Bekor qilish
          </Button>
          <Button type="submit" className="bg-success text-white hover:bg-success/90" disabled={pay.isPending}>
            To&apos;lovni saqlash
          </Button>
        </DialogFooter>
      </form>
    </>
  )
}
