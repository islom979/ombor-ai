-- =============================================================================
-- 004_audit_logs.sql — audit jurnali: har bir API so'rovi (kim, nima, qachon, qayerdan)
-- =============================================================================

create table if not exists public.audit_logs (
  id            bigint generated always as identity primary key,
  created_at    timestamptz not null default now(),

  -- Kim
  actor_kind    text not null check (actor_kind in ('user', 'agent', 'anonymous')),
  user_id       uuid references public.profiles (id) on delete set null,
  user_email    text,
  user_role     public.user_role,

  -- Nima
  action        text not null,                -- masalan: create_kirim, login, list_invoices
  method        text not null,
  path          text not null,                -- shablon: /api/v1/invoices/{invoice_id}
  path_params   jsonb not null default '{}'::jsonb,
  query         text,
  request_body  jsonb,                        -- faqat yozish amallarida, 8 KB gacha
  status_code   integer not null,
  duration_ms   integer not null,

  -- Qayerdan
  ip            inet,
  user_agent    text,
  country       text,
  region        text,
  city          text,
  latitude      double precision,
  longitude     double precision,
  request_id    text
);

create index if not exists audit_logs_created_idx on public.audit_logs (created_at desc);
create index if not exists audit_logs_user_created_idx on public.audit_logs (user_id, created_at desc);
create index if not exists audit_logs_action_created_idx on public.audit_logs (action, created_at desc);
create index if not exists audit_logs_ip_idx on public.audit_logs (ip);

-- Jurnal faqat qo'shiladi: hech kim (hatto admin ham PostgREST orqali) tahrirlay yoki o'chira olmaydi.
alter table public.audit_logs enable row level security;
revoke all on public.audit_logs from anon;

drop policy if exists audit_logs_select_admin on public.audit_logs;
create policy audit_logs_select_admin on public.audit_logs
  for select to authenticated
  using (public.is_admin());
