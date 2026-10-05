"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, type FormEvent } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { counterpartiesApi } from "@/lib/api/endpoints"
import type { Counterparty, CounterpartyKind } from "@/lib/api/types"
import { KIND_LABEL } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"

interface Props {
  kind: CounterpartyKind
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Berilsa — tahrirlash rejimi. */
  counterparty?: Counterparty | null
}

export function CounterpartyFormDialog(props: Props) {
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      {/* Forma har ochilganda yangidan o'rnatiladi — boshlang'ich qiymatlar props'dan olinadi. */}
      <DialogContent>{props.open && <CounterpartyForm {...props} />}</DialogContent>
    </Dialog>
  )
}

function CounterpartyForm({ kind, onOpenChange, counterparty }: Props) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    name: counterparty?.name ?? "",
    phone: counterparty?.phone ?? "",
    address: counterparty?.address ?? "",
    note: counterparty?.note ?? "",
  })

  const save = useMutation({
    mutationFn: () => {
      const payload = {
        name: form.name.trim(),
        phone: form.phone.trim() || null,
        address: form.address.trim() || null,
        note: form.note.trim() || null,
      }
      return counterparty
        ? counterpartiesApi.update(counterparty.id, payload)
        : counterpartiesApi.create({ kind, ...payload })
    },
    onSuccess: (saved) => {
      toast.success(counterparty ? "O'zgarishlar saqlandi" : `"${saved.name}" qo'shildi`)
      void queryClient.invalidateQueries({ queryKey: queryKeys.counterparties.all })
      onOpenChange(false)
    },
  })

  const set = (field: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }

  const label = KIND_LABEL[kind].one
  return (
    <>
      <DialogHeader>
        <DialogTitle>{counterparty ? `${label}ni tahrirlash` : `Yangi ${label.toLowerCase()}`}</DialogTitle>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="grid gap-3">
        <div className="grid gap-1.5">
          <Label htmlFor="cp-name">Nomi *</Label>
          <Input id="cp-name" required value={form.name} onChange={set("name")} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="cp-phone">Telefon</Label>
          <Input id="cp-phone" type="tel" placeholder="+998 90 123 45 67" value={form.phone} onChange={set("phone")} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="cp-address">Manzil</Label>
          <Input id="cp-address" value={form.address} onChange={set("address")} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="cp-note">Izoh</Label>
          <Textarea id="cp-note" value={form.note} onChange={set("note")} />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Bekor qilish
          </Button>
          <Button type="submit" disabled={save.isPending || !form.name.trim()}>
            Saqlash
          </Button>
        </DialogFooter>
      </form>
    </>
  )
}
