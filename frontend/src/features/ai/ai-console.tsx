"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  BotIcon,
  CheckCircle2Icon,
  ChevronDownIcon,
  CircleDashedIcon,
  Loader2Icon,
  SendIcon,
  WrenchIcon,
  XCircleIcon,
} from "lucide-react"
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react"

import { EmptyState } from "@/components/common/empty-state"
import { PageHeader } from "@/components/common/page-header"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { useAuth } from "@/features/auth/auth-provider"
import { useInvalidateWarehouse } from "@/features/invoices/use-invalidate-warehouse"
import { aiApi } from "@/lib/api/endpoints"
import type { AiCommand, AiCommandStatus, AiToolCall } from "@/lib/api/types"
import { formatDateTime } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

const POLL_INTERVAL_MS = 1500
const ACTIVE: AiCommandStatus[] = ["pending", "running"]
const MUTATING_TOOLS = new Set(["create_kirim", "create_chiqim", "create_payment", "create_product", "create_counterparty"])

const EXAMPLES = [
  "Omborda nimalar kam qoldi?",
  "Bu oydagi foyda va eng katta qarzdor klientlarni ko'rsat",
  "Elbek Baxt uyi klientiga 5 dona Burger chiqim qil",
  "To'lanmagan kirim invoicelari qaysilar?",
]

const STATUS_VIEW: Record<AiCommandStatus, { label: string; icon: typeof BotIcon; className: string }> = {
  pending: { label: "Navbatda", icon: CircleDashedIcon, className: "text-muted-foreground" },
  running: { label: "Bajarilmoqda", icon: Loader2Icon, className: "text-primary [&_svg]:animate-spin" },
  completed: { label: "Bajarildi", icon: CheckCircle2Icon, className: "text-success" },
  failed: { label: "Xato", icon: XCircleIcon, className: "text-destructive" },
}

function StatusLabel({ status }: { status: AiCommandStatus }) {
  const view = STATUS_VIEW[status]
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs font-medium", view.className)}>
      <view.icon className="size-3.5" /> {view.label}
    </span>
  )
}

function ToolCallItem({ call }: { call: AiToolCall }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-md border bg-muted/40 text-xs">
      <button type="button" className="flex w-full items-center gap-2 px-2 py-1.5 text-left" onClick={() => setOpen((v) => !v)}>
        <WrenchIcon className={cn("size-3.5", call.is_error ? "text-destructive" : "text-primary")} />
        <span className="font-mono font-medium">{call.name}</span>
        {MUTATING_TOOLS.has(call.name) && !call.is_error && (
          <span className="rounded bg-warning/20 px-1 text-[10px] font-semibold text-amber-700 uppercase dark:text-warning">
            o&apos;zgartirish
          </span>
        )}
        {call.duration_ms !== null && <span className="text-muted-foreground">{call.duration_ms} ms</span>}
        <ChevronDownIcon className={cn("ml-auto size-3.5 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <pre className="max-h-64 overflow-auto border-t px-2 py-1.5 font-mono text-[11px] whitespace-pre-wrap">
          {JSON.stringify({ input: call.input, output: call.output }, null, 2)}
        </pre>
      )}
    </div>
  )
}

function CommandCard({ command }: { command: AiCommand }) {
  return (
    <Card className="gap-3 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium break-words">{command.prompt}</p>
          <p className="text-xs text-muted-foreground">
            {formatDateTime(command.created_at)}
            {command.user_email && ` · ${command.user_email}`}
          </p>
        </div>
        <StatusLabel status={command.status} />
      </div>

      {command.tool_calls.length > 0 && (
        <div className="grid gap-1.5">
          {command.tool_calls.map((call, index) => (
            <ToolCallItem key={`${call.name}-${index}`} call={call} />
          ))}
        </div>
      )}

      {command.status === "pending" && (
        <p className="text-sm text-muted-foreground">Agent buyruqni olishini kutmoqda...</p>
      )}
      {command.response && (
        <div className="flex gap-2 rounded-lg bg-primary/5 p-3">
          <BotIcon className="mt-0.5 size-4 shrink-0 text-primary" />
          <p className="text-sm whitespace-pre-wrap">{command.response}</p>
        </div>
      )}
      {command.status === "failed" && command.error && command.error !== command.response && (
        <p className="text-sm text-destructive">{command.error}</p>
      )}
      {command.model && (
        <p className="text-[11px] text-muted-foreground">
          {command.model} · {command.input_tokens ?? 0} / {command.output_tokens ?? 0} token
        </p>
      )}
    </Card>
  )
}

