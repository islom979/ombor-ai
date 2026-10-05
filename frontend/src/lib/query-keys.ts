import type { CounterpartyKind, InvoiceFilters, UUID } from "@/lib/api/types"

/** TanStack Query kalitlari — invalidatsiya uchun yagona joy. */
export const queryKeys = {
  me: ["me"] as const,
  users: ["users"] as const,
  stock: {
    all: ["stock"] as const,
    list: (search: string, lowOnly: boolean) => ["stock", "list", search, lowOnly] as const,
    summary: ["stock", "summary"] as const,
    available: (search: string) => ["stock", "available", search] as const,
  },
  products: {
    all: ["products"] as const,
    list: (search: string, page: number) => ["products", "list", search, page] as const,
  },
  counterparties: {
    all: ["counterparties"] as const,
    list: (kind: CounterpartyKind, search: string, page: number, size: number) =>
      ["counterparties", kind, search, page, size] as const,
    allOfKind: (kind: CounterpartyKind) => ["counterparties", kind, "all"] as const,
    detail: (id: UUID) => ["counterparties", "detail", id] as const,
  },
  invoices: {
    all: ["invoices"] as const,
    list: (filters: InvoiceFilters) => ["invoices", "list", filters] as const,
    detail: (id: UUID) => ["invoices", "detail", id] as const,
  },
  payments: {
    all: ["payments"] as const,
    list: (counterpartyId: UUID, page: number) => ["payments", counterpartyId, page] as const,
    registers: ["cash-registers"] as const,
  },
  statistics: (from: string, to: string) => ["statistics", from, to] as const,
  ai: { all: ["ai-commands"] as const },
}
