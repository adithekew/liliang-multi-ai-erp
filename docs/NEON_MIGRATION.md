# Neon PostgreSQL — ERP Multi-AI PT Liliang (Pilot)

**Scope:** only synthetic data until written company authorization, privacy review and private repository. Free-tier offerings can change. No production go-live implied.

## Status
- `app.py` now accepts `DATABASE_URL` and selects PostgreSQL via psycopg3.
- If `DATABASE_URL` is absent, existing SQLite pilot continues (ephemeral).
- On first start against an **empty** PostgreSQL database, seven tables are initialized.
- Seed data comprises only five dummy flavor SKUs and an Admin account. Existing SQLite records are **not migrated automatically**.
- This is a pilot bootstrap, **not a versioned production migration system**; add Alembic before real business rollout.

## Step-by-step using Neon Free
1. Connect Neon to ChatGPT or sign in at Neon and create a Free project named `liliang-erp-pilot`. Choose the region closest to Singapore if available.
2. Locate the PostgreSQL connection URI on Neon. Never paste the URI/password in chat, a GitHub commit, or screenshots.
3. In Render > `liliang-multi-ai-erp-pilot` > Environment, add `DATABASE_URL` with the entire Neon `postgresql://...` connection URI. Keep `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SECRET_KEY`, and `APP_ENV=pilot`.
4. Use Save, rebuild, and deploy. Do **not** delete `DATABASE_PATH`: it acts as fallback when `DATABASE_URL` is not configured.
5. Confirm `GET /readyz` returns `{"ready":true,"database_backend":"postgresql"}`.
6. Confirm `GET /healthz` returns `persistent_database:true`. This describes the backend only, not backup or production readiness.
7. Log in with your current Admin environment credentials. For a clean database, the bootstrap creates the Admin user anew.
8. Create **dummy** inquiry and a demo user; redeploy Render and confirm they still exist.
9. If deployment fails, examine Render application logs; remove only the `DATABASE_URL` value to fall back to disposable SQLite while investigating.

## Data safety
- Keep repository **Private** before any real enterprise data is used.
- Render service remains accessible publicly via its URL; authenticated RBAC still needs security testing and rate limits.
- Never put customer requirements, commercial prices, sales orders or technical datasheets into this demo until explicit approval.
- Neon Free and Render Free have quotas and no business-grade availability guarantee.
- Test recovery and retention separately before claiming production readiness.
- Raw SQL uses placeholders; do not build ad hoc SQL from user input.

## Schema
`users` (auth) -> `inquiries` -> `runs` -> `candidates` -> `reviews`.
`products` supports master SKUs; `audits` records workflow events. All demo tables remain separated conceptually from research datasets.

## Next engineering milestones
- Version-controlled schema migrations (Alembic); add constraints/indexes and role-scoped audit access.
- Durable object storage for datasheets and evidence provenance.
- Add pgvector vectors for licensed product text, with model/index version snapshots.
- Build secure ETL for sales transaction baskets and SKU-week marts with point-in-time splits.
- Compare BM25, dense-only, hybrid RRF, and constraint/UNKNOWN guardrails on expert-labelled inquiries.
