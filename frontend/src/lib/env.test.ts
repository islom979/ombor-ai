import { afterEach, describe, expect, it, vi } from "vitest"

async function loadEnv(values: Record<string, string | undefined>) {
  vi.resetModules()
  for (const [key, value] of Object.entries(values)) vi.stubEnv(key, value as string)
  return import("@/lib/env")
}

afterEach(() => vi.unstubAllEnvs())

describe("env", () => {
  it("hamma qiymat bor bo'lsa sozlangan hisoblanadi va oxiridagi / olib tashlanadi", async () => {
    const mod = await loadEnv({ NEXT_PUBLIC_API_URL: "https://api.uz/api/v1/" })
    expect(mod.isConfigured).toBe(true)
    expect(mod.env.apiUrl).toBe("https://api.uz/api/v1")
  })

  it("namuna (<...>) qiymatlarni yetishmayotgan deb biladi", async () => {
    const mod = await loadEnv({
      NEXT_PUBLIC_SUPABASE_URL: "https://<project-ref>.supabase.co",
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "",
    })
    expect(mod.isConfigured).toBe(false)
    expect(mod.missingEnv).toEqual(["NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"])
    expect(() => mod.env.supabaseUrl).toThrow(/NEXT_PUBLIC_SUPABASE_URL/)
  })
})
