# PT Liliang — ERP Multi-AI Cloud Pilot

Research development cloud demo for five internal roles: Admin, Sales, Technical, Manager Operasional, Gudang.

> **PILOT ONLY — no real customer information.** Render Free uses ephemeral SQLite at /tmp. Data can be lost on restart, redeploy, or spin-down. Do not use the pilot for production.

## Features
- Admin bootstrap, login, Argon2 password hashes, JWT auth, RBAC and five roles.
- Synthetic Flavor SKU catalog; inventory update API for Gudang.
- Sales inquiry, lexical Top-5 matching baseline, expert Technical review (relevance 0–3), Manager approval.
- Basic audit events, OpenAPI at /docs, /healthz and /readyz.
- This is **NOT** hybrid semantic AI. No embeddings/BM25, verified datasheet grounding, AI forecasting, or SKU bundling have been implemented on this cloud branch. Source package v0.1 and research plan are maintained separately.

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env
# Export the values from .env in your shell, replacing secret placeholders
uvicorn app:app --reload
```

## Render Free
Connect repository to Render using Python runtime, Build Command: `pip install -r requirements.txt`, Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`. Required environment: `ADMIN_EMAIL`, `ADMIN_PASSWORD` (min 12 chars), `SECRET_KEY` (min 32 chars), `APP_ENV=pilot`. Only use synthetic data.

## Production blockers
1. Persistent PostgreSQL + migrations; isolate demo and business data.
2. Implement and validate hybrid BM25 + embedding retrieval with evidence/provenance and UNKNOWN guardrail.
3. Add rate limiting, operational monitoring, backups, audit retention, HTTPS and MFA/SSO as appropriate.
4. Establish company data release authorization and UAT.
5. Move private data into private GitHub repository and secured managed cloud.

No auto-sell or auto-replenishment. AI is advisory and Technical reviews remain mandatory.
