import { createClient, type SupabaseClient } from "@supabase/supabase-js"

import { env } from "@/lib/env"

let browserClient: SupabaseClient | null = null

/** Brauzer uchun yagona Supabase klienti (sessiya localStorage'da saqlanadi). */
export function getSupabase(): SupabaseClient {
  browserClient ??= createClient(env.supabaseUrl, env.supabaseAnonKey, {
    auth: { persistSession: true, autoRefreshToken: true },
  })
  return browserClient
}
