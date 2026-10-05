import { api } from "@/lib/api/client"
import type {
  AiCommand,
  CashRegister,
  ChiqimInput,
  Counterparty,
  CounterpartyInput,
  CounterpartyKind,
  Invoice,
  InvoiceDetail,
  InvoiceFilters,
  KirimInput,
  Me,
  Page,
  Payment,
  PaymentInput,
  Product,
  ProductCreate,
  ProductWithStock,
  Profile,
  Statistics,
  StockRow,
  StockSummary,
  UserRole,
  UUID,
} from "@/lib/api/types"

export const stockApi = {
  list: (params: { search?: string; low_only?: boolean }, signal?: AbortSignal) =>
    api.get<StockRow[]>("/stock", params, signal),
  summary: () => api.get<StockSummary>("/stock/summary"),
  available: (search: string, signal?: AbortSignal) =>
    api.get<StockRow[]>("/stock/available", { search, limit: 30 }, signal),
  exportCsv: () => api.download("/stock/export", "ombor-qoldiq.csv"),
}

export const productsApi = {
  list: (params: { search?: string; page?: number; size?: number }, signal?: AbortSignal) =>
    api.get<Page<ProductWithStock>>("/products", params, signal),
  create: (data: ProductCreate) => api.post<Product>("/products", data),
}

export const counterpartiesApi = {
  list: (params: { kind: CounterpartyKind; search?: string; page?: number; size?: number }, signal?: AbortSignal) =>
    api.get<Page<Counterparty>>("/counterparties", params, signal),
  get: (id: UUID) => api.get<Counterparty>(`/counterparties/${id}`),
  create: (data: CounterpartyInput) => api.post<Counterparty>("/counterparties", data),
  update: (id: UUID, data: Partial<CounterpartyInput>) => api.patch<Counterparty>(`/counterparties/${id}`, data),
  remove: (id: UUID) => api.delete(`/counterparties/${id}`),
}

export const invoicesApi = {
  list: (filters: InvoiceFilters, signal?: AbortSignal) =>
    api.get<Page<Invoice>>("/invoices", { ...filters }, signal),
  get: (id: UUID) => api.get<InvoiceDetail>(`/invoices/${id}`),
  createKirim: (data: KirimInput) => api.post<InvoiceDetail>("/invoices/kirim", data),
  createChiqim: (data: ChiqimInput) => api.post<InvoiceDetail>("/invoices/chiqim", data),
}

export const paymentsApi = {
  list: (params: { counterparty_id?: UUID; page?: number; size?: number }) =>
    api.get<Page<Payment>>("/payments", params),
  create: (data: PaymentInput) => api.post<Payment>("/payments", data),
  registers: () => api.get<CashRegister[]>("/cash-registers"),
}

export const statisticsApi = {
  get: (params: { date_from?: string; date_to?: string }) => api.get<Statistics>("/statistics", params),
}

export const aiApi = {
  list: (params: { page?: number; size?: number }) => api.get<Page<AiCommand>>("/ai/commands", params),
  create: (prompt: string) => api.post<AiCommand>("/ai/commands", { prompt }),
}

export const usersApi = {
  me: () => api.get<Me>("/users/me"),
  list: () => api.get<Profile[]>("/users"),
  updateRole: (id: UUID, role: UserRole) => api.patch<Profile>(`/users/${id}/role`, { role }),
}
