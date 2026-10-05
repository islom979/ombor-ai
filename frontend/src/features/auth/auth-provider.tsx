"use client"

import type { Session } from "@supabase/supabase-js"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

import { usersApi } from "@/lib/api/endpoints"
import { isConfigured } from "@/lib/env"
import type { Me } from "@/lib/api/types"
import { queryKeys } from "@/lib/query-keys"
import { getSupabase } from "@/lib/supabase/client"

interface AuthContextValue {
  session: Session | null
  me: Me | undefined
  isLoading: boolean
  canWrite: boolean
  isAdmin: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [session, setSession] = useState<Session | null>(null)
  // Sozlanmagan bo'lsa sessiya yuklashning hojati yo'q — login sahifasi ogohlantirish ko'rsatadi.
  const [sessionLoaded, setSessionLoaded] = useState(!isConfigured)

  useEffect(() => {
    if (!isConfigured) return
    const supabase = getSupabase()
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setSessionLoaded(true)
    })
    const { data } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next)
      if (!next) queryClient.clear()
    })
    return () => data.subscription.unsubscribe()
  }, [queryClient])

  const meQuery = useQuery({
    queryKey: queryKeys.me,
    queryFn: usersApi.me,
    enabled: Boolean(session),
    staleTime: 5 * 60_000,
  })

  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await getSupabase().auth.signInWithPassword({ email, password })
    if (error) throw new Error(error.message === "Invalid login credentials" ? "Email yoki parol noto'g'ri" : error.message)
  }, [])

  const signOut = useCallback(async () => {
    await getSupabase().auth.signOut()
  }, [])

  const value = useMemo<AuthContextValue>(() => {
    const role = meQuery.data?.role
    return {
      session,
      me: meQuery.data,
      isLoading: !sessionLoaded || (Boolean(session) && meQuery.isPending),
      canWrite: role === "admin" || role === "manager",
      isAdmin: role === "admin",
      signIn,
      signOut,
    }
  }, [session, sessionLoaded, meQuery.data, meQuery.isPending, signIn, signOut])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth AuthProvider ichida ishlatilishi kerak")
  return context
}
