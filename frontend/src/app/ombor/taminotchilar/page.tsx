import type { Metadata } from "next"

import { CounterpartyListView } from "@/features/counterparties/counterparty-list-view"

export const metadata: Metadata = { title: "Ta'minotchilar" }

export default function SuppliersPage() {
  return <CounterpartyListView kind="supplier" />
}
