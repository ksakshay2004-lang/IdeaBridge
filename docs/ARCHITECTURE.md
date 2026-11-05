# IdeaBridge – Architecture

## 1. System architecture

```mermaid
flowchart LR
  subgraph Browser
    SPA["React + TS SPA<br/>(Vite, Tailwind, Router, Recharts)"]
  end
  subgraph Backend["FastAPI backend"]
    API["REST routers<br/>auth · ideas · documents · evaluations<br/>collaboration · messages · notifications · admin"]
    AUTHZ["JWT auth + RBAC<br/>permissions.idea_access()"]
    BG["BackgroundTasks<br/>evaluation pipeline"]
    SVC["Services<br/>vectors · evaluation · matching · files · seed"]
  end
  subgraph AI["ai_engine (pure Python)"]
    EMB["Embedding providers<br/>local-hash (lexical) | OpenAI (semantic)"]
    ENG["EvaluationEngine<br/>LLM path | labelled DEMO engine"]
    MATCH["Matching engine"]
    LLM["LLM providers<br/>Anthropic | OpenAI | (add yours)"]
    EXT["arXiv retrieval (optional)"]
  end
  subgraph Data
    PG[("PostgreSQL 16 + pgvector")]
    FS[("Upload volume")]
  end
  SPA -- "HTTPS /api (Bearer JWT)" --> API
  API --> AUTHZ --> SVC
  API --> BG --> SVC
  SVC --> PG
  SVC --> FS
  SVC --> EMB
  SVC --> ENG --> LLM
  ENG --> EXT
  SVC --> MATCH
```

* The frontend never sees API keys; all AI calls happen server-side.
* `ai_engine` has no web-framework dependency and is unit-tested on its own.
* Vector search runs inside PostgreSQL via pgvector (`<=>` cosine distance); on SQLite (dev/tests) an exact in-process cosine search with identical semantics is used.

## 2. AI evaluation workflow

```mermaid
flowchart TD
  A["Creator submits idea"] --> B["Evaluation row created (queued)"]
  B --> C["1 Understanding: build canonical idea text"]
  C --> D["2 Embedding: text → 384-d vector, stored on the idea"]
  D --> E["3 Retrieval (pgvector cosine)"]
  E --> E1["curated reference projects (70 real products/projects)"]
  E --> E2["platform ideas: public + restricted only<br/>(private never searched)"]
  E --> E3["arXiv papers (optional)"]
  E1 & E2 & E3 --> F{"LLM configured?"}
  F -- yes --> G["4a LLM gets idea + retrieved evidence only<br/>(hidden ideas excluded) → JSON"]
  F -- no --> H["4b Local rule-based DEMO engine"]
  G -- "error / invalid JSON" --> H
  G --> I["5 Validate & sanitise<br/>• similar projects ONLY from retrieved items<br/>• similarity % = computed cosine<br/>• unknown ids dropped, scores clamped 0-100"]
  H --> I
  I --> J["Persist report + similarity rows<br/>mode = live_llm | demo (labelled)"]
  J --> K["Notify creator; UI polls progress"]
```

## 3. Entity-relationship diagram

```mermaid
erDiagram
  USERS ||--o| CREATOR_PROFILES : has
  USERS ||--o| ENTREPRENEUR_PROFILES : has
  USERS ||--o{ IDEAS : creates
  IDEAS ||--o{ IDEA_DOCUMENTS : has
  IDEAS ||--o{ EVALUATIONS : "evaluated by"
  EVALUATIONS ||--o{ SIMILARITY_RESULTS : produces
  USERS ||--o{ SAVED_IDEAS : saves
  IDEAS ||--o{ SAVED_IDEAS : "saved as"
  IDEAS ||--o{ COLLABORATION_REQUESTS : receives
  USERS ||--o{ COLLABORATION_REQUESTS : "sends / receives"
  USERS ||--o{ MESSAGES : "sends / receives"
  USERS ||--o{ NOTIFICATIONS : gets
  USERS ||--o{ ADMIN_ACTIVITY_LOGS : performs
  IDEAS ||--o{ CONTENT_REPORTS : "reported in"
  USERS ||--o{ CONTENT_REPORTS : files
  USERS {int id PK string email UK string role bool is_active bool is_verified}
  ENTREPRENEUR_PROFILES {int user_id FK json industries json technologies text interests json preferred_stages int investment_min int investment_max vector embedding}
  IDEAS {int id PK int creator_id FK string title text problem text solution string industry json technologies string stage string visibility string moderation_status vector embedding}
  EVALUATIONS {int id PK int idea_id FK int version string status string mode json report int overall_score}
  SIMILARITY_RESULTS {int id PK int evaluation_id FK string source_type string source_ref float similarity bool is_competitor}
  REFERENCE_PROJECTS {int id PK string slug UK string name text description string url vector embedding}
  CATEGORIES {int id PK string name string kind bool is_active}
```

`REFERENCE_PROJECTS` (curated corpus) and `CATEGORIES` are standalone lookup tables.

## 4. Access control model

| Visibility | Anonymous | Other creators | Entrepreneurs | Owner / Admin |
|---|---|---|---|---|
| public | teaser + scores | full | full | full |
| restricted | hidden (404) | teaser | teaser → **full after an accepted request** | full |
| private | hidden (404) | hidden | hidden | full |

*Teaser* = title, short description, industry, technologies, stage. Documents, the evaluation report and long-form text require **full** access. Hidden/removed-by-moderation ideas behave as private. Forbidden resources return 404 rather than 403 so existence is not revealed. All rules live in `backend/app/permissions.py`.

## 5. Design decisions & limitations

* **Embeddings.** Default `local-hash` embeddings are *lexical* (hashed stemmed words/bigrams/char-trigrams). They measure shared vocabulary, not meaning, and are labelled as such in every report. Set `EMBEDDING_PROVIDER=openai` for semantic vectors (384 dims via the `dimensions` parameter). Switching models requires *Admin → Re-embed all content*.
* **Comparison corpus.** 70 curated real projects/products (`ai_engine/data/reference_projects.json`) + platform ideas + optional arXiv. It is not the whole market; reports say so.
* **Scoring.** In live mode the LLM proposes the three sub-scores; the overall score is computed in code (35/35/30 weighting). In demo mode all scores come from transparent heuristics (`ai_engine/demo_engine.py`).
* **Documents** are stored and access-controlled but not read by the AI.
* **Background jobs** use FastAPI `BackgroundTasks` (in-process). For production scale replace with a queue (Celery/RQ/Arq) – the pipeline entry point `run_evaluation(evaluation_id)` is already queue-friendly.
* **Search & matching at scale.** Explore filters on technology/semantic ranking and recommendations run in Python over at most 1000/300 candidate rows. Fine for thousands of ideas; move to SQL/pgvector queries beyond that.
* **Rate limiting** is limited to an in-memory login throttle; use a gateway or Redis-based limiter in production.
* **Token storage.** The SPA keeps the JWT in `localStorage` (simple, XSS-sensitive). For stricter deployments move to httpOnly cookies + CSRF protection.
