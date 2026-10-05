"use client"

import { useQuery } from "@tanstack/react-query"

import { AppSelect } from "@/components/common/app-select"
import { counterpartiesApi } from "@/lib/api/endpoints"
import type { CounterpartyKind, UUID } from "@/lib/api/types"
import { queryKeys } from "@/lib/query-keys"

export function CounterpartySelect({
  kind,
  value,
  onChange,
  id,
}: {
  kind: CounterpartyKind
  value: UUID | null
  onChange: (id: UUID) => void
  id?: string
}) {
  const { data, isPending } = useQuery({
    queryKey: queryKeys.counterparties.allOfKind(kind),
    queryFn: () => counterpartiesApi.list({ kind, size: 200 }),
  })
  const options = (data?.items ?? []).map((c) => ({ value: c.id, label: c.name }))
  return (
    <AppSelect
      id={id}
      value={value}
      onChange={onChange}
      options={options}
      placeholder={isPending ? "Yuklanmoqda..." : "Tanlang..."}
    />
  )
}
