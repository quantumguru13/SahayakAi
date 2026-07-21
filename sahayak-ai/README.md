# Sahayak AI — Humanitarian Case Intelligence Platform

> An AI-native operational copilot that turns fragmented, unstructured NGO inputs
> (Aadhaar cards, medical reports, income certificates) into clean, **prioritized,
> actionable lifelines** — so no vulnerable individual falls through the cracks.

Built for the **Hack4Humanity** MVP. Optimized for a flawless **5-minute judge demo**
with **< 6-second** OCR-to-extraction latency.

---

## ✨ What it does

1. **Document Intake** — drag & drop an image/PDF. OCR + GPT-4o extract a strict JSON
   profile (name, government ID, deadlines, medical conditions, household income).
2. **Deterministic Urgency Matrix** — a pure function labels each case
   `CRITICAL / HIGH / MEDIUM / LOW` with an explainable reasoning string.
3. **Semantic Welfare Recommender** — matches beneficiaries against a corpus of real
   Indian welfare schemes using pgvector-style cosine similarity **blended** with
   deterministic eligibility rules, surfacing **eligibility confidence scores**.
4. **AI Daily Brief** — a live, markdown-formatted field brief with the top-3
   priorities for the day.
5. **One-click Impact Report** — donor/CSR-ready summary of case progress.

## 🧱 Tech stack

| Layer     | Technology |
| --------- | ---------- |
| Frontend  | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui-style primitives, TanStack Query v5, Framer Motion |
| Backend   | FastAPI (Python 3.11+), Pydantic v2 |
| AI        | GPT-4o (structured JSON extraction, temp 0.1), text-embedding-3-small (1536-dim) |
| OCR       | GPT-4o vision (cloud-native) with a pypdf text path; Tesseract-compatible |
| Database  | Supabase (PostgreSQL) + pgvector (schema provided) |

## 🔌 Demo mode vs. Live mode (the reliability trick)

The backend detects whether an `OPENAI_API_KEY` is present:

- **No key → DEMO_MODE** (default): deterministic mock AI + in-memory seeded data.
  Zero network, zero cost, **cannot fail on stage**. The upload pipeline maps files
  to curated realistic documents and returns the exact JSON GPT-4o would.
- **Key present → LIVE**: real GPT-4o OCR + extraction and real embeddings, using the
  identical API shapes. Add Supabase creds to persist to PostgreSQL/pgvector.

Three capabilities switch on independently, each purely by presence of config:

| Capability | Off (default) | On when you set… |
| ---------- | ------------- | ---------------- |
| **AI** | deterministic mock | `OPENAI_API_KEY` |
| **Auth** | no login (open demo) | `SUPABASE_URL` (+ frontend `NEXT_PUBLIC_SUPABASE_*`) |
| **Persistence** | in-memory (resets on restart) | `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` |

This means you can run the entire product — beautifully — with **no setup at all**, and
harden it incrementally. `FORCE_DISABLE_AUTH=true` / `FORCE_DEMO_MODE=true` guarantee an
offline demo even if creds are present.

---

## 🚀 Quick start

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional: add OPENAI_API_KEY to go live
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Health/mode: http://localhost:8000/health
- Run tests: `python -m pytest`

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL defaults to :8000
npm run dev
```

Open http://localhost:3000 → redirects to the dashboard.

> **Fresh demo:** the demo store is in-memory. Restart `uvicorn` to reset to the
> 6 seeded beneficiaries / 10 welfare schemes before presenting.

---

## 🎬 5-minute demo script

| Time | Beat | Action |
| ---- | ---- | ------ |
| 0:00–1:00 | **The Hook** | Open **Dashboard**. Point out the workspace aesthetic + AI Daily Brief with the day's top-3 priorities. |
| 1:00–2:30 | **The Magic** | Go to **New Intake** → click the **Medical report** sample (or drop a real file). Watch the OCR transcript, extracted profile, `CRITICAL` urgency (94/100) and deadlines appear in ~milliseconds. |
| 2:30–4:00 | **The Impact** | Scroll to **Matched Welfare Schemes** — PM-JAY & Rashtriya Arogya Nidhi surface with eligibility confidence and reasons. |
| 4:00–5:00 | **The Wrap** | Open **Impact Report** → one-click donor-ready summary. Close on social impact. |

---

## 🔐 Authentication

Auth is enforced automatically once `SUPABASE_URL` is set (bypassed otherwise, so the
demo stays keyless). Flow:

- **Frontend** ([`src/components/auth`](frontend/src/components/auth)) — Supabase browser
  client with **Google + email/password** sign-in. When unauthenticated, a full-screen
  login gate replaces the app; the access token is attached to every backend request.
- **Backend** ([`app/core/auth.py`](backend/app/core/auth.py)) — a FastAPI dependency
  verifies the Supabase bearer token against the project **JWKS** (asymmetric ES256/RS256)
  or the legacy HS256 secret, and resolves `{ id, email, org_id }`. All `/api/v1/*` data
  routes are guarded; `GET /api/v1/auth/me` returns the current identity.

Enable it: set `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (frontend)
and `SUPABASE_URL` (backend). For Google, enable the provider in Supabase → Auth and add
`http://localhost:3000` as a redirect URL.

## 🗄️ Persistence: provision Supabase

The store auto-switches from in-memory to **Supabase-backed** (persists across restarts,
scoped to a single org) when `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` are set. If Supabase
init fails it safely falls back to in-memory — the app never fails to boot.

1. Create a Supabase project; open the SQL editor.
2. Run [`supabase/schema.sql`](supabase/schema.sql) (tables, enums, pgvector index,
   `match_welfare_schemes()` cosine function, org-scoped RLS policies).
3. In `backend/.env` set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (the `sb_secret_…` key).
4. Seed schemes (+ embeddings) and the demo cases:
   `python backend/scripts/seed_supabase.py`.
5. Restart the backend — the log prints `Store=SupabaseStore`.

> PII: the DB never stores a raw government ID — only a masked value + a dedup hash.

---

## 📁 Project structure

```
sahayak-ai/
├── backend/                 FastAPI service
│   ├── app/
│   │   ├── main.py          app + routers + CORS
│   │   ├── core/            config, ai_engine, urgency, store, brief
│   │   ├── models/          Pydantic v2 schemas
│   │   ├── data/            seed corpus + curated demo documents
│   │   └── routes/          dashboard, beneficiaries, documents, tasks, schemes, reports
│   ├── tests/               pytest pipeline tests
│   └── Dockerfile
├── frontend/                Next.js 14 App Router
│   └── src/
│       ├── app/             dashboard, beneficiaries, intake, reports
│       ├── components/      ui/, layout/, dashboard/, beneficiary/, schemes/, intake/
│       └── lib/             api client, types, TanStack Query hooks, utils
└── supabase/                schema.sql + seed.sql
```

## 🔗 Key API endpoints (`/api/v1`)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET  | `/dashboard/brief` | AI Daily Brief + metrics |
| GET  | `/beneficiaries` | Prioritized case list |
| POST | `/documents/upload` | OCR → JSON → urgency → schemes → tasks |
| GET  | `/beneficiaries/{id}/schemes` | Semantic welfare matches |
| PATCH| `/tasks/{id}` | Update task status |
| GET  | `/reports/impact` | One-click impact report |

---

_“To ensure no vulnerable individual falls through the cracks of social infrastructure.”_
