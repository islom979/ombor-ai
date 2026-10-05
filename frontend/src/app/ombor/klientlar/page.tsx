import type { Metadata } from "next"

import { CounterpartyListView } from "@/features/counterparties/counterparty-list-view"

export const metadata: Metadata = { title: "Klientlar" }

export default function ClientsPage() {
  return <CounterpartyListView kind="client" />
}
