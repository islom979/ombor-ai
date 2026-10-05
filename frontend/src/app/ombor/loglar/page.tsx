import type { Metadata } from "next"

import { AuditView } from "@/features/audit/audit-view"

export const metadata: Metadata = { title: "Loglar" }

export default function AuditPage() {
  return <AuditView />
}
