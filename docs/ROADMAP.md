# Roadmap (iterative and incremental)

| # | Scope | Status |
|---|-------|--------|
| 1 | Foundation, settings split, custom user + roles, academic models, registration/login/profile, course selection, tests | **Done** |
| 2 | Document upload + validation (extension, MIME, signature, size), private storage, ClamAV hook, moderation queue | Next |
| 3 | Video links (YouTube), discovery, search/filter/sort, authorized downloads | |
| 4 | Content-based recommendations (configurable weights), bookmarks, ratings, reviews, notifications | |
| 5 | Admin dashboard and analytics, reports, audit log, security hardening | |
| 6 | Full test pass on PostgreSQL, deployment, report chapters, demo | |

Each increment must end with working, tested functionality before the next begins.
Scoping advice: if time runs short, drop reviews and the analytics charts first; keep moderation,
search, and recommendations.
