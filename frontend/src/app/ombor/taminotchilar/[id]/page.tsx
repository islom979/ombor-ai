import type { Metadata } from "next"

import { CounterpartyDetailView } from "@/features/counterparties/counterparty-detail-view"

export const metadata: Metadata = { title: "Ta'minotchi" }

export default async function SupplierDetailPage({ params }: PageProps<"/ombor/taminotchilar/[id]">) {
  const { id } = await params
  return <CounterpartyDetailView id={id} />
}
