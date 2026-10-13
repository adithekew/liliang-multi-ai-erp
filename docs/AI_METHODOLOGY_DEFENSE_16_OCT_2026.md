# AI Research Evidence Pack — PT Liliang ERP Multi-AI
**Persiapan paparan 16 Oktober 2026 | Magister Teknik Informatika — Universitas Pradita**

Status: **Pilot v0.5**, bukan paper dengan hasil akhir. Studi utama: **AI-Assisted Semantic Product Matching for B2B Flavor Inquiry Management Using Hybrid Retrieval and Expert-in-the-Loop Validation**. AI-03 bundling dan AI-04 forecasting bersifat pendukung dan belum menggunakan histori penjualan perusahaan.

## Executive response to lecturer questions

### Q1 — How can we know whether AI is accurate?
**Current answer:** We cannot yet assert accuracy. The existing BM25 output is a ranking score; the five candidates have not yet received Technical 0–3 judgments. Neural cosine and RRF scores are likewise **not probabilities**. Initial Neon pilot had one inquiry, one matching run, five candidates, zero expert reviews at the time of audit.

**Proposed procedure:** Establish a gold-standard inquiry × SKU relevance set with Technical experts (0–3). Label every candidate in the evaluation pool; unknown/unjudged is **not** automatically 0. Two experts review a stratified subset independently (target 20–30%, subject to availability) and adjudicate disagreements. Report inter-rater agreement (weighted Cohen's kappa for two raters or Krippendorff's alpha as applicable). Split by project/customer/time; lock the held-out test set before tuning.

Primary metrics:
- nDCG@5: measures ranking quality using relevance grades 0–3; report mean over held-out inquiries with bootstrap confidence intervals.
- MRR@5: reciprocal rank of first useful result, **label >= 2**.
- Recall@5: useful only with a sufficiently large SKU corpus and known relevant set; with five demo SKUs and Top-5 it is trivially saturated.
- P50/P95 end-to-end latency including query encoding, retrieval, fusion and reranking; omit offline generator time from online latency claims only when disclosed.
- Manual versus AI-assisted completion time, expert decision quality and confidence intervals; target of 2+ hours to seconds remains a hypothesis, not a result.

Paired evaluation on the **same** test queries: lexical BM25, pretrained dense-only, Hybrid RRF, and Hybrid + evidence-aware reranking. The real measured win/loss will determine the final paper claims.

