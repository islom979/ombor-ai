"use client"

import {
  BotIcon,
  ChartLineIcon,
  ChevronLeftIcon,
  FileClockIcon,
  LogOutIcon,
  MoonIcon,
  MoveIcon,
  PackageIcon,
  PackageMinusIcon,
  PackagePlusIcon,
  ShieldCheckIcon,
  SunIcon,
  TruckIcon,
  UserCogIcon,
  UsersIcon,
  type LucideIcon,
} from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"
import { useAuth } from "@/features/auth/auth-provider"
import { ROLE_LABEL } from "@/lib/format"
import { cn } from "@/lib/utils"

interface NavItem {
  href: string
  label: string
  icon: LucideIcon
  exact?: boolean
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/ombor", label: "Ombor", icon: PackageIcon, exact: true },
  { href: "/ombor/kirim", label: "Kirim", icon: PackagePlusIcon },
  { href: "/ombor/chiqim", label: "Chiqim", icon: PackageMinusIcon },
  { href: "/ombor/operatsiyalar", label: "Operatsiyalar", icon: MoveIcon },
  { href: "/ombor/taminotchilar", label: "Ta'minotchilar", icon: TruckIcon },
  { href: "/ombor/klientlar", label: "Klientlar", icon: UsersIcon },
  { href: "/ombor/statistics", label: "Hisobotlar", icon: ChartLineIcon },
  { href: "/ombor/ai", label: "AI yordamchi", icon: BotIcon },
]

interface AppSidebarProps {
  collapsed?: boolean
  onToggle?: () => void
  onNavigate?: () => void
}

export function AppSidebar({ collapsed = false, onToggle, onNavigate }: AppSidebarProps) {
  const pathname = usePathname()
  const { me, isAdmin, signOut } = useAuth()
  const { resolvedTheme, setTheme } = useTheme()

  const isActive = (item: NavItem) =>
    item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`)

  const linkClass = (active: boolean) =>
    cn(
      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
      active ? "bg-primary text-primary-foreground shadow-sm" : "text-sidebar-foreground hover:bg-muted",
      collapsed && "justify-center px-2",
    )

  const name = me?.full_name || me?.email || "Foydalanuvchi"

  return (
    <aside className="flex h-full flex-col gap-2 bg-sidebar p-3">
      {onToggle && (
        <div className={cn("flex", collapsed ? "justify-center" : "justify-end")}>
          <Button variant="ghost" size="icon-sm" onClick={onToggle} aria-label="Menyuni yig'ish">
            <ChevronLeftIcon className={cn("transition-transform", collapsed && "rotate-180")} />
          </Button>
        </div>
      )}

      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={linkClass(isActive(item))}
            title={collapsed ? item.label : undefined}
          >
            <item.icon className="size-4.5 shrink-0" />
            {!collapsed && item.label}
          </Link>
        ))}
      </nav>

      <div className="flex flex-col gap-1 border-t pt-2">
        {isAdmin && (
          <Link
            href="/ombor/role"
            onClick={onNavigate}
            className={linkClass(pathname === "/ombor/role")}
            title={collapsed ? "Role" : undefined}
          >
            <UserCogIcon className="size-4.5 shrink-0" />
            {!collapsed && "Role"}
          </Link>
        )}
        {isAdmin && (
          <Link
            href="/ombor/loglar"
            onClick={onNavigate}
            className={linkClass(pathname === "/ombor/loglar")}
            title={collapsed ? "Loglar" : undefined}
          >
            <FileClockIcon className="size-4.5 shrink-0" />
            {!collapsed && "Loglar"}
          </Link>
        )}
        <button
          type="button"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          className={linkClass(false)}
          title={collapsed ? "Theme" : undefined}
        >
          {resolvedTheme === "dark" ? <SunIcon className="size-4.5" /> : <MoonIcon className="size-4.5" />}
          {!collapsed && "Theme"}
        </button>
      </div>

      <div className={cn("flex items-center gap-2 rounded-lg px-2 py-2", collapsed && "flex-col")}>
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground uppercase">
          {name[0]}
        </span>
        {!collapsed && (
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">{name}</p>
            <p className="flex items-center gap-1 text-[11px] text-muted-foreground uppercase">
              <ShieldCheckIcon className="size-3" />
              {me ? ROLE_LABEL[me.role] : "..."}
            </p>
          </div>
        )}
        <Button variant="ghost" size="icon-sm" onClick={signOut} aria-label="Chiqish">
          <LogOutIcon />
        </Button>
      </div>
    </aside>
  )
}
