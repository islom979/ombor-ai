// NEXT_PUBLIC_* qiymatlari build vaqtida joylanadi, shuning uchun to'liq nom bilan o'qiladi.
const raw = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL,
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL,
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
}

const NAMES: Record<keyof typeof raw, string> = {
  apiUrl: "NEXT_PUBLIC_API_URL",
  supabaseUrl: "NEXT_PUBLIC_SUPABASE_URL",
  supabaseAnonKey: "NEXT_PUBLIC_SUPABASE_ANON_KEY",
}

/** Yetishmayotgan yoki namuna (<...>) qiymatli o'zgaruvchilar ro'yxati. */
export const missingEnv: string[] = (Object.keys(raw) as (keyof typeof raw)[])
  .filter((key) => !raw[key] || raw[key]!.includes("<"))
  .map((key) => NAMES[key])

export const isConfigured = missingEnv.length === 0

function required(key: keyof typeof raw): string {
  const value = raw[key]
  if (!value || value.includes("<")) {
    throw new Error(`Muhit o'zgaruvchisi sozlanmagan: ${NAMES[key]}`)
  }
  return value
}

// Qiymatlar faqat ishlatilganda tekshiriladi — sozlanmagan holatda ham build buzilmaydi.
export const env = {
  get apiUrl() {
    return required("apiUrl").replace(/\/$/, "")
  },
  get supabaseUrl() {
    return required("supabaseUrl")
  },
  get supabaseAnonKey() {
    return required("supabaseAnonKey")
  },
}
