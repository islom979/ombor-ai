import type { Metadata } from "next"

import { KirimForm } from "@/features/invoices/kirim-form"

export const metadata: Metadata = { title: "Kirim" }

export default function KirimPage() {
  return <KirimForm />
}
