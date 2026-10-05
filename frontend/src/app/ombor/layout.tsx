import { AppShell } from "@/components/layout/app-shell"

export default function OmborLayout({ children }: LayoutProps<"/ombor">) {
  return <AppShell>{children}</AppShell>
}
