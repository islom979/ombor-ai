import type { Metadata } from "next"

import { CounterpartyDetailView } from "@/features/counterparties/counterparty-detail-view"

export const metadata: Metadata = { title: "Klient" }

export default async function ClientDetailPage({ params }: PageProps<"/ombor/klientlar/[id]">) {
  const { id } = await params
  return <CounterpartyDetailView id={id} />
}
