"use client"

import { Loader2Icon, WarehouseIcon } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/features/auth/auth-provider"
import { isConfigured, missingEnv } from "@/lib/env"

export default function LoginPage() {
  const router = useRouter()
  const { session, signIn } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (session) router.replace("/ombor")
  }, [session, router])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await signIn(email, password)
      router.replace("/ombor")
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Kirishda xato")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="mx-auto mb-2 flex size-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <WarehouseIcon className="size-6" />
          </div>
          <CardTitle className="text-xl">Ombor AI</CardTitle>
          <CardDescription>Tizimga kirish</CardDescription>
        </CardHeader>
        <CardContent>
          {!isConfigured && (
            <div className="mb-4 rounded-lg border border-warning/50 bg-warning/10 p-3 text-sm">
              <p className="font-medium">Ilova hali sozlanmagan</p>
              <p className="mt-1 text-muted-foreground">
                Vercel → Project Settings → Environment Variables bo&apos;limida quyidagilarni kiriting va qayta deploy
                qiling: <span className="font-mono text-xs">{missingEnv.join(", ")}</span>
              </p>
            </div>
          )}
          <form onSubmit={handleSubmit} className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="password">Parol</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" size="lg" disabled={submitting || !isConfigured}>
              {submitting && <Loader2Icon className="animate-spin" />}
              Kirish
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  )
}
