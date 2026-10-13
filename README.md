# PT Liliang · ERP Multi-AI Research Pilot

Five-role internal ERP research pilot: Admin, Sales, Technical, Manager Operasional, Gudang.

**Status:** Render Free demo, *not production*. Synthetic product and sales history only. Repo is currently public; no company data or secrets belong here.

## v0.4 — Real multilingual neural embedding demonstration

The new **Hybrid Semantic Lab** runs a genuine pretrained multilingual Sentence Transformers model **offline** on 5 synthetic flavor SKUs and 10 illustrative inquiries, records normalized 384-dimensional vectors, and compares BM25 / dense cosine / RRF (k=60) in Render Free **without hosting the heavyweight encoder**. The browser only evaluates pre-embedded synthetic cases: arbitrary user-entered ERP inquiries still use BM25 and are not passed to an online neural model.

- Research methodology: [docs/HYBRID_SEMANTIC_RESEARCH.md](docs/HYBRID_SEMANTIC_RESEARCH.md)
- Fixed neural assets: [research/fixtures/neural_synthetic_v1.json](research/fixtures/neural_synthetic_v1.json)
- Reproducible generator: [scripts/generate_neural_fixtures.py](scripts/generate_neural_fixtures.py)
- Expert-ready metrics: `research/metrics.py` (nDCG@K and MRR, requiring complete relevance judgments)
- API: `GET /v1/ai/hybrid-cases`; `GET /v1/ai/hybrid-evaluate?case_id=Q01`
- Research limitations: developer-authored labels are **not** expert ground truth, latency excludes offline inference, datasheet evidence and halal/regulatory attributes remain `UNKNOWN`, **no production AI claims**.

## v0.3 capabilities
- ERP: session-based browser JWT login, RBAC, inquiry → BM25 Top-5 → Technical review → Manager approval; Admin user creation, audit events.
- AI-01: deterministic Indonesian/English requirement extraction (baseline).
- AI-02: BM25 lexical ranking (baseline). Not yet deployed as a real neural hybrid service.
- AI-03: association-rule bundling from 16 synthetic baskets (demo).
- AI-04: 4-week moving average forecast from 24 synthetic SKU-weeks (demo).
- Optional Neon PostgreSQL persistence via `DATABASE_URL`. SQLite fallback for standalone demos.
- Offline research: `research/hybrid.py` implements RRF fusion and evidence-aware UNKNOWN checks; `scripts/semantic_poc.py` downloads a multilingual neural model and computes embeddings *locally*.

## Run locally
Install Python 3.12, then:

```bash
python -m venv .venv
pip install -r requirements.txt
# Set ADMIN_EMAIL, ADMIN_PASSWORD (>11 characters), SECRET_KEY (>=32 characters)
# APP_ENV=pilot, DATABASE_PATH=./liliang-local.db
uvicorn app:app --reload
```

### Optional research experiment with real neural embeddings
```bash
pip install -r requirements-ai-local.txt
python scripts/semantic_poc.py
```
The sentence-transformers model may download substantial files to the local machine. No academic performance claims follow from this toy demonstration. Use expert-labelled inquiry-product judgments (0–3), agreed train/dev/test splits and reproducible index/model versions before evaluation.

## Connect Neon PostgreSQL Free
Follow **[docs/NEON_MIGRATION.md](docs/NEON_MIGRATION.md)**. The database is only persistent **after** a valid PostgreSQL connection URI is configured in Render and verified via `/readyz`. Do not submit a connection URI or secrets via chat/GitHub.

The first successful PostgreSQL boot seeds five dummy products and an Admin; it does **not** copy data out of temporary SQLite.

## Cloud
- Render: [liliang-multi-ai-erp-pilot.onrender.com](https://liliang-multi-ai-erp-pilot.onrender.com)
- API health: `/healthz` and `/readyz`
- OpenAPI: `/docs`
- Python 3.12, `uvicorn app:app --host 0.0.0.0 --port $PORT`

## Research boundary
Core publication: AI-assisted Semantic Product Matching for B2B Flavor Inquiries, with expert validation and provenance; E1–E5 and RQ1–RQ4 remain fixed. No auto-sell or auto-replenishment. The ERP provides workflow context, and the AI recommendation does not become a business decision until Technical validation.

## Production blockers
Before real company deployment: private repo, authorization and data minimization, PostgreSQL migrations and backup/restore tests, transactional integrity, audit constraints, secrets rotation, rate limiting, HTTPS, secure file storage, UAT, operational monitoring and error budgets.
