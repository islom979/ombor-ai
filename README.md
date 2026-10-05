# Ombor AI — ombor boshqaruv tizimi + Claude AI yordamchi

Ulgurji ombor uchun to'liq tizim: **qoldiq (partiyalar kesimida), kirim, chiqim, operatsiyalar tarixi,
ta'minotchilar/klientlar balansi, to'lovlar, kassalar, hisobotlar** va tizimni tabiiy tilda boshqaruvchi
**AI agent** (Claude, Tool Use / Function Calling).

| Qism | Texnologiya |
|---|---|
| `frontend/` | Next.js 16 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui (Base UI), TanStack Query |
| `backend/` | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.0 async + asyncpg |
| `database/` | Supabase PostgreSQL: jadvallar, indekslar, triggerlar, RLS siyosatlari |
| `ai_agent/` | Anthropic Python SDK (Claude Opus 5.5), tool'lar → FastAPI, navbat worker'i, CLI |

---

## 1. Arxitektura

```
 Brauzer (Next.js)                         Supabase
 ┌───────────────────┐  login (email/parol) ┌──────────────┐
 │ Dashboard UI      │ ───────────────────► │ Auth (JWT)   │
 │ TanStack Query    │                      │ PostgreSQL   │◄──── RLS (2-qatlam himoya)
 └────────┬──────────┘                      └──────▲───────┘
          │ Authorization: Bearer <JWT>            │ asyncpg (server ulanishi)
          ▼                                        │
 ┌──────────────────────────────────────────────────┴───┐
 │ FastAPI  /api/v1                                      │
 │  api (routerlar, deps) → services (biznes oqimlar)    │
 │   → repositories (SQL) → db (ORM modellari)           │
 │  domain/rules.py — sof biznes qoidalari (I/O yo'q)    │
 └───────────────▲──────────────────────────────────────┘
                 │ X-API-Key
 ┌───────────────┴──────────────┐      ┌─────────────────┐
 │ ai_agent worker              │◄────►│ Claude API      │
 │ claim → Claude tool-use →    │      │ (tool use)      │
 │ tools.py → FastAPI → natija  │      └─────────────────┘
 └──────────────────────────────┘
```

**AI buyruq oqimi:** Dashboard'da "AI yordamchi" sahifasidan buyruq yuboriladi → `ai_commands` jadvaliga
`pending` bo'lib tushadi → worker uni `FOR UPDATE SKIP LOCKED` bilan atomar egallaydi (`running`) →
Claude kerakli tool'larni chaqiradi (har bir chaqiruvdan keyin oraliq natija yoziladi) → yakuniy javob
(`completed`/`failed`). Dashboard faol buyruq bor paytda holatni har 1.5 soniyada yangilaydi, shuning
uchun tool chaqiruvlari va javob real vaqtda ko'rinadi.

### Clean architecture qoidalari (backend)

- **Qatlamlar bir yo'nalishda bog'lanadi:** `api → services → repositories → db`. Routerlarda biznes mantiq yo'q.
- **`domain/rules.py`** — partiya kodi, invoice raqami, chegirma, to'lov holati, balans yo'nalishlari,
  to'lovni invoicelarga taqsimlash. Hech qanday I/O yo'q — to'liq unit-test qilingan.
- **Unit of Work:** bitta HTTP so'rov = bitta tranzaksiya. Xato bo'lsa hammasi rollback.
- **Konkurentlik:** chiqimda partiyalar `SELECT … FOR UPDATE` bilan qulflanadi; DB'da `CHECK (quantity >= 0)`
  oxirgi himoya. Test: 5 ta parallel chiqimdan faqat qoldiq yetadiganlari o'tadi.
- **Xatolar:** servislar faqat `AppError` turlarini ko'taradi; HTTP'ga moslash bitta joyda (`main.py`).
  Javob formati: `{"error": {"code", "message", "details"}}`.
- **Pul** — `NUMERIC` / `Decimal` (float emas); JSON'da son sifatida qaytadi.

### Ma'lumotlar modeli

