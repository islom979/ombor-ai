-- =============================================================================
-- 001_schema.sql — Ombor AI: asosiy sxema (Supabase PostgreSQL)
-- Supabase SQL Editor'da tartib bilan ishga tushiring: 001 → 002 → 003 → (seed)
-- Skript idempotent: qayta ishga tushirish xavfsiz.
-- =============================================================================

create extension if not exists pgcrypto;
create extension if not exists pg_trgm;

-- -----------------------------------------------------------------------------
-- ENUM turlari
-- -----------------------------------------------------------------------------
do $$ begin
  create type public.user_role as enum ('admin', 'manager', 'viewer');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.counterparty_kind as enum ('supplier', 'client');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.product_unit as enum ('kg', 'dona', 'litr', 'metr', 'quti');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.invoice_type as enum ('kirim', 'chiqim', 'utilizatsiya');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.invoice_status as enum ('accepted', 'cancelled');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.payment_status as enum ('unpaid', 'partial', 'paid');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.payment_method as enum ('cash', 'card', 'transfer');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.payment_direction as enum ('incoming', 'outgoing');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.ai_command_status as enum ('pending', 'running', 'completed', 'failed');
exception when duplicate_object then null; end $$;

-- -----------------------------------------------------------------------------
-- 1. profiles — Supabase auth.users bilan 1:1 bog'langan foydalanuvchilar
-- -----------------------------------------------------------------------------
create table if not exists public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  email       text not null,
  full_name   text,
  role        public.user_role not null default 'viewer',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- 2. products — mahsulotlar katalogi
