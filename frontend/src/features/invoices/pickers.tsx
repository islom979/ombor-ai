"use client"

import { useQuery } from "@tanstack/react-query"
import { PlusIcon } from "lucide-react"
import { useState, type ReactNode } from "react"

import { SearchInput } from "@/components/common/search-input"
import { BatchCode } from "@/components/common/status-badges"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { productsApi, stockApi } from "@/lib/api/endpoints"
import type { ProductWithStock, StockRow } from "@/lib/api/types"
import { formatMoney, formatNumber, formatQuantity, UNIT_LABEL } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"

export const MIN_SEARCH_CHARS = 3

// ---------------------------------------------------------------- umumiy qism
function ResultRow({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between gap-3 border-b px-3 py-2.5 text-left last:border-b-0 hover:bg-muted"
    >
      {children}
    </button>
  )
}

function SearchHint({ term }: { term: string }) {
  const missing = MIN_SEARCH_CHARS - term.length
  return missing > 0 && term.length > 0 ? (
    <p className="mt-1 text-xs text-muted-foreground">Yana {missing} ta belgi kiriting</p>
  ) : null
}

function ProductResult({ product, onPick }: { product: ProductWithStock; onPick: () => void }) {
  return (
    <ResultRow onClick={onPick}>
      <div>
        <p className="font-medium">{product.name}</p>
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {UNIT_LABEL[product.unit]}
          {product.stock > 0 && (
            <span className="rounded bg-success/15 px-1 text-[10px] font-semibold text-success uppercase">Omborda bor</span>
          )}
        </p>
      </div>
      {product.last_purchase_price !== null && (
        <div className="text-right">
          <p className="text-sm font-medium tabular-nums">{formatMoney(product.last_purchase_price)}</p>
          <p className="text-[11px] text-muted-foreground">Oldingi narx</p>
        </div>
      )}
    </ResultRow>
  )
}

function BatchResult({ batch, onPick }: { batch: StockRow; onPick: () => void }) {
  return (
    <ResultRow onClick={onPick}>
      <div>
        <p className="font-medium">{batch.product_name}</p>
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <BatchCode code={batch.batch_code} />
          Omborda: {formatQuantity(batch.quantity)} {UNIT_LABEL[batch.unit]}
        </p>
      </div>
      <div className="text-right">
        <p className="text-sm font-medium tabular-nums">{formatMoney(batch.sale_price)}</p>
        <p className="text-[11px] text-muted-foreground">Sotuv narxi</p>
      </div>
    </ResultRow>
  )
}

