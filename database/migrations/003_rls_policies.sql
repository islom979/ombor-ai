-- =============================================================================
-- 003_rls_policies.sql — Row Level Security
--
-- Kirish modeli:
--   * FastAPI backend bazaga server roli (postgres / service connection) bilan
--     ulanadi va RLS'ni chetlab o'tadi — biznes qoidalari backend'da tekshiriladi.
--   * RLS — himoyaning ikkinchi qatlami: kimdir Supabase anon/authenticated
--     kaliti bilan to'g'ridan-to'g'ri PostgREST orqali murojaat qilsa ham,
--     faqat ruxsat etilgan ma'lumotni ko'radi.
--   * anon roli hech narsani ko'rmaydi.
-- =============================================================================

alter table public.profiles            enable row level security;
alter table public.products            enable row level security;
alter table public.counterparties      enable row level security;
alter table public.cash_registers      enable row level security;
alter table public.invoices            enable row level security;
alter table public.batches             enable row level security;
alter table public.invoice_items       enable row level security;
alter table public.payments            enable row level security;
alter table public.payment_allocations enable row level security;
alter table public.ai_commands         enable row level security;

revoke all on all tables in schema public from anon;

-- -----------------------------------------------------------------------------
-- profiles: o'zini ko'radi; admin hammani ko'radi va rolini o'zgartiradi
-- -----------------------------------------------------------------------------
drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles
  for select to authenticated
  using (id = auth.uid() or public.is_admin());

drop policy if exists profiles_update_admin on public.profiles;
create policy profiles_update_admin on public.profiles
  for update to authenticated
  using (public.is_admin())
  with check (public.is_admin());

-- -----------------------------------------------------------------------------
-- Biznes jadvallari: profili bor har qanday foydalanuvchi o'qiydi,
-- faqat admin/manager yozadi.
-- -----------------------------------------------------------------------------
do $$
declare
  t text;
begin
  foreach t in array array[
    'products', 'counterparties', 'cash_registers', 'invoices',
    'batches', 'invoice_items', 'payments', 'payment_allocations'
  ] loop
    execute format('drop policy if exists %1$s_select on public.%1$s', t);
    execute format(
      'create policy %1$s_select on public.%1$s for select to authenticated
         using (public.current_user_role() is not null)', t);

    execute format('drop policy if exists %1$s_insert on public.%1$s', t);
    execute format(
      'create policy %1$s_insert on public.%1$s for insert to authenticated
         with check (public.is_staff())', t);

    execute format('drop policy if exists %1$s_update on public.%1$s', t);
    execute format(
      'create policy %1$s_update on public.%1$s for update to authenticated
         using (public.is_staff()) with check (public.is_staff())', t);

    execute format('drop policy if exists %1$s_delete on public.%1$s', t);
    execute format(
      'create policy %1$s_delete on public.%1$s for delete to authenticated
         using (public.is_admin())', t);
  end loop;
end $$;

-- -----------------------------------------------------------------------------
-- ai_commands: foydalanuvchi faqat o'z buyruqlarini ko'radi/yaratadi,
-- admin hammasini ko'radi. Natijani faqat backend (agent) yozadi.
-- -----------------------------------------------------------------------------
drop policy if exists ai_commands_select on public.ai_commands;
create policy ai_commands_select on public.ai_commands
  for select to authenticated
  using (user_id = auth.uid() or public.is_admin());

drop policy if exists ai_commands_insert on public.ai_commands;
create policy ai_commands_insert on public.ai_commands
  for insert to authenticated
  with check (user_id = auth.uid() and status = 'pending' and public.is_staff());

-- Realtime: dashboard AI buyruqlari holatini jonli kuzatishi uchun (ixtiyoriy)
do $$ begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    begin
      alter publication supabase_realtime add table public.ai_commands;
    exception when duplicate_object then null;
    end;
  end if;
end $$;
