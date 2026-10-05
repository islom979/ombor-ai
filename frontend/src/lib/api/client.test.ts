import { beforeEach, describe, expect, it, vi } from "vitest"

import { api, ApiError, errorMessage } from "@/lib/api/client"

const getSession = vi.fn()
vi.mock("@/lib/supabase/client", () => ({
  getSupabase: () => ({ auth: { getSession } }),
}))

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

describe("api client", () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn()
    vi.stubGlobal("fetch", fetchMock)
    getSession.mockResolvedValue({ data: { session: { access_token: "jwt-123" } } })
  })

  it("Bearer token va bo'sh bo'lmagan query parametrlarini yuboradi", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }))
    await api.get("/stock", { search: "bur", low_only: false, empty: "", missing: undefined, nothing: null })

    const [url, init] = fetchMock.mock.calls[0]
    const parsed = new URL(url)
    expect(parsed.origin + parsed.pathname).toBe("http://api.test/api/v1/stock")
    expect(Object.fromEntries(parsed.searchParams)).toEqual({ search: "bur", low_only: "false" })
    expect(init.headers.Authorization).toBe("Bearer jwt-123")
    expect(init.headers["Content-Type"]).toBeUndefined()
  })

  it("sessiya bo'lmasa Authorization sarlavhasi qo'shilmaydi", async () => {
    getSession.mockResolvedValue({ data: { session: null } })
    fetchMock.mockResolvedValue(jsonResponse({}))
    await api.get("/stock")
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined()
  })

  it("POST body'ni JSON qilib yuboradi", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: "1" }, 201))
    const result = await api.post<{ id: string }>("/products", { name: "Burger" })
    const init = fetchMock.mock.calls[0][1]
    expect(init.method).toBe("POST")
    expect(init.headers["Content-Type"]).toBe("application/json")
    expect(JSON.parse(init.body)).toEqual({ name: "Burger" })
    expect(result).toEqual({ id: "1" })
  })

  it("204 javobda undefined qaytaradi", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }))
    await expect(api.delete("/products/1")).resolves.toBeUndefined()
  })

  it("backend xato formatini ApiError'ga aylantiradi", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "insufficient_stock", message: "Burger yetarli emas", details: { a: 1 } } }, 409),
    )
    const error = await api.post("/invoices/chiqim", {}).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 409, code: "insufficient_stock", message: "Burger yetarli emas" })
  })

  it("JSON bo'lmagan xato javobida ham ApiError beradi", async () => {
    fetchMock.mockResolvedValue(new Response("Bad gateway", { status: 502, statusText: "Bad Gateway" }))
    const error = await api.get("/stock").catch((e) => e)
    expect(error).toMatchObject({ status: 502, code: "http_error" })
  })

  it("tarmoq xatosini tushunarli xabarga aylantiradi", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"))
    const error = await api.get("/stock").catch((e) => e)
    expect(error).toMatchObject({ status: 0, code: "network_error", message: "Server bilan aloqa yo'q" })
  })

  it("so'rov bekor qilinganda AbortError'ni o'zgartirmaydi", async () => {
    fetchMock.mockRejectedValue(new DOMException("aborted", "AbortError"))
    const error = await api.get("/stock").catch((e) => e)
    expect(error).toBeInstanceOf(DOMException)
  })
})

describe("errorMessage", () => {
  it("maydon xatolarini birlashtiradi", () => {
    const error = new ApiError(422, "validation_failed", "So'rov ma'lumotlari noto'g'ri", {
      errors: [
        { field: "name", message: "required" },
        { field: "unit", message: "invalid" },
      ],
    })
    expect(errorMessage(error)).toBe("So'rov ma'lumotlari noto'g'ri: name — required; unit — invalid")
  })

  it("oddiy Error va noma'lum qiymatlar", () => {
    expect(errorMessage(new Error("boom"))).toBe("boom")
    expect(errorMessage("x")).toBe("Noma'lum xato")
  })
})
