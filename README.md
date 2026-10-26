# PT Liliang · ERP Multi-AI Research Pilot

Five-role internal ERP research pilot: Admin, Sales, Technical, Manager Operasional, Gudang.

**Status:** Render Free research pilot, *not production*. A supplier-PDF catalog has been imported to a private Neon database but remains UNVERIFIED; AI-03/04 demonstrations are synthetic, and 2025 sales history has only been extracted pending Finance reconciliation. This public repository must never include company datasets or secrets.

## Capstone P7 — 26 Oktober 2026 (merged; route live, role UAT pending)

A new **Learning & Adoption Center** (`/learning/center`) is deployed as a *read-only UX prototype* for the Aswaya P7 rubric: five-role learning journey, skills matrix, formative browser-only 3-question quiz, draft pre/post-test, and **not-yet-measured** learning/adoption KPI definitions. It does **not** write user learning progress or change Neon, production stock, company sales data, or model weights.

- [P7 academic milestone, evidence matrix and Drive files](docs/CAPSTONE_P7_LEARNING_ADOPTION_20261026.md)
- [P7 presenter script and safe demo SOP](docs/P7_PRESENTATION_AND_DEMO_SOP_20261026.md)
- [21-slide editable deck](https://docs.google.com/presentation/d/1dDFkZJ1zdFq8EDzgLDFdnCMrW3d5ughA/edit)
- [P7 class submission folder](https://drive.google.com/drive/folders/1gbiNBG8ejF-LTObMGJg9-kmQ30GVWrRx)

**Scientific gate unchanged:** PR #22–25 have been merged for source governance and independent AI-02 evaluation infrastructure. June 2025 is excluded from company sales experiments, user-assumed proxy baskets are not invoice-validated orders, and no independently judged company model accuracy has been produced. [PR #26](https://github.com/adithekew/liliang-multi-ai-erp/pull/26) merged with green CI; Render `/learning/center` was independently reachable on 26 Oct 2026. Authenticated five-role UAT remains pending.

## Capstone Weekly Update — 23 Oktober 2026

Materi paparan IT40513 untuk Kelompok 3 (22 slide) dan bukti kegiatan 16–23 Oktober 2026 sudah disiapkan dalam [**laporan mingguan + tautan pengumpulan Google Drive**](docs/CAPSTONE_WEEKLY_UPDATE_2026-10-23.md).

- [PPTX asli (editable)](https://docs.google.com/presentation/d/1n0TulHPVLWHUBMm-gmALBJEQCoIUE2VR/edit) dan [PDF asli](https://drive.google.com/file/d/1qDwD0oGrw8mgf_-JT1KLcU00NQ4sRSBM/view)
- [Google Slides 22 slide yang dapat diedit online](https://docs.google.com/presentation/d/1sao9LQOE8YcBKOpIp60idlk0qL2SR2vWuB6BBT9j8Zs/edit)
- [Panduan presenter](https://drive.google.com/file/d/1ug2j7r1pQ1i943TYPfuYMroyv0CNg3vI/view) dan [catatan pembicara](https://docs.google.com/document/d/1hGOjirRWTnCoQe9Y9Z7kfDCMfxVGgbTiGShFSZdFW-o/edit)

**Status akademik:** UAT operasional dan CI telah menghasilkan bukti fungsional. MiniLM belum menjalankan inferensi online pada katalog penuh; AI-03/04 masih sintetis; data sales 2025 telah diekstraksi tetapi perlu rekonsiliasi; tidak ada klaim presisi AI yang tervalidasi.

## v0.5 — Research evidence, data quality and supervised-training readiness

- **Research Evidence** page (Admin / Technical / Manager) displays real Technical label coverage, 0–3 expert rubric, synthetic dataset cleaning QA, comparative readiness gates and training status. With no gold-standard labels, the page explicitly reports **no validated accuracy**.
- Read-only endpoints: \`GET /v1/research/methodology\`, \`GET /v1/research/readiness\`, \`GET /v1/research/evaluation\`, \`GET /v1/research/quality-demo\`.
- Research lab computes exploratory nDCG@5 and MRR@5 **only** for complete, consistent expert-labeled candidate sets. MRR considers grades 2–3 relevant. It does not make held-out or generalizability claims.
- Research data cleansing includes schema checks, SKU canonicalization, Indonesian/English alias normalization, duplicate controls, PII quarantine and anti-leakage group/time splitting. It defaults to **synthetic/approved-only** records.
- Optional offline supervised domain adaptation: \`research/training_gate.py\` and \`research/finetune_encoder.py\` require authorized, anonymized Technical-labelled pairs, enough examples and group diversity, and local written permission. **No PT Liliang data has been fine-tuned.** Training code does not run automatically.
- Lecturer-response / defense handout: [AI Methodology Defense — 16 October 2026](docs/AI_METHODOLOGY_DEFENSE_16_OCT_2026.md).
- None of these additions modify the existing Neon ERP schema or create/overwrite company records.

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
