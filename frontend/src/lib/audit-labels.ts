import type { AuditLog } from "@/lib/api/types"

/** Backend endpoint nomi → foydalanuvchiga tushunarli amal nomi. */
export const ACTION_LABEL: Record<string, string> = {
  "auth.login": "Tizimga kirdi",
  "auth.logout": "Tizimdan chiqdi",
  me: "Profilini ochdi",
  list_stock: "Ombor qoldig'ini ko'rdi",
  stock_summary: "Ombor ko'rsatkichlarini ko'rdi",
  available_batches: "Partiyalarni qidirdi",
  export_stock: "Qoldiqni yuklab oldi (CSV)",
  list_products: "Mahsulotlarni ko'rdi",
  get_product: "Mahsulotni ochdi",
  create_product: "Mahsulot qo'shdi",
  update_product: "Mahsulotni tahrirladi",
  delete_product: "Mahsulotni o'chirdi",
  list_counterparties: "Kontragentlarni ko'rdi",
  get_counterparty: "Kontragentni ochdi",
  create_counterparty: "Kontragent qo'shdi",
  update_counterparty: "Kontragentni tahrirladi",
  delete_counterparty: "Kontragentni o'chirdi",
  list_invoices: "Operatsiyalarni ko'rdi",
  get_invoice: "Invoiceni ochdi",
  create_kirim: "Kirim qildi",
  create_chiqim: "Chiqim qildi",
  create_utilizatsiya: "Hisobdan chiqardi",
  list_payments: "To'lovlarni ko'rdi",
  create_payment: "To'lov qildi",
  list_registers: "Kassalarni ko'rdi",
  create_register: "Kassa qo'shdi",
  get_statistics: "Hisobotni ko'rdi",
  create_command: "AI'ga buyruq berdi",
  list_commands: "AI buyruqlarini ko'rdi",
  get_command: "AI buyrug'ini ochdi",
  claim_command: "AI buyruqni oldi",
  update_command: "AI natijani yozdi",
  list_users: "Foydalanuvchilarni ko'rdi",
  update_role: "Rolni o'zgartirdi",
  list_audit_logs: "Loglarni ko'rdi",
  unmatched_route: "Noma'lum manzil",
}

export function actionLabel(action: string): string {
  return ACTION_LABEL[action] ?? action
}

export type ActionKind = "auth" | "write" | "read"

export function actionKind(log: Pick<AuditLog, "action" | "method">): ActionKind {
  if (log.action.startsWith("auth.")) return "auth"
  return log.method === "GET" ? "read" : "write"
}

export function actorName(log: Pick<AuditLog, "actor_kind" | "user_email">): string {
  if (log.actor_kind === "agent") return "AI agent"
  if (log.actor_kind === "anonymous") return "Noma'lum (kirmagan)"
  return log.user_email ?? "—"
}

/** "UZ" → 🇺🇿 (mintaqaviy indikator belgilari orqali). */
export function countryFlag(code: string | null): string {
  if (!code || !/^[A-Za-z]{2}$/.test(code)) return ""
  return String.fromCodePoint(...[...code.toUpperCase()].map((c) => 0x1f1e6 + c.charCodeAt(0) - 65))
}

export function location(log: Pick<AuditLog, "city" | "region" | "country">): string {
  const parts = [log.city, log.region, log.country].filter(Boolean)
  return parts.length ? parts.join(", ") : "—"
}

/** Qisqa qurilma tavsifi: "Chrome · Windows". */
export function deviceLabel(userAgent: string | null): string {
  if (!userAgent) return "—"
  const browser =
    /Edg\//.test(userAgent) ? "Edge"
    : /OPR\/|Opera/.test(userAgent) ? "Opera"
    : /YaBrowser/.test(userAgent) ? "Yandex"
    : /Firefox\//.test(userAgent) ? "Firefox"
    : /Chrome\//.test(userAgent) ? "Chrome"
    : /Safari\//.test(userAgent) ? "Safari"
    : /python-httpx|curl/i.test(userAgent) ? "API klient"
    : "Boshqa"
  const os =
    /Windows/.test(userAgent) ? "Windows"
    : /Android/.test(userAgent) ? "Android"
    : /iPhone|iPad|iOS/.test(userAgent) ? "iOS"
    : /Mac OS X|Macintosh/.test(userAgent) ? "macOS"
    : /Linux/.test(userAgent) ? "Linux"
    : ""
  return os ? `${browser} · ${os}` : browser
}
