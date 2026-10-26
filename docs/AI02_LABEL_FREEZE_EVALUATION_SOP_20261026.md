# AI-02 — Independent Technical Labelling → Frozen Dataset → Offline Training & Evaluation

**26 October 2026 | PT. Liliang ERP Multi-AI | Research / private data SOP**

## Current factual status

- The two existing Technical workbooks (TECHNICAL_A and TECHNICAL_B) have **zero completed pair IDs or expert grades** at the time of this update. They are structured empty templates, not independent annotations.
- ERP Neon holds prior Technical review transactions for functional UAT. Those reviews **must not** be promoted into research gold labels or company-specific model weights.
- The business-relevance model in the app remains **online BM25**, while the MiniLM + RRF assets are only an offline fixed synthetic experiment.
- June 2025 remains excluded from AI-03 proxy association and monthly AI-04 exploratory work. Grouped sales lists remain proxy basket assumptions, not verified invoice IDs.
- Warehouse stock remains UNKNOWN until physical count.

## Technical review workflow — both experts receive the same LOCKED pool

1. The research coordinator obtains company data-use authorization and a pseudonymous inquiry set from Sales. Remove customer names, emails, contact numbers, personal/project secrets and commercially confidential free text.
2. Obtain permitted product descriptors and official datasheet references. Match normalized catalogue SKUs and freeze a candidate pool with `pair_id`, inquiry ID, SKU, project group and permitted query/document texts. Do **not** create fictional customer inquiries or fill 0–3 grades automatically.
3. Write a private `task_pool.jsonl` with one object per candidate:

```json
{"pair_id":"PAIR-001","inquiry_id":"AUTH-INQ-001","project_group":"GROUP-001","query":"[authorized anonymized customer requirement]","document":"[authorized technical product descriptor]","sku":"[verified catalog SKU]","authorization_ref":"DATA-APPROVAL-REFERENCE","data_classification":"AUTHORIZED_ANONYMIZED","expert_validated":true}
```

The shown values are *schema placeholders*, not an actual authorized customer example. `expert_validated:true` is entered **only after** the coordinator has verified the source and approved the task pool. This flag is an attestation, not proof of genuine legal permission.

4. Copy `pair_id`, `inquiry_id`, `project_group`, `query_anonymized`, `sku`, and `product_form` from this same locked pool into both supplied workbooks' **PENILAIAN** sheet. **Neither reviewer may change the task identities.**
5. Technical A and Technical B work independently and complete `datasheet_reference`, `label_0_3`, and substantive `rationale` (10+ characters). Neither reviewer sees the other person's answers beforehand.
6. Save each `PENILAIAN` sheet as CSV UTF-8 with the original snake_case headers. The newer forms named `PT_Liliang_Independent_Label_TECHNICAL_A/B.xlsx` use these headers; older Indonesian-labelled templates require a column-map conversion.
7. Compare reviews. The offline tool uses quadratic weighted Cohen's kappa and lists pair IDs with disagreements; these must be resolved by a third independent human or a documented adjudication panel.

**Adjudication CSV columns:** `pair_id,adjudicator_id,datasheet_reference,label_0_3,rationale`. Only disputed pair IDs may appear. A/B reviewers cannot act as the third adjudicator.

## Freeze and split

Only after real review + written authorization:

```bash
python -m research.label_release \
  --task-pool /private/task_pool.jsonl \
  --review-a /private/technical_a.csv \
  --review-b /private/technical_b.csv \
  --adjudication /private/adjudication.csv \
  --authorization /private/approved_company_data_use.pdf \
  --out-dir /private/frozen_release_001
```

Omit `--adjudication` only if the independent reviewers have **no** disagreements.

The release gate rejects incomplete/mismatched tasks, missing sources, missing permission record, unresolved reviewer differences, UAT/demo identifiers, detectable PII, duplicate query leakage, and overlap of project groups across train/dev/test. Group assignments are deterministic for a frozen corpus; target ratios are ~70/15/15, not exact guarantee for a small sample.

**Training uses relevance 3 as a strict positive; relevance 0, 1, 2, 3 all remain available for graded held-out evaluation.** Existing training safeguards still demand ≥50 qualified train positives, ≥10 dev positives, ≥20 distinct training SKUs, and ≥10 independent training groups. The holdout additionally needs ≥5 distinct judged inquiry IDs. These are engineering quality gates, *not statistically established study sample sizes*.

Outputs remain outside Git:
- `train_positives.jsonl`
- `dev_positives.jsonl`
- `train_judged_qrels.jsonl`
- `dev_judged_qrels.jsonl`
- `test_judged_qrels.jsonl`
- `release_manifest.json` with SHA256 fingerprints, reviewer agreement and quality indicators

No dedicated `test_positives.jsonl` is exported, to discourage accidental training on held-out labels.

## Fine-tune ONLY after the frozen gate passes

```bash
python -m research.finetune_encoder \
  --train /private/frozen_release_001/train_positives.jsonl \
  --dev /private/frozen_release_001/dev_positives.jsonl \
  --authorization-record /private/approved_company_data_use.pdf \
  --output /private/models/liliang-ai02-001 \
  --epochs 1
```

The experiment must run on authorized **local/secure compute** with its optional dependencies and access to the pinned base model. No weights or customer data may be committed to the public repository or sent to Render without separate company authorization. The training script alone does not evaluate locked test data or deploy the encoder.

## Locked retrieval evaluation

Generate `/private/rankings_ai02_bm25.jsonl` and alternative `rankings_ai02_dense.jsonl`, `rankings_ai02_rrf.jsonl`, separately **without reading the held-out labels**. Each prediction line contains:

```json
{"query_id":"AUTH-INQ-001","ranked_skus":["SKU-001","SKU-002"],"retrieval_latency_ms":13.2}
```

These values are *format illustrations only*. The evaluator deliberately rejects any retrieved SKU without a Technical relevance grade. It evaluates a **judged candidate pool** and must not be presented as full-catalog (1,452 SKU) accuracy.

```bash
python -m research.ranking_evaluation \
  --locked-qrels /private/frozen_release_001/test_judged_qrels.jsonl \
  --rankings /private/rankings_ai02_bm25.jsonl \
  --out /private/results/bm25_holdout_metrics.json
```

Metrics: graded nDCG@5, MRR@5 for relevance ≥2, Recall@5 for relevance ≥2, and P95 **retrieval-only** latency when reported. No-positive queries yield an undefined nDCG and are excluded from aggregates rather than inflating score. Scientific interpretation still needs model comparisons, confidence intervals, annotation reliability, data representativeness, and independent validation.

## Demonstration and sign-off

While Technical labels are still blank:
- Demonstrate **BM25 online** + one-run matching + Technical/Manager workflow and audit.
- Demonstrate **AI-03 exploratory proxy basket**, carefully labeled not invoice-verified.
- Demonstrate **AI-04 synthetic/naive baseline**, not failed pooled Ridge as the recommended company forecast.
- Display `/ai/data-readiness` to explain honest readiness state; do not claim that company fine-tuned AI-02 or validated AI-04 has shipped.

The research coordinator may sign the label/data release only after both experts have completed assignments, all disagreements are adjudicated, sources are approved, quality gates pass, and the holdout is frozen. **This release does not modify Neon or change stock.**