// ---------------------------------------------------------- inline qidiruvlar
export function ProductSearch({ onPick }: { onPick: (product: ProductWithStock) => void }) {
  const [term, setTerm] = useState("")
  const debounced = useDebouncedValue(term.trim())
  const enabled = debounced.length >= MIN_SEARCH_CHARS
  const { data, isFetching } = useQuery({
    queryKey: queryKeys.products.list(debounced, 1),
    queryFn: ({ signal }) => productsApi.list({ search: debounced, size: 10 }, signal),
    enabled,
  })

  return (
    <div>
      <SearchInput
        placeholder={`Mahsulot nomini kiriting (kamida ${MIN_SEARCH_CHARS} ta belgi)...`}
        value={term}
        onChange={(e) => setTerm(e.target.value)}
      />
      <SearchHint term={term.trim()} />
      {enabled && (
        <div className="mt-2 overflow-hidden rounded-lg border bg-card">
          {isFetching && !data && <Skeleton className="m-2 h-10" />}
          {data?.items.length === 0 && <p className="p-3 text-sm text-muted-foreground">&quot;{debounced}&quot; bo&apos;yicha natija topilmadi</p>}
          {data?.items.map((product) => (
            <ProductResult
              key={product.id}
              product={product}
              onPick={() => {
                onPick(product)
                setTerm("")
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function BatchSearch({ onPick }: { onPick: (batch: StockRow) => void }) {
  const [term, setTerm] = useState("")
  const debounced = useDebouncedValue(term.trim())
  const enabled = debounced.length >= MIN_SEARCH_CHARS
  const { data, isFetching } = useQuery({
    queryKey: queryKeys.stock.available(debounced),
    queryFn: ({ signal }) => stockApi.available(debounced, signal),
    enabled,
  })

  return (
    <div>
      <SearchInput
        placeholder={`Mahsulot nomini kiriting (kamida ${MIN_SEARCH_CHARS} ta belgi)...`}
        value={term}
        onChange={(e) => setTerm(e.target.value)}
      />
      <SearchHint term={term.trim()} />
      {enabled && (
        <div className="mt-2 overflow-hidden rounded-lg border bg-card">
          {isFetching && !data && <Skeleton className="m-2 h-10" />}
          {data?.length === 0 && (
            <p className="rounded-lg bg-primary/10 p-3 text-sm text-primary">&quot;{debounced}&quot; bo&apos;yicha natija topilmadi</p>
          )}
          {data?.map((batch) => (
            <BatchResult
              key={batch.batch_id}
              batch={batch}
              onPick={() => {
                onPick(batch)
                setTerm("")
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ------------------------------------------------- "+ Mahsulotlar" panellari
interface SheetProps<T> {
  open: boolean
  onOpenChange: (open: boolean) => void
  onPick: (item: T) => void
}

export function ProductCatalogSheet({
  open,
  onOpenChange,
  onPick,
  onCreateNew,
}: SheetProps<ProductWithStock> & { onCreateNew: () => void }) {
  const [term, setTerm] = useState("")
  const debounced = useDebouncedValue(term.trim())
  const { data, isPending } = useQuery({
    queryKey: queryKeys.products.list(`catalog:${debounced}`, 1),
    queryFn: ({ signal }) => productsApi.list({ search: debounced || undefined, size: 100 }, signal),
    enabled: open,
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Barcha mahsulotlar</SheetTitle>
          <p className="text-xs text-muted-foreground">Jami: {data?.total ?? 0} ta mahsulot</p>
        </SheetHeader>
        <div className="flex gap-2 px-4">
          <SearchInput className="flex-1" placeholder="Qidirish..." value={term} onChange={(e) => setTerm(e.target.value)} />
          <Button variant="outline" onClick={onCreateNew}>
            <PlusIcon /> Yangi
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto border-t">
          {isPending && <Skeleton className="m-3 h-10" />}
          {data?.items.map((product) => (
            <ProductResult key={product.id} product={product} onPick={() => onPick(product)} />
          ))}
        </div>
      </SheetContent>
    </Sheet>
  )
}

export function BatchCatalogSheet({ open, onOpenChange, onPick }: SheetProps<StockRow>) {
  const { data, isPending } = useQuery({
    queryKey: queryKeys.stock.list("", false),
    queryFn: ({ signal }) => stockApi.list({}, signal),
    enabled: open,
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Barcha mahsulotlar</SheetTitle>
          <p className="text-xs text-muted-foreground">Jami: {data?.length ?? 0} ta partiya</p>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto border-t">
          {isPending && <Skeleton className="m-3 h-10" />}
          {data?.map((batch) => (
            <BatchResult key={batch.batch_id} batch={batch} onPick={() => onPick(batch)} />
          ))}
        </div>
      </SheetContent>
    </Sheet>
  )
}

export function TotalsCards({ count, total }: { count: number; total: number }) {
  return (
    <div className="grid max-w-xl grid-cols-2 gap-3">
      <div className="rounded-xl border bg-card p-4">
        <p className="text-xs text-muted-foreground">Jami mahsulotlar</p>
        <p className="text-2xl font-bold">{count} ta</p>
      </div>
      <div className="rounded-xl border bg-card p-4">
        <p className="text-xs text-muted-foreground">Umumiy summa</p>
        <p className="text-2xl font-bold text-primary tabular-nums">{formatNumber(total)} so&apos;m</p>
      </div>
    </div>
  )
}
