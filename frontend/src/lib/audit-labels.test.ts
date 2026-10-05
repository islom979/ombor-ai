import { describe, expect, it } from "vitest"

import { actionKind, actionLabel, actorName, countryFlag, deviceLabel, location } from "@/lib/audit-labels"

describe("audit labels", () => {
  it("ma'lum amallarni tarjima qiladi, noma'lumini o'zgartirmaydi", () => {
    expect(actionLabel("create_kirim")).toBe("Kirim qildi")
    expect(actionLabel("auth.login")).toBe("Tizimga kirdi")
    expect(actionLabel("something_new")).toBe("something_new")
  })

  it("amal turini aniqlaydi", () => {
    expect(actionKind({ action: "auth.logout", method: "POST" })).toBe("auth")
    expect(actionKind({ action: "list_stock", method: "GET" })).toBe("read")
    expect(actionKind({ action: "delete_product", method: "DELETE" })).toBe("write")
  })

  it("bajaruvchini ko'rsatadi", () => {
    expect(actorName({ actor_kind: "agent", user_email: null })).toBe("AI agent")
    expect(actorName({ actor_kind: "anonymous", user_email: null })).toBe("Noma'lum (kirmagan)")
    expect(actorName({ actor_kind: "user", user_email: "a@b.uz" })).toBe("a@b.uz")
  })

  it("davlat bayrog'i va joylashuv", () => {
    expect(countryFlag("UZ")).toBe("🇺🇿")
    expect(countryFlag("uz")).toBe("🇺🇿")
    expect(countryFlag(null)).toBe("")
    expect(countryFlag("UZB")).toBe("")
    expect(location({ city: "Tashkent", region: "TK", country: "UZ" })).toBe("Tashkent, TK, UZ")
    expect(location({ city: null, region: null, country: null })).toBe("—")
  })

  it("brauzer va OT ni aniqlaydi", () => {
    const chromeWin =
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
    const edge = `${chromeWin} Edg/140.0`
    const iphone =
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
    expect(deviceLabel(chromeWin)).toBe("Chrome · Windows")
    expect(deviceLabel(edge)).toBe("Edge · Windows")
    expect(deviceLabel(iphone)).toBe("Safari · iOS")
    expect(deviceLabel("python-httpx/0.28")).toBe("API klient")
    expect(deviceLabel(null)).toBe("—")
  })
})
