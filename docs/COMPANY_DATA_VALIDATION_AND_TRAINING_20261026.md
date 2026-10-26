# PT. Liliang — Company Data Validation and ML Training Gate

**26 Oct 2026 | Capstone ERP Multi-AI | Engineering release**

## Objective
Make company-specific learning reproducible and safe while physical warehouse
stock remains UNKNOWN. Improve the AI dataset lifecycle without treating UAT
pass, successful ingestion, or a plausible forecast as scientific validation.

## Observed evidence and classification

The source received from the company is a 2025 sales-list Word document.
Its extracted CSVs are private local files, **NOT** repository assets.
Some source lines in June are labelled *payment due*, not sales.
A monthly aggregate does not establish the calendar date of an order.
A paragraph/customer grouping does not establish a shared order/invoice ID.
Do **not** generate pseudoinvoice dates, zero-fill missing June, claim genuine
basket associations from paragraph groups, or merge unknown stocks as zero.

The private audit script records only dataset counts, checksums and gate reasons:

```bash
python -m research.company_sales_audit \
 --items /secure/01_item_lines_full.csv \
 --lines /secure/04_ml_lineitems_deidentified.csv \
 --monthly /secure/05_monthly_sku_observed_only.csv \
 --baskets /secure/06_basket_proxy_not_orders.csv \
 --out /secure/reports/company_sales_source_quality.json
```

Never run this on Render free ephemeral filesystem with unapproved documents;
keep raw data in a restricted company system, not Github or shared Drive.

## AI-specific validation

| Module | Validation before private company training / credible analytics |
|---|---|
| AI-01 | Approved deidentified inquiry text + independently checked intent/entity labels; current parser stays rule-based |
| AI-02 | Company-approved inquiry–SKU pairs with *independent* Technical 0–3 labels, justification/datasheet, adjudication, leakage-safe train/dev/test, and withheld test |
| AI-03 | Actual SO/invoice IDs, normalized SKU, line items, transaction dates, status/returns; not monthly sales-list bullets |
| AI-04 | Finance-verified KG quantities and 24+ complete contiguous calendar weeks per SKU, with documented missing/closed weeks, rolling holdout and baseline |
| WMS | Separate stock opname, inbound/outbound ledger, lot/receipt, stockouts and lead time before available-to-promise or reorder recommendation |

**Stock wait is not a blocker for AI-01/AI-02 language and retrieval
experiments**, but procurement based on model output stays blocked.

## Private AI-04 model training executable

We supply an **offline reproducible trainer** that fits a regularized lag-1–4
autoregressive ridge model and compares it against a 4-week moving-average
baseline on the last 4 chronological weeks. It requires 24+ contiguous,
fully reconciled, complete weekly records for each SKU and fails closed
otherwise. No model is automatically deployed or promoted to AI-04 runtime.

It accepts only a local CSV with:
`sku,week_start,qty_kg,source_status,week_complete,source_doc_sha256`

Every row must carry `FINANCE_VERIFIED`, `YES`, a real Monday week start,
a nonnegative numeric KG total and a SHA256 reference to source proof.
Human authenticity review remains necessary: these fields are *claims*,
not cryptographic proof of Finance approval.

```bash
python -m research.private_demand_training \
 --weekly-csv /secure/finance_approved_sku_weeks.csv \
 --research-authorization /secure/signed_research_approval.pdf \
 --finance-signoff /secure/signed_finance_reconciliation.pdf \
 --output /secure/private_models/liliang_ai04
```

Output: `training_manifest.json` with coefficients, fingerprint, local source
documents' SHA256, per-SKU MAE on heldout weeks vs baseline and status
`PENDING_HUMAN_AND_STATISTICAL_REVIEW`. No raw records or customer names
are written to the manifest. The trained artifact stays outside GitHub.

**Important:** Even if the code runs, small 4-week holdout and known dataset
bias do not establish production-grade accuracy. Models require independent
approval, source/label verification, broader backtesting, uncertainty and
business-impact assessment before production.

## AI-02 domain encoder fine-tune

The existing `research/finetune_encoder.py` contains the optional offline
MiniLM training entrypoint; it requires authorized, anonymized expert-positive
pairs with adequate diversity via `research/training_gate.py` and a
separate frozen test set. A supplier catalog alone or UAT review records do
not meet this gate. Local compute outside free Render should perform training
only after all required source authorizations and labels are present.
Do not claim BM25 or RRF themselves were trained neural models.

## New live data-status endpoint

`GET /v1/research/company-data-gates` is read-only, JWT-protected
(Admin/Manager/Technical), and returns counts/status without customer names.
The existing `/ai/data-readiness` view now differentiates:
- functional demo smoke PASS,
- extracted but unreconciled company data,
- candidate Technical labels vs independently validated research gold labels,
- sales facts attestation vs verified transaction evidence,
- independent warehouse stock gate.

This is a visibility/control feature, **not a trainer running on Render**.

## Acceptance criteria

- New training and audit scripts reject missing source columns, incomplete
weekly series, unverified rows, missing authorization records and source gaps.
- CI uses synthetic fixtures exclusively and never trains on real company
source files.
- PostgreSQL/SQLite existing 5-role workflows and source-labelled reports pass.
- Live UI clearly states *no company model scientifically validated* while
Neon still has no eligible independent labels and no Finance-verified orders.
- No inventory status, no sale amounts, no UAT records are modified.

## Finance and Technical dependencies

Finance must supply reconciled SO/Invoice + line items + date + KG quantity +
status and credit notes/returns, specifically resolving June. Technical must
independently score inquiry–SKU 0–3 using authorized datasheets. Only then
should we freeze datasets and run true company training and held-out tests.
