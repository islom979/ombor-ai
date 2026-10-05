import type { Metadata } from "next"

import { RolesView } from "@/features/users/roles-view"

export const metadata: Metadata = { title: "Rollar" }

export default function RolePage() {
  return <RolesView />
}
