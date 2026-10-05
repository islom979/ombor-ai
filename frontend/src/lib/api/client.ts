import { env } from "@/lib/env"
import { getSupabase } from "@/lib/supabase/client"

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = "ApiError"
  }
}

type QueryValue = string | number | boolean | null | undefined
export type Query = Record<string, QueryValue>

interface RequestOptions {
  query?: Query
  body?: unknown
  signal?: AbortSignal
}

function buildUrl(path: string, query?: Query): string {
  const url = new URL(`${env.apiUrl}${path}`)
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value))
    }
  }
  return url.toString()
}

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await getSupabase().auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const payload = await response.json()
    const error = payload?.error ?? {}
    return new ApiError(
      response.status,
      error.code ?? "http_error",
      error.message ?? response.statusText,
      error.details ?? {},
    )
  } catch {
    return new ApiError(response.status, "http_error", response.statusText || "So'rov bajarilmadi")
  }
}

async function send(method: string, path: string, options: RequestOptions = {}): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json", ...(await authHeaders()) }
  if (options.body !== undefined) headers["Content-Type"] = "application/json"

  let response: Response
  try {
    response = await fetch(buildUrl(path, options.query), {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause
    throw new ApiError(0, "network_error", "Server bilan aloqa yo'q")
  }
  if (!response.ok) throw await toApiError(response)
  return response
}

async function request<T>(method: string, path: string, options?: RequestOptions): Promise<T> {
  const response = await send(method, path, options)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string, query?: Query, signal?: AbortSignal) => request<T>("GET", path, { query, signal }),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  delete: (path: string) => request<void>("DELETE", path),
  /** Faylni yuklab olish (masalan, CSV eksport). */
  async download(path: string, fallbackName: string): Promise<void> {
    const response = await send("GET", path)
    const disposition = response.headers.get("Content-Disposition") ?? ""
    const filename = /filename="?([^"]+)"?/.exec(disposition)?.[1] ?? fallbackName
    const url = URL.createObjectURL(await response.blob())
    const link = Object.assign(document.createElement("a"), { href: url, download: filename })
    link.click()
    URL.revokeObjectURL(url)
  },
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const fieldErrors = error.details?.errors as { field: string; message: string }[] | undefined
    if (fieldErrors?.length) {
      return `${error.message}: ${fieldErrors.map((e) => `${e.field} — ${e.message}`).join("; ")}`
    }
    return error.message
  }
  return error instanceof Error ? error.message : "Noma'lum xato"
}
