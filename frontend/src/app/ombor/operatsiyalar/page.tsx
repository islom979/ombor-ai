import type { Metadata } from "next"

import { OperationsView } from "@/features/invoices/operations-view"

export const metadata: Metadata = { title: "Operatsiyalar" }

export default function OperationsPage() {
  return <OperationsView />
}
