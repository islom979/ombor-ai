import type { Metadata } from "next"

import { StatisticsView } from "@/features/statistics/statistics-view"

export const metadata: Metadata = { title: "Hisobotlar" }

export default function StatisticsPage() {
  return <StatisticsView />
}
