import { toIsoDate } from "@/lib/format"

export type RangePreset = "today" | "week" | "month" | "all"

export interface DateRange {
  from: string
  to: string
}

export const RANGE_LABEL: Record<RangePreset, string> = {
  today: "Bugun",
  week: "Shu hafta",
  month: "Joriy oy",
  all: "Barchasi",
}

export function rangeFor(preset: RangePreset, now = new Date()): DateRange {
  const today = toIsoDate(now)
  switch (preset) {
    case "today":
      return { from: today, to: today }
    case "week": {
      const monday = new Date(now)
      monday.setDate(now.getDate() - ((now.getDay() + 6) % 7))
      return { from: toIsoDate(monday), to: today }
    }
    case "month":
      return { from: toIsoDate(new Date(now.getFullYear(), now.getMonth(), 1)), to: today }
    case "all":
      return { from: "", to: "" }
  }
}

export function matchPreset(range: DateRange): RangePreset | null {
  return (Object.keys(RANGE_LABEL) as RangePreset[]).find((preset) => {
    const candidate = rangeFor(preset)
    return candidate.from === range.from && candidate.to === range.to
  }) ?? null
}