export function AiConsole() {
  const { canWrite } = useAuth()
  const queryClient = useQueryClient()
  const invalidateWarehouse = useInvalidateWarehouse()
  const [prompt, setPrompt] = useState("")
  const previouslyActive = useRef<Set<string>>(new Set())

  const commands = useQuery({
    queryKey: queryKeys.ai.all,
    queryFn: () => aiApi.list({ size: 30 }),
    // Real vaqt: faol buyruq bor ekan, holat har 1.5 soniyada yangilanadi.
    refetchInterval: (query) =>
      query.state.data?.items.some((c) => ACTIVE.includes(c.status)) ? POLL_INTERVAL_MS : false,
  })

  // Agent ma'lumotni o'zgartirgan bo'lsa, buyruq tugashi bilan ombor keshlarini yangilaymiz.
  useEffect(() => {
    const items = commands.data?.items ?? []
    const finishedWithWrites = items.some(
      (c) =>
        previouslyActive.current.has(c.id) &&
        !ACTIVE.includes(c.status) &&
        c.tool_calls.some((t) => MUTATING_TOOLS.has(t.name) && !t.is_error),
    )
    if (finishedWithWrites) invalidateWarehouse()
    previouslyActive.current = new Set(items.filter((c) => ACTIVE.includes(c.status)).map((c) => c.id))
  }, [commands.data, invalidateWarehouse])

  const send = useMutation({
    mutationFn: aiApi.create,
    onSuccess: () => {
      setPrompt("")
      void queryClient.invalidateQueries({ queryKey: queryKeys.ai.all })
    },
  })

  function submit(event?: FormEvent) {
    event?.preventDefault()
    const text = prompt.trim()
    if (text && !send.isPending) send.mutate(text)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) submit()
  }

  return (
    <>
      <PageHeader title="AI yordamchi" subtitle="Claude orqali tizimni tabiiy tilda boshqarish" />

      {canWrite ? (
        <Card className="mb-6 gap-3 p-4">
          <form onSubmit={submit} className="grid gap-3">
            <Textarea
              rows={3}
              placeholder="Masalan: Omborda nimalar kam qoldi? (Ctrl+Enter — yuborish)"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              maxLength={4000}
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-1.5">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    className="rounded-full border px-2.5 py-1 text-xs text-muted-foreground hover:border-primary hover:text-primary"
                    onClick={() => setPrompt(example)}
                  >
                    {example}
                  </button>
                ))}
              </div>
              <Button type="submit" disabled={!prompt.trim() || send.isPending}>
                <SendIcon /> Yuborish
              </Button>
            </div>
          </form>
        </Card>
      ) : (
        <p className="mb-6 text-sm text-muted-foreground">AI&apos;ga buyruq berish uchun menejer yoki admin roli kerak.</p>
      )}

      <div className="grid gap-3">
        {commands.isPending && <Skeleton className="h-24" />}
        {commands.data?.items.length === 0 && (
          <EmptyState icon={BotIcon} title="Hali buyruqlar yo'q" description="Yuqoridagi maydonga savol yoki topshiriq yozing" />
        )}
        {commands.data?.items.map((command) => <CommandCard key={command.id} command={command} />)}
      </div>
    </>
  )
}
