import { describe, expect, it } from "vitest"

import { matchPreset, rangeFor } from "@/lib/date-ranges"

// 2026-09-10 — payshanba
const THURSDAY = new Date(2026, 8, 10, 15, 0)

describe("rangeFor", () => {
  it("bugun", () => {
    expect(rangeFor("today", THURSDAY)).toEqual({ from: "2026-09-10", to: "2026-09-10" })
  })

  it("shu hafta dushanbadan boshlanadi", () => {
    expect(rangeFor("week", THURSDAY)).toEqual({ from: "2026-09-07", to: "2026-09-10" })
  })

  it("yakshanba kuni hafta oldingi dushanbadan boshlanadi", () => {
    const sunday = new Date(2026, 8, 13)
    expect(rangeFor("week", sunday).from).toBe("2026-09-07")
  })

  it("dushanba kuni hafta shu kunning o'zi", () => {
    const monday = new Date(2026, 8, 7)
    expect(rangeFor("week", monday)).toEqual({ from: "2026-09-07", to: "2026-09-07" })
  })

  it("joriy oy 1-sanadan", () => {
    expect(rangeFor("month", THURSDAY)).toEqual({ from: "2026-09-01", to: "2026-09-10" })
  })

  it("barchasi — chegarasiz", () => {
    expect(rangeFor("all", THURSDAY)).toEqual({ from: "", to: "" })
  })
})

describe("matchPreset", () => {
  it("joriy sana oralig'iga mos presetni topadi", () => {
    expect(matchPreset(rangeFor("today"))).toBe("today")
    expect(matchPreset({ from: "", to: "" })).toBe("all")
  })

  it("qo'lda kiritilgan oraliq uchun null", () => {
    expect(matchPreset({ from: "2020-01-01", to: "2020-01-02" })).toBeNull()
  })
})
