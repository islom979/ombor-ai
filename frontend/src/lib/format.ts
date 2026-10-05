import type {
  CounterpartyKind,
  InvoiceType,
  PaymentMethod,
  PaymentStatus,
  ProductUnit,
  UserRole,
} from "@/lib/api/types"

const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 })
const quantityFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 })

/** 1500000 → "1,500,000" (videodagi kabi vergul bilan). */
export const formatNumber = (value: number) => numberFormat.format(value)
export const formatMoney = (value: number) => `${numberFormat.format(value)} so'm`
export const formatQuantity = (value: number) => quantityFormat.format(value)

export function formatDateTime(iso: string): string {
  const date = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** Mahalliy sana YYYY-MM-DD formatida (input[type=date] va API uchun). */
export function toIsoDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
}

export const UNIT_LABEL: Record<ProductUnit, string> = {
  kg: "kg",
  dona: "dona",
  litr: "litr",
  metr: "metr",
  quti: "quti",
}

export const INVOICE_TYPE_LABEL: Record<InvoiceType, string> = {
  kirim: "Kirim",
  chiqim: "Chiqim",
  utilizatsiya: "Utilizatsiya",
}

export const PAYMENT_STATUS_LABEL: Record<PaymentStatus, string> = {
  unpaid: "To'lanmagan",
  partial: "Qisman to'langan",
  paid: "To'langan",
}

export const PAYMENT_METHOD_LABEL: Record<PaymentMethod, string> = {
  cash: "Naqd",
  card: "Karta",
  transfer: "O'tkazma",
}

export const ROLE_LABEL: Record<UserRole, string> = {
  admin: "Admin",
  manager: "Menejer",
  viewer: "Kuzatuvchi",
}

export const KIND_LABEL: Record<CounterpartyKind, { one: string; many: string }> = {
  supplier: { one: "Ta'minotchi", many: "Ta'minotchilar" },
  client: { one: "Klient", many: "Klientlar" },
}