`profiles` (auth.users bilan 1:1, rol) · `products` · `batches` (partiyalar) · `counterparties`
(ta'minotchi/klient + balans) · `invoices` + `invoice_items` (kirim/chiqim/utilizatsiya) ·
`payments` + `payment_allocations` (to'lov → invoicelar) · `cash_registers` · `ai_commands` (AI tarixi).

**Balans konvensiyasi:** musbat — biz kontragentga qarzdormiz; manfiy — kontragent bizga qarzdor.

---

## 2. Papkalar strukturasi

```
ombor-ai/
├── database/
│   ├── migrations/001_schema.sql            # ENUM'lar, 10 jadval, indekslar
│   ├── migrations/002_functions_triggers.sql # updated_at, yangi user → profil, rol funksiyalari
│   ├── migrations/003_rls_policies.sql      # Row Level Security
│   ├── seed/seed.sql                        # demo ma'lumotnomalar (ixtiyoriy)
│   └── local/000_supabase_stubs.sql         # FAQAT lokal Postgres testlari uchun
├── backend/
│   ├── app/
│   │   ├── main.py                 # ilova fabrikasi, CORS, xato handlerlari
│   │   ├── core/                   # config, security (JWT/API key), errors, logging
│   │   ├── domain/                 # enums, rules (sof biznes qoidalari)
│   │   ├── db/                     # async engine/sessiya, ORM modellari
│   │   ├── repositories/           # SQL so'rovlar
│   │   ├── schemas/                # Pydantic v2 DTO'lar
│   │   ├── services/               # biznes oqimlar (kirim, chiqim, to'lov, ...)
│   │   └── api/                    # deps (auth, rollar), v1 routerlar
│   ├── tests/                      # unit + integratsion (haqiqiy Postgres)
│   ├── pyproject.toml, requirements.txt, Dockerfile, .env.example
├── ai_agent/
│   ├── ai_agent/
│   │   ├── tools.py                # ★ Tool ta'riflari (JSON Schema) + ijrochi
│   │   ├── agent.py                # Claude tool-use sikli
│   │   ├── worker.py               # dashboard buyruqlar navbati
│   │   ├── cli.py                  # terminal rejimi, tool schema eksporti
│   │   ├── api_client.py, config.py
│   ├── tests/, pyproject.toml, requirements.txt, Dockerfile, .env.example
├── frontend/
│   ├── src/app/                    # sahifalar: /login, /ombor, /ombor/kirim, ...
│   ├── src/features/               # stock, invoices, counterparties, statistics, ai, users, auth
│   ├── src/components/             # ui (shadcn), common, layout (sidebar, shell)
│   ├── src/lib/                    # api client + endpoints + types, format, query-keys, supabase
│   └── .env.example
└── docker-compose.yml              # backend + ai-worker
```

---

## 3. O'rnatish

### 3.1 Supabase

1. [supabase.com](https://supabase.com) da loyiha yarating.
2. Migratsiyalarni qo'llang — `backend/.env` da `DATABASE_URL` to'ldirilgach:
   `cd backend && python -m scripts.apply_migrations --seed`
   (yoki **SQL Editor**'da tartib bilan: `001_schema.sql` → `002_functions_triggers.sql` →
   `003_rls_policies.sql` → ixtiyoriy `seed/seed.sql`). Skriptlar idempotent.
3. **Authentication → Users → Add user** orqali foydalanuvchi yarating. **Birinchi foydalanuvchi
   avtomatik `admin`** bo'ladi, keyingilari `viewer` — rollarni ilovadagi **Role** sahifasida o'zgartirasiz.
4. Kerakli qiymatlar: Project URL, `anon` kalit (frontend), Database connection string (backend),
   JWT secret (legacy HS256 ishlatsangiz; aks holda backend JWKS orqali tekshiradi).

### 3.2 Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env    # DATABASE_URL, SUPABASE_URL, AI_AGENT_API_KEYS ni to'ldiring
uvicorn app.main:create_app --factory --reload --port 8000
```

Swagger: http://localhost:8000/docs · Sog'liq: http://localhost:8000/health

> Supabase **transaction pooler** (6543-port) ishlatsangiz `DB_USE_PGBOUNCER=true` qiling.

### 3.3 AI agent

```bash
cd ai_agent
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env    # ANTHROPIC_API_KEY, OMBOR_API_KEY (= backend AI_AGENT_API_KEYS dan biri)
python -m ai_agent.worker                        # dashboard navbatini qayta ishlash
python -m ai_agent.cli "Omborda nimalar kam qoldi?"   # yoki terminaldan bevosita
python -m ai_agent.cli --export-tools openai > tools.json   # Open WebUI / OpenAI-mos klientlar uchun
```

### 3.4 Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
npm run dev                  # http://localhost:3000
```

### 3.5 Vercel

| Loyiha | Papka | Manzil |
|---|---|---|
| `ombor-ai-api` (FastAPI) | `backend/` (entrypoint `app.asgi:app`, Python 3.12) | https://ombor-ai-api.vercel.app |
| `ombor-ai-web` (Next.js) | `frontend/` | https://ombor-ai-web.vercel.app |

```bash
cd backend && vercel deploy --prod      # yoki: cd frontend && vercel deploy --prod
```

Serverless uchun backend'da `DB_USE_PGBOUNCER=true` — Supabase **Transaction pooler** (6543-port) ulanish
satrini ishlating. AI worker uzoq ishlaydigan jarayon, Vercel'da ishlamaydi — uni o'z kompyuteringizda yoki
Docker'da ishga tushiring (`OMBOR_API_URL=https://ombor-ai-api.vercel.app/api/v1`).

### 3.6 Docker (backend + worker)

```bash
docker compose up --build
```

---

## 4. API (asosiy endpointlar, prefiks `/api/v1`)

| Metod | Yo'l | Rol | Vazifa |
|---|---|---|---|
| GET | `/stock`, `/stock/summary`, `/stock/available`, `/stock/export` | hamma | Qoldiq, ko'rsatkichlar, chiqim uchun partiyalar, CSV |
| GET/POST/PATCH/DELETE | `/products` | o'qish: hamma, yozish: staff | Mahsulotlar katalogi |
| GET/POST/PATCH/DELETE | `/counterparties` | o'qish: hamma, yozish: staff | Ta'minotchi/klientlar |
| GET | `/invoices`, `/invoices/{id}` | hamma | Operatsiyalar (filtrlar, sahifalash) |
| POST | `/invoices/kirim`, `/invoices/chiqim`, `/invoices/utilizatsiya` | staff | Ombor operatsiyalari |
| GET/POST | `/payments` | o'qish: hamma, yozish: staff | To'lovlar va invoicelarga taqsimlash |
| GET/POST | `/cash-registers` | o'qish: hamma, yaratish: admin | Kassalar |
| GET | `/statistics` | hamma | Hisobot (foyda, qarzlar, kassalar, operatsiyalar) |
| POST/GET | `/ai/commands` | staff / hamma | AI buyruq yuborish, tarix |
| POST | `/ai/commands/claim`, PATCH `/ai/commands/{id}` | faqat agent | Worker navbati |
| GET/PATCH | `/users/me`, `/users`, `/users/{id}/role` | me: hamma, qolgani: admin | Rollar |

*staff* = `admin` yoki `manager`. AI agent `X-API-Key` bilan `AI_AGENT_ROLE` huquqlarida ishlaydi;
agent yaratgan hujjatlar `source = 'ai'` bilan belgilanadi (UI'da ✨ belgisi).

## 5. AI tool'lar (`ai_agent/ai_agent/tools.py`)

O'qish: `get_stock_summary`, `search_stock`, `list_products`, `find_available_batches`,
`list_counterparties`, `get_counterparty`, `list_invoices`, `get_invoice`, `list_payments`,
`list_cash_registers`, `get_statistics`.
Yozish: `create_product`, `create_counterparty`, `create_kirim`, `create_chiqim`, `create_payment`.

Har bir tool'ning kirish modeli Pydantic'da yozilgan — undan JSON Schema avtomatik yasaladi va
model yuborgan argumentlar API'ga yuborilishidan oldin tekshiriladi. `AGENT_ALLOW_WRITES=false` —
agent faqat o'qiy oladi (yozish tool'lari modelga ko'rsatilmaydi ham).

---

## 6. Xavfsizlik

- Frontend → backend: Supabase JWT (`aud=authenticated`), HS256 secret yoki JWKS (RS256/ES256).
  Rol har so'rovda `profiles` jadvalidan olinadi (token'dagi da'voga ishonilmaydi).
- Agent → backend: `X-API-Key`, timing-safe solishtirish, kamida 32 belgi.
- RLS: anon hech narsa ko'rmaydi; viewer faqat o'qiydi; manager yozadi; o'chirish faqat admin;
  `ai_commands` — foydalanuvchi faqat o'zinikini ko'radi.
- CORS faqat `CORS_ORIGINS` dagi manzillar uchun; production'da `/docs` o'chiriladi.

## 7. Testlar

```bash
# Backend: unit testlar har doim; integratsion testlar alohida test bazasida
cd backend
psql "$TEST_DB" -f ../database/local/000_supabase_stubs.sql   # faqat Supabase bo'lmagan lokal Postgres uchun
for f in ../database/migrations/*.sql; do psql "$TEST_DB" -f "$f"; done
TEST_DATABASE_URL=postgresql+asyncpg://... pytest

# AI agent (Claude chaqiruvlari soxta klient bilan sinaladi — API kaliti kerak emas)
cd ai_agent && pytest

# Frontend
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```
