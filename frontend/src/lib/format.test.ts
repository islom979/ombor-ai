import { describe, expect, it } from "vitest"

import { formatDateTime, formatMoney, formatNumber, formatQuantity, initials, toIsoDate } from "@/lib/format"

describe("format", () => {
  it("raqamlarni vergul bilan ajratadi", () => {
    expect(formatNumber(1500000)).toBe("1,500,000")
    expect(formatNumber(0)).toBe("0")
    expect(formatNumber(-6056000)).toBe("-6,056,000")
    expect(formatNumber(1234.567)).toBe("1,234.57")
  })

  it("pul summasiga so'm qo'shadi", () => {
    expect(formatMoney(24000)).toBe("24,000 so'm")
  })

  it("miqdorni 3 xonagacha ko'rsatadi", () => {
    expect(formatQuantity(52.5)).toBe("52.5")
    expect(formatQuantity(0.9105)).toBe("0.911")
  })

  it("sanani mahalliy vaqtda YYYY-MM-DD HH:mm ko'rinishida beradi", () => {
    const local = new Date(2026, 8, 12, 9, 5)
    expect(formatDateTime(local.toISOString())).toBe("2026-09-12 09:05")
  })

  it("toIsoDate mahalliy sanani qaytaradi (UTC emas)", () => {
    expect(toIsoDate(new Date(2026, 0, 1, 23, 59))).toBe("2026-01-01")
  })

  it("ismdan ikki harfli bosh harflar oladi", () => {
    expect(initials("Elbek Baxt uyi")).toBe("EB")
    expect(initials("  mayonez   sof food ")).toBe("MS")
    expect(initials("Ombor")).toBe("O")
    expect(initials("")).toBe("")
  })
})
