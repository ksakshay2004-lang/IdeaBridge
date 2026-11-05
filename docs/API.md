# IdeaBridge REST API

Base URL `/api`. Interactive OpenAPI docs: `http://localhost:8000/docs` (Swagger) and `/redoc`.
Auth: `Authorization: Bearer <JWT>` from `/auth/login`. Errors: `{"detail": "..."}` (422 returns a field list).

| Method & path | Auth | Description |
|---|---|---|
| **Auth** | | |
| POST `/auth/register` | – | Create creator/entrepreneur account → token + user |
| POST `/auth/login` | – | JSON `{email,password}` → token (throttled after repeated failures) |
| POST `/auth/token` | – | OAuth2 form login (Swagger "Authorize") |
| GET `/auth/me` | any | Current user |
| POST `/auth/change-password` | any | |
| **Profiles** | | |
| GET `/profile/me` | any | User + role-specific profile |
| PUT `/profile/me/creator` | creator | Update creator profile |
| PUT `/profile/me/entrepreneur` | entrepreneur | Update company profile (re-embeds interests) |
| GET `/entrepreneurs/{id}` | any | Public company card |
| **Ideas** | | |
| GET `/ideas` | optional | Explore. Query: `q, industry, technology, stage, sort=newest\|score, semantic=true, page, page_size` |
| GET `/ideas/featured` | – | Top public ideas for the landing page |
| GET `/ideas/mine` | creator | Own ideas with evaluation status and pending requests |
| POST `/ideas` | creator | Create → starts AI evaluation (background) |
| GET `/ideas/{id}` | optional | Full or teaser view (`access` field); 404 if not permitted |
| PUT `/ideas/{id}` | owner | Edit (re-embeds if core text changed) |
| DELETE `/ideas/{id}` | owner | Delete incl. documents |
| POST `/ideas/{id}/evaluate` | owner | New evaluation run (202) |
| GET `/ideas/{id}/evaluation` | full access | `{current, latest_completed}`; owners also see in-progress runs |
| GET `/ideas/{id}/matches` | owner/admin | Best-matched entrepreneurs with explanations |
| POST `/ideas/{id}/report` | any | Report content |
| **Documents** | | |
| POST `/ideas/{id}/documents` | owner | multipart `file` (pdf, docx, pptx, png, jpg, txt; ≤ `MAX_UPLOAD_MB`; magic-byte checked) |
| GET `/documents/{id}/download` | full access | Attachment download |
| DELETE `/documents/{id}` | owner | |
| **Evaluations** | | |
| GET `/evaluations` | creator | Latest evaluation per own idea |
| GET `/evaluations/{id}` | full access | Progress polling / report |
| **Entrepreneur** | | |
| GET `/recommendations` | entrepreneur | Ideas ranked by match score + breakdown |
| GET/POST/DELETE `/saved[/{idea_id}]` | entrepreneur | Saved ideas |
| **Collaboration** | | |
| POST `/collaboration` | entrepreneur | `{idea_id, kind: collaborate\|fund\|develop, message}` |
| GET `/collaboration?status=` | any | Incoming (creator) / outgoing (entrepreneur) |
| POST `/collaboration/{id}/respond` | creator | `{action: accept\|decline, message}` – accept unlocks restricted idea |
| POST `/collaboration/{id}/withdraw` | entrepreneur | |
| **Messages & notifications** | | |
| GET `/messages/conversations` · GET `/messages/thread/{user_id}` · POST `/messages` | any | Anti-spam rules in `can_message()` |
| GET `/notifications` · GET `/notifications/unread-count` · POST `/notifications/read-all` · POST `/notifications/{id}/read` | any | |
| **Public** | | |
| GET `/categories` · GET `/stats` · GET `/system/status` · GET `/health` | – | `system/status` reports demo vs live AI |
| **Admin** (admin only) | | |
| GET `/admin/analytics` | | Totals, growth, distributions |
| GET `/admin/users` · PATCH/DELETE `/admin/users/{id}` | | Search, (de)activate, verify entrepreneurs |
| GET `/admin/ideas` · PATCH/DELETE `/admin/ideas/{id}` | | Moderate (`active\|hidden\|removed`) |
| GET `/admin/reports` · POST `/admin/reports/{id}/resolve` | | `dismiss\|hide_idea\|remove_idea` |
| GET/POST `/admin/categories` · PATCH/DELETE `/admin/categories/{id}` | | |
| GET `/admin/logs` · POST `/admin/reindex` | | Audit trail; re-embed everything |

## Evaluation report (JSON)
`meta{mode: "demo"|"live_llm", provider, model, notice}`, `idea_summary`, `problem_statement`, `proposed_solution`,
`similar_projects[{ref_id, kind, title, url, similarity_pct, key_differences, is_competitor}]`, `novelty_assessment{level, rationale}`,
`scores{technical_feasibility, market_opportunity, innovation_differentiation, overall}`, `development_complexity`, `target_users`,
`revenue_models`, `competitors`, `strengths`, `weaknesses`, `risks`, `recommended_improvements`, `overall_evaluation`, `evidence{...}`.