-- -----------------------------------------------------------------------------
create table if not exists public.products (
  id                  uuid primary key default gen_random_uuid(),
  name                text not null check (length(trim(name)) > 0),
  unit                public.product_unit not null default 'dona',
  barcode             text unique,
  min_stock           numeric(14, 3) not null default 0 check (min_stock >= 0),
  default_sale_price  numeric(14, 2) not null default 0 check (default_sale_price >= 0),
  is_active           boolean not null default true,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create unique index if not exists products_name_active_uq
  on public.products (lower(name)) where is_active;
create index if not exists products_name_trgm_idx
  on public.products using gin (name gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- 3. counterparties — ta'minotchilar va klientlar
--    balance konvensiyasi: musbat = BIZ ularga qarzdormiz,
--                          manfiy = ULAR bizga qarzdor.
-- -----------------------------------------------------------------------------
create table if not exists public.counterparties (
  id          uuid primary key default gen_random_uuid(),
  kind        public.counterparty_kind not null,
  name        text not null check (length(trim(name)) > 0),
  phone       text,
  address     text,
  note        text,
  balance     numeric(16, 2) not null default 0,
  is_active   boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists counterparties_kind_idx
  on public.counterparties (kind, is_active, created_at desc);
create index if not exists counterparties_name_trgm_idx
  on public.counterparties using gin (name gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- 4. cash_registers — kassalar
-- -----------------------------------------------------------------------------
create table if not exists public.cash_registers (
  id          uuid primary key default gen_random_uuid(),
  name        text not null unique,
  balance     numeric(16, 2) not null default 0,
  is_active   boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- 5. invoices — kirim / chiqim / utilizatsiya hujjatlari
-- -----------------------------------------------------------------------------
create table if not exists public.invoices (
  id                uuid primary key default gen_random_uuid(),
  number            text not null unique,
  type              public.invoice_type not null,
  counterparty_id   uuid references public.counterparties (id) on delete restrict,
  status            public.invoice_status not null default 'accepted',
  payment_status    public.payment_status not null default 'unpaid',
  subtotal          numeric(16, 2) not null default 0 check (subtotal >= 0),
  discount_percent  numeric(5, 2)  not null default 0 check (discount_percent between 0 and 100),
  discount_amount   numeric(16, 2) not null default 0 check (discount_amount >= 0),
  total             numeric(16, 2) not null default 0 check (total >= 0),
  paid_amount       numeric(16, 2) not null default 0 check (paid_amount >= 0),
  note              text,
  source            text not null default 'web' check (source in ('web', 'ai')),
  created_by        uuid references public.profiles (id) on delete set null,
  created_at        timestamptz not null default now(),
  constraint invoices_counterparty_required
    check ((type = 'utilizatsiya') = (counterparty_id is null)),
  constraint invoices_paid_le_total check (paid_amount <= total)
);
create index if not exists invoices_type_created_idx
  on public.invoices (type, created_at desc);
create index if not exists invoices_counterparty_created_idx
  on public.invoices (counterparty_id, created_at desc);
create index if not exists invoices_open_idx
  on public.invoices (counterparty_id, created_at)
  where payment_status <> 'paid' and status = 'accepted';

-- -----------------------------------------------------------------------------
-- 6. batches — partiyalar (har bir kirim yangi partiya yaratadi)
-- -----------------------------------------------------------------------------
create table if not exists public.batches (
  id                uuid primary key default gen_random_uuid(),
  product_id        uuid not null references public.products (id) on delete restrict,
  invoice_id        uuid references public.invoices (id) on delete set null,
  code              text not null unique,
  purchase_price    numeric(14, 2) not null check (purchase_price >= 0),
  sale_price        numeric(14, 2) not null check (sale_price >= 0),
  initial_quantity  numeric(14, 3) not null check (initial_quantity > 0),
  quantity          numeric(14, 3) not null check (quantity >= 0),
  received_at       timestamptz not null default now(),
  created_at        timestamptz not null default now()
);
create index if not exists batches_product_fifo_idx
  on public.batches (product_id, received_at, id) where quantity > 0;

-- -----------------------------------------------------------------------------
-- 7. invoice_items — hujjat qatorlari
-- -----------------------------------------------------------------------------
create table if not exists public.invoice_items (
  id          uuid primary key default gen_random_uuid(),
  invoice_id  uuid not null references public.invoices (id) on delete cascade,
  position    integer not null check (position >= 0),
  product_id  uuid not null references public.products (id) on delete restrict,
  batch_id    uuid not null references public.batches (id) on delete restrict,
  quantity    numeric(14, 3) not null check (quantity > 0),
  unit_price  numeric(14, 2) not null check (unit_price >= 0),
  cost_price  numeric(14, 2) not null check (cost_price >= 0),
  line_total  numeric(16, 2) not null check (line_total >= 0)
);
create index if not exists invoice_items_invoice_idx on public.invoice_items (invoice_id, position);
create index if not exists invoice_items_product_idx on public.invoice_items (product_id);

-- -----------------------------------------------------------------------------
-- 8. payments + payment_allocations — to'lovlar va ularning invoicelarga taqsimoti
-- -----------------------------------------------------------------------------
create table if not exists public.payments (
  id                uuid primary key default gen_random_uuid(),
  counterparty_id   uuid not null references public.counterparties (id) on delete restrict,
  cash_register_id  uuid not null references public.cash_registers (id) on delete restrict,
  direction         public.payment_direction not null,
  method            public.payment_method not null default 'cash',
  amount            numeric(16, 2) not null check (amount > 0),
  note              text,
  created_by        uuid references public.profiles (id) on delete set null,
  created_at        timestamptz not null default now()
);
create index if not exists payments_counterparty_created_idx
  on public.payments (counterparty_id, created_at desc);
create index if not exists payments_cash_register_idx
  on public.payments (cash_register_id, created_at desc);

create table if not exists public.payment_allocations (
  payment_id  uuid not null references public.payments (id) on delete cascade,
  invoice_id  uuid not null references public.invoices (id) on delete cascade,
  amount      numeric(16, 2) not null check (amount > 0),
  primary key (payment_id, invoice_id)
);
create index if not exists payment_allocations_invoice_idx
  on public.payment_allocations (invoice_id);

-- -----------------------------------------------------------------------------
-- 9. ai_commands — AI agentga berilgan buyruqlar tarixi
-- -----------------------------------------------------------------------------
create table if not exists public.ai_commands (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid references public.profiles (id) on delete set null,
  prompt         text not null check (length(trim(prompt)) > 0),
  status         public.ai_command_status not null default 'pending',
  response       text,
  error          text,
  tool_calls     jsonb not null default '[]'::jsonb,
  model          text,
  input_tokens   integer,
  output_tokens  integer,
  claimed_by     text,
  started_at     timestamptz,
  finished_at    timestamptz,
  created_at     timestamptz not null default now()
);
create index if not exists ai_commands_queue_idx
  on public.ai_commands (created_at) where status = 'pending';
create index if not exists ai_commands_user_created_idx
  on public.ai_commands (user_id, created_at desc);
