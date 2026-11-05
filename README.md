# IdeaBridge – AI-Powered Innovation Marketplace

A full-stack platform where **idea creators** submit innovations and **entrepreneurs / investors** discover, evaluate and collaborate on them. An integrated **AI evaluation agent** compares each idea with real existing projects, other ideas on the platform and (optionally) research papers, then produces a structured report with feasibility, market and novelty scores.

> **Honesty by design.** No LLM key → the app runs in a loudly-labelled **DEMO MODE** (local rule-based engine). It never presents demo output as a live AI result, and it cannot invent projects, papers or companies – similar projects come only from retrieved data and similarity percentages are real vector calculations.

## Features
* Roles: creator, entrepreneur/investor, administrator – JWT auth, role-based access, protected routes.
* Idea submission with documents, categories, stage, **public / restricted / private** visibility (enforced server-side).
* AI evaluation with live progress, versioned reports, re-run, "outdated" flag after edits.
* Hybrid similarity: embeddings + **pgvector** search over a curated dataset (70 real projects/products), platform ideas, optional arXiv.
* Smart matching with explainable 0-100 scores (industry, technology, interests, stage, market, ticket size).
* Search (keyword **and** meaning-based), filters, saved ideas, recommendations.
* Collaboration requests (accepting one unlocks a restricted idea for that person), messaging, notifications.
* Admin: analytics (Recharts), user management & entrepreneur verification, idea moderation, content reports, categories, audit log, re-embed.
* Responsive SaaS UI with loading, empty and error states.

## Architecture
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (system diagram, AI workflow, ER diagram, access model, limitations) and [docs/API.md](docs/API.md).

```
ideabridge/
  frontend/     React + TypeScript + Vite + Tailwind
  backend/      FastAPI, SQLAlchemy 2, Alembic, pytest-ready
  ai_engine/    embeddings, similarity, LLM providers, evaluator, demo engine, matching, curated dataset
  database/     init.sql (pgvector), notes
  docs/         architecture + API docs
  tests/        ai_engine (unittest), backend (pytest), e2e (API journey)
  docker-compose.yml  .env.example  README.md
```

## Prerequisites
Python 3.11+ · Node 18+ (22 recommended) · PostgreSQL 15+ with the `pgvector` extension (or Docker). SQLite works for quick local trials (no pgvector).

## Quick start with Docker
```bash
cp .env.example .env          # edit SECRET_KEY, ADMIN_EMAIL/ADMIN_PASSWORD
docker compose up --build
# App:      http://localhost:3000     API docs: http://localhost:8000/docs
```

## Local development (no Docker)
```bash
cp .env.example .env
# 1) Database (pgvector image is easiest)
docker run -d --name ib-db -p 5432:5432 -e POSTGRES_USER=ideabridge -e POSTGRES_PASSWORD=ideabridge \
  -e POSTGRES_DB=ideabridge pgvector/pgvector:pg16
#    …or use SQLite: set DATABASE_URL=sqlite:///./ideabridge.db in .env

# 2) Backend
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head          # optional: tables are also auto-created at start (AUTO_CREATE_TABLES=true)
uvicorn app.main:app --reload --port 8000

# 3) Frontend (new terminal)
cd frontend && npm install && npm run dev                 # http://localhost:5173 (proxies /api → :8000)
```
With `SEED_DEMO_DATA=true` an empty database is filled with sample data. Demo logins (password **`Demo@12345`**): `admin@ideabridge.demo`, `maya@ideabridge.demo` / `arjun@…` / `lena@…` (creators), `ravi@…` / `sofia@…` / `omar@…` (entrepreneurs, `@ideabridge.demo`). **Never enable seeding in production.**

## Environment configuration
All settings are environment variables (see `.env.example`): `DATABASE_URL`, `SECRET_KEY` (32+ chars, required when `APP_ENV=production`), `CORS_ORIGINS`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `ADMIN_EMAIL/ADMIN_PASSWORD` (bootstrap admin), `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `EMBEDDING_PROVIDER`, `EXTERNAL_RETRIEVAL`. Keys live only in backend environment variables – never in the frontend bundle.

## Database setup
`database/init.sql` enables pgvector (run automatically by the compose file). Schema: `alembic upgrade head`, or automatic `create_all` at start. After changing the embedding model run **Admin → Re-embed all content**. Details: [database/README.md](database/README.md).

## AI configuration & demo mode
| Goal | Settings |
|---|---|
| Demo mode (default) | `LLM_PROVIDER=none`, `EMBEDDING_PROVIDER=local` |
| Live reports with Claude | `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=…`, optional `LLM_MODEL` |
| Live reports with OpenAI | `LLM_PROVIDER=openai`, `OPENAI_API_KEY=…`, optional `LLM_MODEL` (works with OpenAI-compatible servers via `OPENAI_BASE_URL`) |
| Semantic embeddings | `EMBEDDING_PROVIDER=openai` (+ key). Then run *Re-embed all content* |
| arXiv research retrieval | `EXTERNAL_RETRIEVAL=arxiv` (public API, needs outbound internet) |

* The UI banner and every report show whether it came from a **live LLM** or **DEMO MODE**. If a configured LLM call fails, the report is regenerated by the demo engine and says so (with the reason).
* Default local embeddings are **lexical**, not semantic (reports state this). Similarity values are only comparable within one embedding model.
* Add a provider: subclass `LLMProvider` in `ai_engine/llm.py` and register it in `get_llm()`.
* Privacy: private ideas are never compared or sent to an LLM; restricted ideas of other users appear only as "details withheld".

## Running the tests
```bash
python -m unittest discover -s tests/ai_engine -v          # AI engine – no dependencies beyond numpy
pip install -r backend/requirements-dev.txt
pytest                                                     # backend API, auth, DB, AI service, privacy, admin, e2e journey (SQLite)
cd frontend && npm run typecheck && npm run build          # frontend validation
```

## Deployment notes
* Set `APP_ENV=production`, a random `SECRET_KEY`, real `CORS_ORIGINS`, `SEED_DEMO_DATA=false`, strong `ADMIN_PASSWORD`; terminate TLS in front (nginx/Caddy/cloud LB).
* Run `alembic upgrade head` on release; keep `uploads` on a persistent volume or move to object storage.
* Run several uvicorn/gunicorn workers behind the proxy; replace in-process background tasks and the in-memory login throttle with a queue/Redis for multi-instance setups.
* Back up PostgreSQL and the uploads volume. See "Design decisions & limitations" in the architecture doc.

## Known limitations
Documents are not analysed by the AI · comparison corpus is limited (not the whole market) · evaluations are decision-support, not legal/financial advice · email verification, password reset and e-mail notifications are not implemented · no browser (Playwright) tests are included – the e2e test exercises the full workflow at API level.
