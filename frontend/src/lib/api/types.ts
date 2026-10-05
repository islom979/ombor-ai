// Backend (FastAPI / Pydantic) sxemalarining TypeScript ko'zgusi.

export type UUID = string

export type UserRole = "admin" | "manager" | "viewer"
export type CounterpartyKind = "supplier" | "client"
export type ProductUnit = "kg" | "dona" | "litr" | "metr" | "quti"
export type InvoiceType = "kirim" | "chiqim" | "utilizatsiya"
export type InvoiceStatus = "accepted" | "cancelled"
export type PaymentStatus = "unpaid" | "partial" | "paid"
export type PaymentMethod = "cash" | "card" | "transfer"
export type PaymentDirection = "incoming" | "outgoing"
export type AiCommandStatus = "pending" | "running" | "completed" | "failed"

export interface Page<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export interface Me {
  kind: "user" | "agent"
  role: UserRole
  user_id: UUID | null
  email: string | null
  full_name: string | null
}

export interface Profile {
  id: UUID
  email: string
  full_name: string | null
  role: UserRole
  created_at: string
}

export interface Product {
  id: UUID
  name: string
  unit: ProductUnit
  barcode: string | null
  min_stock: number
  default_sale_price: number
  is_active: boolean
  created_at: string
}

export interface ProductWithStock extends Product {
  stock: number
  batches_count: number
  last_purchase_price: number | null
}

export interface ProductCreate {
  name: string
  unit: ProductUnit
  barcode?: string | null
  min_stock?: number
  default_sale_price?: number
}

export interface StockRow {
  batch_id: UUID
  batch_code: string
  product_id: UUID
  product_name: string
  unit: ProductUnit
  barcode: string | null
  purchase_price: number
  sale_price: number
  quantity: number
  total_value: number
  is_low: boolean
  received_at: string
}

export interface StockSummary {
  total_products: number
  total_batches: number
  total_value: number
  low_stock_count: number
}

export interface Counterparty {
  id: UUID
  kind: CounterpartyKind
  name: string
  phone: string | null
  address: string | null
  note: string | null
  balance: number
  created_at: string
}

export interface CounterpartyInput {
  kind: CounterpartyKind
  name: string
  phone?: string | null
  address?: string | null
  note?: string | null
}

export interface CounterpartyBrief {
  id: UUID
  kind: CounterpartyKind
  name: string
}

export interface Invoice {
  id: UUID
  number: string
  type: InvoiceType
  status: InvoiceStatus
  payment_status: PaymentStatus
  counterparty: CounterpartyBrief | null
  subtotal: number
  discount_percent: number
  discount_amount: number
  total: number
  paid_amount: number
  note: string | null
  source: "web" | "ai"
  created_at: string
}

export interface InvoiceItem {
  id: UUID
  product_id: UUID
  product_name: string
  unit: ProductUnit
  batch_id: UUID
  batch_code: string
  quantity: number
  unit_price: number
  cost_price: number
  line_total: number
}

export interface InvoiceDetail extends Invoice {
  items: InvoiceItem[]
}

export interface InvoiceFilters {
  type?: InvoiceType
  counterparty_id?: UUID
  payment_status?: PaymentStatus
  date_from?: string
  date_to?: string
  search?: string
  page?: number
  size?: number
}

export interface KirimInput {
  supplier_id: UUID
  note?: string | null
  items: { product_id: UUID; quantity: number; purchase_price: number; sale_price: number }[]
}

export interface ChiqimInput {
  client_id: UUID
  note?: string | null
  discount_percent: number
  items: { product_id: UUID; batch_id?: UUID; quantity: number; unit_price?: number }[]
}

export interface PaymentAllocation {
  invoice_id: UUID
  invoice_number: string
  amount: number
}

export interface Payment {
  id: UUID
  counterparty_id: UUID
  cash_register_id: UUID
  cash_register_name: string
  direction: PaymentDirection
  method: PaymentMethod
  amount: number
  note: string | null
  created_by_name: string | null
  allocations: PaymentAllocation[]
  created_at: string
}

export interface PaymentInput {
  counterparty_id: UUID
  amount: number
  method: PaymentMethod
  cash_register_id?: UUID
  invoice_ids?: UUID[]
  note?: string | null
}

export interface CashRegister {
  id: UUID
  name: string
  balance: number
  is_active: boolean
}

export interface OperationStat {
  type: InvoiceType
  count: number
  total: number
}

export interface Statistics {
  date_from: string | null
  date_to: string | null
  suppliers_count: number
  clients_count: number
  products_count: number
  revenue: number
  cost_of_goods: number
  profit: number
  receivables: number
  payables: number
  cash_registers: CashRegister[]
  operations: OperationStat[]
}

export interface AiToolCall {
  name: string
  input: Record<string, unknown>
  output: unknown
  is_error: boolean
  duration_ms: number | null
}

export interface AiCommand {
  id: UUID
  user_id: UUID | null
  user_email: string | null
  prompt: string
  status: AiCommandStatus
  response: string | null
  error: string | null
  tool_calls: AiToolCall[]
  model: string | null
  input_tokens: number | null
  output_tokens: number | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}

export type AuditCategory = "auth" | "write" | "read" | "error"

export interface AuditLog {
  id: number
  created_at: string
  actor_kind: "user" | "agent" | "anonymous"
  user_id: UUID | null
  user_email: string | null
  user_role: UserRole | null
  action: string
  method: string
  path: string
  path_params: Record<string, string>
  query: string | null
  request_body: unknown
  status_code: number
  duration_ms: number
  ip: string | null
  user_agent: string | null
  country: string | null
  region: string | null
  city: string | null
  latitude: number | null
  longitude: number | null
  request_id: string | null
}

export interface AuditFilters {
  category?: AuditCategory
  ip?: string
  search?: string
  date_from?: string
  date_to?: string
  page?: number
  size?: number
}
