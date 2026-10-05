import type { Metadata } from "next"

import { AiConsole } from "@/features/ai/ai-console"

export const metadata: Metadata = { title: "AI yordamchi" }

export default function AiPage() {
  return <AiConsole />
}
