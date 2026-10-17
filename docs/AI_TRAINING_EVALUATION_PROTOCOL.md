# PT. Li Liang Multi-AI — AI-02 Training and Evaluation Protocol

## Current live status (verified implementation)

- 1,452 supplier-catalog SKU records in Neon PostgreSQL, imported from company PDF, status `CATALOG-PDF-UNVERIFIED`; supplier catalog is **not** independently verified datasheet evidence.
- AI-01: bilingual rules/normalization; no trained language model.
- Operational AI-02: BM25 retrieval on currently active catalog; free-text new inquiries are **not** encoded by a neural model yet.
- Research Hybrid Lab: **genuine pretrained multilingual MiniLM 384-dimensional embeddings** previously generated offline for 10 fixed synthetic inquiries and five synthetic products. Cosine similarity + Reciprocal Rank Fusion (RRF). This is not a live company-data evaluation.
- AI-03: association rules using synthetic baskets, not company sales.
- AI-04: four-week moving-average baseline on synthetic demand, not company sales.
- No valid expert-labelled/held-out result or domain fine-tuned model exists. No accuracy percentage can be stated.

## Why a product PDF alone cannot train AI-02

Supervised query-to-product training requires **inquiry × SKU** relevance pairs. A supplier catalog without labelled historical customer requirements and independent expert judgements is a candidate corpus, not a supervised gold-standard dataset.

## Data collection contract: private, authorized, and auditable

For each training/evaluation pair, require:

1. Authorized de-identified inquiry ID and normalized customer requirement; retain permission scope and data provenance outside public GitHub.
2. Canonical supplier SKU (candidate must exist in versioned catalog).
3. Expert Technical relevance label **0, 1, 2 or 3** and independent evidence for the judgement.
4. Technical reviewer pseudonym, adjudication status, controlled timestamps and candidate generation source.
5. Grouping keys for customer/project/product family and inquiry date to prevent group/temporal leakage.
6. Missing datasheet constraints remain `UNKNOWN`, not inferred to be compliant or halal.
7. UAT users and `UAT-` customer references excluded from scientific training and evaluation.

Do not export personal data, real customer transactions, passwords or proprietary supplier documents to this public repo or general-purpose GitHub Actions artifacts.

## Data quality pipeline

1. Approval and provenance: documented company authorization, source snapshot SHA-256, field dictionary.
2. Audit and quarantine: invalid code, missing SKU, duplicate conflicting SKU, unresolvable inquiry, personal data or unverifiable provenance.
3. Normalize whitespace, Unicode NFKC, mixed Indonesian/English synonyms and SKU taxonomy; retain original text for approved private audit.
4. Join inquiry ID to candidate SKU to form labels 0–3; duplicate reviews require adjudication, not automatic averaging.
5. Produce immutable dataset versions and QA reports (accepted, quarantined, label balance, groups).
6. **Split before training** by customer/project and temporal holdout to prevent information leakage; frozen test split must never be trained against.

## Baselines and training experiments

- **E1:** BM25 only (live lexical baseline).
- **E2:** Frozen multilingual MiniLM encoder (384 dimensions), cosine ranking across the *approved* versioned catalog.
- **E3:** BM25 + dense retrieval via RRF(k=60), same held-out queries.
- **E4:** If authorized labelled corpus adequate, supervised contrastive bi-encoder fine-tuning on the **train set only**. Candidates positives from qualified labels (e.g., 3; label 2 requires validation policy), negatives sampled carefully and never from test. Example loss MultipleNegativesRankingLoss with checked false-negative collisions.
- **E5:** Constraint evidence/UNKNOWN aware post-ranking + human-in-the-loop, latency and time-to-shortlist evaluation.

Pin model revision, dataset fingerprint, seed, hyperparameters, package versions and device. Run heavy embedding/fine-tuning **offline on approved private compute**. Render Free remains API/UI for pilot; do not assume it can afford CPU-based inference across 1,452 SKU and newly supplied texts or hold sensitive cached embeddings.

## Metrics and acceptance

- Primary: **nDCG@5**, **MRR@5**, **Recall@5** where suitable and measured against a properly judged candidate pool.
- Secondary: P50/P95 ranking latency, manual vs assisted time-to-shortlist, unknown-constraint violations, reviewer agreement, and false positives.
- Same held-out inquiries across BM25, frozen dense, hybrid and fine-tuned variants; confidence intervals/paired tests.
- Report actual sample counts and uncertainty. A training score is not an out-of-sample accuracy score, and a match score is not a probability of correctness.
- Gate: no deployment of fine-tuned model until blinded expert evaluation, independence/adjudication and held-out metrics have been reviewed by supervisors and domain experts.

## Next required input from PT. Li Liang

**(1)** Written consent and data usage scope, **(2)** de-identified historical inquiry–SKU mapping or approved historical inquiry records, **(3)** relevant product datasheets and constraints with authorization, **(4)** Technical label/review plan with rubric 0–3. For AI-03 and AI-04 separately: approved historical line-item sales with SKU/date/quantities and reliable missing/returned order handling.

Use **AI Research Evidence → Training Readiness** to see the active catalog count and actual gate status. It is deliberately **not** an automatic "Train Now" button until these inputs exist.
