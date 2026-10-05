import type { Metadata } from "next"

import { StockView } from "@/features/stock/stock-view"

export const metadata: Metadata = { title: "Ombor" }

export default function StockPage() {
  return <StockView />
}
