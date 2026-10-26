# ERP Multi-AI — June 2025 Excluded & Exploratory Basket Assumption

**26 October 2026 | Scope: Finance/Sales 2025 extract, AI-03, AI-04, and independent Technical review.**

## Decisions implemented

1. **June 2025 is entirely excluded** from sales-list experiments, candidate basket groupings, and monthly model training. June payment-due rows are not converted into a fictional sale.
2. Products grouped in the same source list may be analysed under the user's **assumption of joint purchasing**, but they are named `USER_ASSUMED_PROXY`. They cannot be represented in an invoice-grade fact table or as independently verified "same invoice" evidence.
3. ERP has a new **Admin/Manager read-only** endpoint `POST /v1/ai/bundling-proxy-preview` and a corresponding upload-preview control on `/ai/data-readiness`. It neither changes stock nor writes sales facts to Neon. June groups are excluded again server-side, and output is explicitly `EXPLORATORY_USER_ASSUMED_PROXY_NOT_INVOICE_VERIFIED`.
4. Technical relevance labels 0–3 must be supplied independently by two actual reviewers. A new offline `research/technical_independent_agreement.py` compares identical frozen pair IDs, requires per-pair datasheet evidence and rationale, calculates agreement and identifies adjudication candidates. It never fabricates gold labels.
5. New offline `research/monthly_experiment_2025.py` trains a **pooled ridge regression on two monthly lags**, using only complete Jul–Dec 2025 series, train targets September–October, and December as a chronological holdout. It compares MAE against 2-month moving-average baseline and cannot be deployed automatically.
6. `research/company_proxy_basket.py` computes grouped-list *proxy* support/confidence/lift under transparent filtering, without publishing real company data. Both scripts run on analyst's private files only.

## Intended AI-03 workflow

- Privately extract and de-identify the sales-list data.
- Remove June, incomplete/misaligned SKUs and invalid quantities.
- Group the remaining products by source paragraph/bullet group **as an assumption**.
- Run proxy rule mining with `co-group-count >= 2`, `support >= 0.003`, and `confidence >= 0.20`.
- Open the ERP's **AI Demo & Data Readiness** as Admin/Manager, upload locally generated `06_ERP_AI03_proxy_preview_payload.json`, and review a transient Top-30. No SQL insertion and no automatic cross-selling action.
- When Finance later supplies true invoice/order IDs, evaluate actual baskets separately through the already protected company-fact import path. Do **not** overwrite proxy descriptions with fictitious invoice IDs.

## AI-04 experiment (not trained production model)

- Work only with monthly observations and exclude June. No fabricated weekly dates or zero imputation.
- Require six observed and unflagged monthly values July–December per SKU.
- Use known earlier months to form lag features; do not fit on December's target.
- Save local model evaluation results, including comparison with the naive baseline, as a **negative result** when worse.
- Full operational forecasting still requires sufficient Finance-verified dated history and temporal backtests. Existing baseline and WMS stock gate remain unchanged.

## Technical and AI-02 gates

- Two independently completed reviewer files, same real authorized inquiry–SKU pool, but independent grade 0–3, evidence and rationale.
- Workbooks are generated for the user *outside this public repo*, one for Technical A and one for Technical B.
- Export the `PENILAIAN` sheet as CSV UTF-8 and run:

```bash
python -m research.technical_independent_agreement \
  --review-a /secure/technical_a.csv \
  --review-b /secure/technical_b.csv \
  --out /secure/label_agreement.json
```

- No label outputs can be called adjudicated gold until both reviewers, permissions, provenance, and disputed pairs are handled.
- Existing `research/training_gate.py` and `research/finetune_encoder.py` remain the guard for offline MiniLM; no UAT labels are promoted.

## Reproducible, private analysis

```bash
python -m research.company_proxy_basket \
  --deidentified-lines /secure/04_ml_lineitems_deidentified.csv \
  --out /secure/proxy_analysis.json

python -m research.monthly_experiment_2025 \
  --monthly /secure/05_monthly_sku_observed_only.csv \
  --out /secure/monthly_model_experiment.json
```

Do not commit CSV, private model coefficients produced from restricted data, authorized inquiry text, customer names, or reviewer input files to this public repository. All CI fixtures are synthetic.

## Status definitions

| Status | Meaning |
| --- | --- |
| Online BM25 | Operational baseline matching for live inquiry workflow |
| Proxy AI-03 | Exploratory association under an explicit user's co-grouping assumption, **not** invoice verified |
| AI-04 Monthly | Offline limited-data model experiment with measured holdout; **not** production forecast |
| AI-02 expert gold | Pending two independent reviewer labels and adjudication |
| WMS | Stock still UNKNOWN until physical warehouse stock and movement ledger validated |

## Acceptance

The new endpoint rejects non-Admin/Manager access, ignores June even when present in input, returns no data persistence, and marks all rules as exploratory. Unit/SQLite/PostgreSQL and UI JS checks must pass, followed by Render live revision verification. Five-role interactive UAT is still required for final demo sign-off.