### Q2 — How is the AI trained?
**Current:** Encoder \`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2\` is **pretrained upstream** and has produced 384-dimensional real neural embeddings in an offline GitHub Actions run. The original release revision is recorded in \`research/fixtures/neural_synthetic_v1.json\`. **No weights have been fine-tuned on company data.** A fixed-query neural demonstration covers five synthetic SKUs and ten researcher-authored example inquiries. Free-text live ERP inquiry still runs lexical BM25 only.

**Proposed optional domain fine-tuning:**
1. Obtain authorized, anonymized inquiry × SKU records with domain-specific Technical relevance labels and attached verifiable document references.
2. Freeze source snapshot, source lineage, dates and assessor provenance; exclude personal/customer identifiers.
3. Group/time-aware train/dev/locked-test split; validate no overlap of paraphrases/products/projects which could leak labels.
4. Start from pretrained MiniLM (frozen baseline). Compare against BM25-only and pretrained dense-only *before* any tuning.
5. Fine-tune a separate encoder on approved positive inquiry–document pairs using \`SentenceTransformerTrainer\`, \`MultipleNegativesRankingLoss\`, \`BatchSamplers.NO_DUPLICATES\`. Identify false negatives (two distinct SKUs can be equally relevant). Use development split for model choice and stop criterion.
6. Log seed, loss, epochs, learning rate, device, source hash, tokenizer/model commit, training duration. Store checkpoint privately; **do not publish weights trained on private product descriptions without authorization**.
7. Compare on locked held-out expert judgments and a representative UAT. Deploy only if better and operational constraints are satisfied.

Runnable **offline-only training recipe**: \`research/finetune_encoder.py\`, dependencies \`requirements-ai-train-local.txt\`. The gate \`research/training_gate.py\` deliberately rejects the current five-SKU demonstration and checks for 50+ consented positive training pairs, 10+ dev pairs, 20+ distinct training SKUs and 10+ train groups. These are **conservative software readiness minimums, not statistical sufficiency or guarantees of SINTA 2 acceptance**. Neither the training recipe nor the demo proves that a domain model is trained.

### Q3 — How is the dataset cleansed?
The dataset needs at least two independently governed pipelines.

**Retrieval/inquiry corpus:**
- Intake with permission, de-identification review and source tracking;
- Schema validity: nonempty SKU/name/profile/application, raw inquiry text, source ID and event timestamp;
- Quarantine indications of personal data, commercial material without authorization and unauthorized provenance;
- Unicode NFKC, whitespace, case folding, Indonesian/English domain terminology and canonical flavor taxonomy (preserve original in access-controlled raw zone);
- Correct inconsistent SKU aliases; detect duplicate canonical SKUs, duplicate normalized inquiries and near duplicates for human review;
- Missing halal/regulatory values remain **UNKNOWN**, never imputed as certified;
- Normalize application, flavor family, sweetness, sensory descriptors, regulatory constraints only when evidence allows;
- Annotate relevance pairs with Technical experts, version annotations and disagreements;
- Partition by project/customer/time, avoiding split contamination; register corpus/model/index versions.

**Sales history for AI-03 and AI-04 (secondary):**
- Validate transaction/order identifiers, SKU crosswalk, date/time zone, units/quantity/currency, cancellations, returns, corrections and duplicates;
- Handle stockouts, promotions, order splits and temporal leakage;
- Build order baskets for association rules and SKU-week mart for forecasting; preserve event-time cutoffs, price/promotional features, missing periods, and no future features in training;
- Evaluate bundling separately (precision@K, incremental business outcomes if measured) and forecasting separately using time-series backtesting (MAE, wMAPE with stated denominators), never borrow semantic retrieval accuracy metrics.

Executable baseline cleansing: \`research/data_pipeline.py\` with quarantine reasons, source classification restrictions and temporal/project grouped split. It does **not** promise automatic legal anonymization. Current synthetic quality sample is not a measure of PT Liliang's actual data cleanliness.

### Q4 — What ML methods, and what advantages?
| Component | Nature | Business role | Strength | Limitation |
|---|---|---|---|---|
| Rule-based NLP + bilingual taxonomy | deterministic feature extraction | interprets flavor and application | explainable for controlled terms | misses implicit meanings and novel terms |
| BM25 with field-specific boosts | lexical information retrieval, **not a trained neural ML model** | fast candidate retrieval | exact SKU/technical terms | weak for paraphrases |
| MiniLM SentenceTransformer (SBERT family) | **pretrained neural ML bi-encoder**, 384 dimensions | retrieves by semantic similarity | handles paraphrase/multilingual similarities | domain shifts, hallucinated sense of similarity, uncalibrated cosine |
| Cosine similarity | vector similarity | sorts dense vector neighbors | normalized continuous similarity | not probability of product suitability |
| Reciprocal Rank Fusion k=60 | non-trained rank aggregation | combines lexical and dense rankings | robust to incomparable score scales | not automatically optimal on every dataset |
| Evidence-aware constraint reranking | deterministic business safety | flags mismatch / UNKNOWN | discourages unsupported compliance claims | requires authoritative datasheets |
| Fine-tuned bi-encoder (future) | supervised domain adaptation | improve B2B flavor matching | potential domain-specific gains | needs labels, splits, training resources, evaluation |
| Association rule analysis AI-03 | statistical pattern mining | optional bundle recommendations | support/confidence/lift interpretable | co-purchase ≠ causality |
| Moving average AI-04 | forecasting baseline | demand planning comparator | low-cost interpretable | may fail on promotions, trend, irregular data |

Do not call *all four modules deep-learning AI*. The research contribution is a **testable human-governed hybrid information-retrieval architecture**, and any superiority remains to be established empirically.

## Data requirements and who supplies them
1. Product master: SKU, internal descriptions, sensory attributes, application, technical evidence pointer, effective date and statuses; company-approved for research.
2. Inquiry history: anonymized natural-language need, event time, safe project grouping, eventual technical recommendation. No customer names, phones or PII.
3. Expert labels: inquiry × SKU, 0–3 relevance, Technical reviewer (pseudonymized), timestamp, evidence pointer, disagreements/adjudication.
4. Sales/order history for secondary modules: anonymized orders, dates, SKU, quantity, cancellations, returns and optional stockout/promotion indicators.

A practical first annotation **target to plan for** is dozens to hundreds of diverse historical inquiries and five judged candidate pairs per inquiry. Final sample size must reflect accessible data, number of SKUs, label coverage, and statistical precision; never invent that the target has been achieved.

## Experimental plan E1–E5 and research questions
- **E1 — Cleansing & annotation validity:** count valid/quarantined/deduplicated records, missing-evidence rates and Technical inter-rater agreement.
- **E2 — Baseline retrieval:** BM25 versus pretrained dense-only on identical held-out inquiries.
- **E3 — Hybrid retrieval:** BM25 + dense via RRF, with dev-only tuning and test-only reporting.
- **E4 — Evidence-aware reranking:** constraint-aware ablation, UNKNOWN behavior and errors of unsafe suitability claims.
- **E5 — Human-in-the-loop efficiency:** expert acceptance/adjudication, retrieval and review latency, time-to-shortlist compared with manual workflow.

Proposed RQs:
- RQ1: How effectively can bilingual flavor inquiries be interpreted and matched to a technical product catalog?
- RQ2: Does BM25 + multilingual dense RRF improve relevance ranking over single retrievers on held-out expert judgments?
- RQ3: How do provenance and evidence-aware constraints influence recommendation safety and expert acceptance?
- RQ4: Does AI-assisted shortlist plus Technical review improve time-to-shortlist against documented manual search?

## Presentation plan, 16 October 2026
1. Real PT Liliang problem and current manual inquiry flow; research hypothesis not achievement.
2. Five-role ERP and four AI capabilities; primary vs secondary.
3. Architecture: React-like browser UI / FastAPI / Neon PostgreSQL / offline embedding process / Technical decision loop.
4. AI-01/AI-02 pipeline: normalization → BM25 + multilingual MiniLM → RRF → evidence-aware ranking → Technical.
5. Dataset governance: sources, anonymization, QA, canonical SKU, UNKNOWN, leakage avoidance.
6. Training status: pretrained now, fine-tuning gated on expert labels later, no company-trained model yet.
7. Evaluation design: rubric 0–3, nDCG@5/MRR@5, P95, manual comparison; experimental matrix.
8. Demonstration v0.5 Research Evidence dashboard: **0 expert labels means 0 credible accuracy claims**.
9. Limits (5 dummy SKUs, 10 fixed synthetic queries, Render Free resource constraints, private data approval).
10. E1–E5 timeline, expert annotation request and lecturer sign-off questions.

## Core literature
- Reimers, N. and Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.* ACL Anthology, DOI: [10.18653/v1/D19-1410](https://doi.org/10.18653/v1/D19-1410).
- Cormack, G. V., Clarke, C. L. A., and Büttcher, S. (2009). *Reciprocal rank fusion outperforms Condorcet and individual rank learning methods.* SIGIR, DOI: [10.1145/1571941.1572114](https://doi.org/10.1145/1571941.1572114).
- Sentence Transformers official [Training Overview](https://www.sbert.net/docs/sentence_transformer/training_overview.html) and [Loss Overview](https://www.sbert.net/docs/sentence_transformer/loss_overview.html).
