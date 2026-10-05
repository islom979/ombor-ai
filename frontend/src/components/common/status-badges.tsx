import { cn } from "@/lib/utils"
import type { InvoiceType, PaymentStatus } from "@/lib/api/types"
import { INVOICE_TYPE_LABEL, PAYMENT_STATUS_LABEL } from "@/lib/format"

const pill = "inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase"

const paymentClass: Record<PaymentStatus, string> = {
  unpaid: "bg-destructive/10 text-destructive",
  partial: "bg-warning/15 text-amber-700 dark:text-warning",
  paid: "bg-success/15 text-success",
}

const typeClass: Record<InvoiceType, string> = {
  kirim: "bg-success/15 text-success",
  chiqim: "bg-primary/10 text-primary",
  utilizatsiya: "bg-warning/15 text-amber-700 dark:text-warning",
}

export function PaymentStatusBadge({ status }: { status: PaymentStatus }) {
  return <span className={cn(pill, paymentClass[status])}>{PAYMENT_STATUS_LABEL[status]}</span>
}

export function InvoiceTypeBadge({ type }: { type: InvoiceType }) {
  return <span className={cn(pill, typeClass[type])}>{INVOICE_TYPE_LABEL[type]}</span>
}

export function AcceptedBadge() {
  return <span className={cn(pill, "bg-success/15 text-success")}>Qabul qilindi</span>
}

export function BatchCode({ code, tone = "neutral" }: { code: string; tone?: "neutral" | "low" }) {
  return (
    <span
      className={cn(
        "rounded px-1.5 py-0.5 font-mono text-xs font-medium",
        tone === "low" ? "bg-destructive/10 text-destructive" : "bg-warning/20 text-amber-800 dark:text-warning",
      )}
    >
      {code}
    </span>
  )
}

export function LowStockBadge() {
  return <span className={cn(pill, "bg-destructive/10 text-destructive")}>Kam qolgan</span>
}
