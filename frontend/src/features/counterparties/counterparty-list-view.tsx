"use client"

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { DollarSignIcon, PencilIcon, PlusIcon, Trash2Icon, UsersIcon } from "lucide-react"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { toast } from "sonner"

import { AppSelect } from "@/components/common/app-select"
import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { EmptyState } from "@/components/common/empty-state"
import { PageHeader } from "@/components/common/page-header"
import { PaginationBar } from "@/components/common/pagination-bar"
import { SearchInput } from "@/components/common/search-input"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAuth } from "@/features/auth/auth-provider"
import { CounterpartyFormDialog } from "@/features/counterparties/counterparty-form-dialog"
import { PaymentDialog } from "@/features/counterparties/payment-dialog"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { counterpartiesApi } from "@/lib/api/endpoints"
import type { Counterparty, CounterpartyKind } from "@/lib/api/types"
import { formatMoney, KIND_LABEL } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

const sizeOptions = ["10", "20", "50", "100"].map((s) => ({ value: s, label: `${s} ta` }))

export const DETAIL_PATH: Record<CounterpartyKind, string> = {
  supplier: "/ombor/taminotchilar",
  client: "/ombor/klientlar",
}

export function BalanceText({ value, className }: { value: number; className?: string }) {
  return (
    <span className={cn("font-semibold tabular-nums", value > 0 ? "text-success" : value < 0 ? "text-destructive" : "", className)}>
      {formatMoney(value)}
    </span>
  )
}

export function CounterpartyListView({ kind }: { kind: CounterpartyKind }) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { canWrite } = useAuth()
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [size, setSize] = useState("20")
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Counterparty | null>(null)
  const [paying, setPaying] = useState<Counterparty | null>(null)
  const [deleting, setDeleting] = useState<Counterparty | null>(null)
  const debounced = useDebouncedValue(search.trim())

  const list = useQuery({
    queryKey: queryKeys.counterparties.list(kind, debounced, page, Number(size)),
    queryFn: ({ signal }) => counterpartiesApi.list({ kind, search: debounced || undefined, page, size: Number(size) }, signal),
    placeholderData: keepPreviousData,
  })

  const remove = useMutation({
    mutationFn: (id: string) => counterpartiesApi.remove(id),
    onSuccess: () => {
      toast.success("O'chirildi")
      void queryClient.invalidateQueries({ queryKey: queryKeys.counterparties.all })
      setDeleting(null)
    },
  })

  const labels = KIND_LABEL[kind]
  const offset = (page - 1) * Number(size)

  return (
    <>
      <PageHeader
        title={labels.many}
        subtitle={`Jami: ${list.data?.total ?? 0} ta ${labels.one.toLowerCase()}`}
        actions={
          canWrite && (
            <Button
              size="lg"
              onClick={() => {
                setEditing(null)
                setFormOpen(true)
              }}
            >
              <PlusIcon /> Yangi {labels.one.toLowerCase()}
            </Button>
          )
        }
      />

      <div className="mb-4 flex gap-3">
        <SearchInput
          className="flex-1"
          placeholder={`${labels.one} qidirish...`}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
        />
        <AppSelect
          className="w-28"
          value={size}
          options={sizeOptions}
          onChange={(value) => {
            setSize(value)
            setPage(1)
          }}
        />
      </div>

      <Card className="px-2 py-2">
        <Table>
          <TableHeader>
            <TableRow className="text-xs uppercase">
              <TableHead className="w-12">№</TableHead>
              <TableHead>Nomi</TableHead>
              <TableHead>Telefon</TableHead>
              <TableHead>Manzil</TableHead>
              <TableHead>Balans</TableHead>
              <TableHead className="text-right">Amallar</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.isPending &&
              Array.from({ length: 6 }, (_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6}>
                    <Skeleton className="h-5" />
                  </TableCell>
                </TableRow>
              ))}
            {list.data?.items.map((item, index) => (
              <TableRow key={item.id} className="cursor-pointer" onClick={() => router.push(`${DETAIL_PATH[kind]}/${item.id}`)}>
                <TableCell>{offset + index + 1}</TableCell>
                <TableCell className="font-medium">{item.name}</TableCell>
                <TableCell className="whitespace-nowrap">{item.phone ?? "—"}</TableCell>
                <TableCell>{item.address ?? "—"}</TableCell>
                <TableCell>
                  <BalanceText value={item.balance} />
                </TableCell>
                <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                  {canWrite && (
                    <div className="flex justify-end gap-0.5">
                      <Button variant="ghost" size="icon-sm" aria-label="To'lov" onClick={() => setPaying(item)}>
                        <DollarSignIcon className="text-success" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label="Tahrirlash"
                        onClick={() => {
                          setEditing(item)
                          setFormOpen(true)
                        }}
                      >
                        <PencilIcon className="text-primary" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" aria-label="O'chirish" onClick={() => setDeleting(item)}>
                        <Trash2Icon className="text-destructive" />
                      </Button>
                    </div>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {list.isSuccess && list.data.items.length === 0 && <EmptyState icon={UsersIcon} title={`${labels.many} topilmadi`} />}
        {list.data && list.data.total > 0 && (
          <PaginationBar page={list.data.page} pages={list.data.pages} total={list.data.total} onChange={setPage} />
        )}
      </Card>

      <CounterpartyFormDialog kind={kind} open={formOpen} onOpenChange={setFormOpen} counterparty={editing} />
      <PaymentDialog counterparty={paying} open={Boolean(paying)} onOpenChange={(open) => !open && setPaying(null)} />
      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title={`${labels.one}ni o'chirish`}
        description={`"${deleting?.name}" o'chiriladi. Balansi nol bo'lmasa, o'chirib bo'lmaydi.`}
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting.id)}
      />
    </>
  )
}
