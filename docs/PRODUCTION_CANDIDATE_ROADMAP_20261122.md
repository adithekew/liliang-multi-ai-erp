# Production-Candidate ERP Multi-AI Roadmap

Status date: 2026-11-22
Baseline: main `fe7c266ad0fa1bddf8ef14c2686cbbbafe44f574`
Implementation branch: `feat/erp-multi-ai-production-roadmap-20261122`

## Release objective

Move the current research pilot toward a production candidate while preserving the existing main branch and all company records. This roadmap is a gated engineering plan; it is not a claim that models are trained, validated, or production-ready.

## Verified baseline

- The repository is public. Never commit company source data, customer inquiries, invoices, datasheets, credentials, embeddings derived from private records, or private model weights.
- Current deploy configuration targets Render Free. Persistent PostgreSQL is supported through `DATABASE_URL`; SQLite fallback is ephemeral on the pilot host.
- AI-01 is a deterministic bilingual rule-based interpreter, not a trained model.
- Operational AI-02 uses BM25. The 384-dimensional multilingual MiniLM/RRF implementation is an offline fixture for 10 synthetic inquiries and 5 synthetic products, not arbitrary live-query inference over the company catalog.
- AI-03 demo data consists of synthetic baskets. A company-attested order-facts import and association endpoint exist, but company data must be Finance-reconciled before scientific claims.
- AI-04 demo data consists of synthetic SKU-week series. A company-attested moving-average endpoint and an offline ridge training experiment exist; company-specific validation is not established.
- Agent Orchestrator uses fixed synthetic tool outputs and optional Groq. Inquiry Advisor is a separate local, read-only, deterministic advisory service.
- WMS routes and sample dispatch are explicitly UAT-only. They do not mutate physical company inventory.
- Existing governance docs require independent Technical review, Finance reconciliation, authorization, and held-out evaluation before promotion.

## Workstreams

### 0. Governance and privacy
- Keep the public repository free of private company data and artifacts.
- Obtain written data-use approval and specify purpose, data scope, retention, location, access, and any third-party processing.
- Use private storage and restricted compute for real datasets, embeddings, and weights.
- Keep production release, model promotion, and stock mutation behind human approval gates.

### 1. AI-02 live neural retrieval
- Use a pinned multilingual encoder for arbitrary inquiry text at inference time.
- Generate versioned embeddings for every active catalog SKU, including approved descriptions, profile, application, and evidence references.
- Keep vector index private and rebuildable; add incremental updates, stale-index detection, and model/catalog version compatibility checks.
- Compare BM25, dense retrieval, and RRF on the same authorized expert-judged inquiry set.
- Preserve deterministic constraints, UNKNOWN states, abstention, and Technical review.
- Fine-tune only if the independent expert-labelled dataset meets the existing training gate; otherwise evaluate frozen pretrained embeddings honestly.

### 2. AI-03 bundling
- Accept only actual reconciled order/invoice IDs and line items.
- Define treatment of cancellations, returns, credit notes, partial shipments, duplicate lines, and SKU aliases with Finance.
- Evaluate future baskets against popularity and simple co-occurrence baselines using a temporal holdout.
- Report Precision@K/Recall@K or ranking metrics, coverage, uncertainty, and segment limitations.
- No proxy document groups or synthetic baskets in company performance claims.

### 3. AI-04 demand forecasting
- Build SKU-week series from Finance-verified quantities and explicit unit conversions.
- Require 24+ contiguous complete calendar weeks per SKU for the initial controlled experiment; do not zero-fill missing weeks.
- Compare the existing moving-average baseline with seasonal-naive and ridge/autoregressive candidates using rolling-origin backtesting.
- Report MAE, WMAPE, RMSE, bias, interval coverage, and per-SKU/horizon metrics.
- Account for stockouts, lead times, returns, partial weeks, and assortment changes before replenishment use.
- No automatic purchasing or stock adjustment.

### 4. AI Agent
- Provide one authenticated role-aware orchestrator over typed AI-01–AI-04 services.
- Default tools to read-only; validate schemas, enforce timeouts/limits, log tool calls, model/data versions, and provenance.
- Keep private company prompts and outputs inside the approved private environment unless explicit written approval authorizes an external provider.
- Agent must not approve Technical suitability, approve Manager decisions, reserve stock, dispatch goods, or mutate financial/warehouse records.
- Evaluate tool selection, correct argument use, groundedness, refusal/abstention, policy adherence, latency, and failure recovery.

### 5. Operational WMS
- Design a real ledger separate from the UAT tables: warehouse/bin, SKU, lot/batch, expiry where tracked, UoM, receipts, put-away, transfers, reservations, picks, dispatch, returns, adjustments, cycle counts, and reconciliation.
- Use append-only movements, idempotency keys, atomic stock checks, transaction locking, and audit trail.
- Do not treat the 2026-11-06 user-attested stock snapshot as a current opening balance. Require a dated warehouse stock count and reconciliation before go-live.
- Do not invent UoM, conversion, lot, or expiry data. Block dispatch where the package UoM is unresolved.
- Keep physical and UAT stock ledgers isolated.

### 6. Model validation
- AI-01: independently labelled intent/entity test set; precision, recall, F1 and exact match by attribute/language.
- AI-02: two independent Technical reviewers, adjudication, frozen project/time split, nDCG@5, MRR@5, Recall@5, paired baseline comparison and confidence intervals.
- AI-03: temporal future-basket test, ranking/association metrics, coverage and popularity baseline.
- AI-04: rolling-origin backtests and baseline comparisons by SKU and horizon; report uncertainty and stockout/missing-data handling.
- Agent: held-out tool-selection, tool correctness, grounding, policy and latency tests.
- If required evidence is absent, status remains NOT_READY or NOT_VALIDATED.

### 7. Platform and production readiness
- Add versioned database migrations, tested backup/restore, rate limiting, monitoring, alerting, secrets rotation, deployment rollback and incident runbooks.
- Complete UAT for all five roles using real authorized operational scenarios.
- Complete security review and data-protection review.
- Reconcile Render health checks with `/healthz` and `/readyz`.
- Production promotion requires explicit owner, Finance, Technical, Warehouse, and security sign-off.

## External prerequisites

1. Written company authorization and approved private data-processing environment.
2. Current approved catalog snapshot and product technical evidence.
3. Authorized, de-identified free-text inquiries and independent Technical labels.
4. Finance-reconciled order/invoice line items, dates, statuses, returns, quantities, unit conversions, and weekly series.
5. Warehouse-approved current stock count, warehouse/bin structure, lot/expiry scope, package mappings, and UoM definitions.
6. Decision on inference/training compute and approved model-serving location. Render Free must not be assumed to support neural model inference/training at production scale.

## Implementation sequence

1. Protect and baseline the current system; add architecture and release gates.
2. Build and test private catalog embedding/index and arbitrary-query inference.
3. Build reproducible AI-03 and AI-04 company-data evaluation pipelines.
4. Integrate local/private role-aware Agent orchestration.
5. Implement operational WMS ledger and reconciliation workflows.
6. Execute all model validations on frozen, approved datasets.
7. Complete security, backup/restore, CI/CD, five-role UAT, and release sign-off.

## Delivery rules

- Work on the dedicated implementation branch and submit reviewable pull requests.
- Never write directly to `main` for this program.
- Never merge, deploy, change secrets, switch repository visibility, import company data, or mutate physical stock without explicit owner/operator approval.
- Tests and CI must use isolated fixtures; real company datasets and weights stay private.
- Do not claim success from code presence alone. Record the actual test run, dataset provenance, metrics, approvals, and deployment revision.
