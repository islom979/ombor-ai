import type { Metadata } from "next"

import { ChiqimForm } from "@/features/invoices/chiqim-form"

export const metadata: Metadata = { title: "Chiqim" }

export default function ChiqimPage() {
  return <ChiqimForm />
}
