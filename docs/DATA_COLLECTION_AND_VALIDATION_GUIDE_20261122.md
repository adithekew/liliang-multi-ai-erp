# Data collection, verification and validation guide — PT Liliang ERP Multi-AI

Version date: 2026-11-22
Related issue: #37
Implementation PR: #38 (draft)

## Workbook
Use the private workbook `Template_Data_ERP_MultiAI_PT_Liliang.xlsx` delivered to the project owner. It contains 17 sheets:
- Supplier catalog and technical evidence.
- Customer inquiry corpus, AI-01 gold labels, and AI-02 relevance labels.
- Finance order headers/lines and weekly demand.
- Warehouse locations, physical opening count, and movements.
- Model run manifests, AI test results, and Agent evaluation.
- Data dictionary and AI-02 relevance rubric.

The workbook itself must not be committed to this public repository after it contains company data. Keep the original supplier PDFs, COA/TDS/SDS, invoices, order extracts and stock-count documents in the company's private approved storage. Workbook fields should point to controlled document references and file hashes, not public URLs.

## Recommended collection sequence

### 1. Supplier technical catalog
Purchasing exports one row per supplier SKU in `01_SUPPLIER_CATALOG`. Do not merge distinct supplier SKUs simply because the product names look similar. Preserve supplier/manufacturer wording in `product_description_verbatim`.
Technical records each TDS/COA/SDS/certification as a separate row in `02_TECHNICAL_EVIDENCE`, including revision, issue/expiry date, page/section, exact supported value, file hash, and review status.
Only a human Technical reviewer may mark a record VERIFIED. If a document is missing, expired, contradictory, or silent on an attribute, leave the field unknown and record the question. Do not infer halal, allergen, GMO, food/pharma grade, CAS, or regulatory compliance from a product name.

### 2. Inquiry and expert labels
Sales supplies de-identified free-text inquiries and a valid data-use authorization reference. Remove names, email, phone, customer addresses, personal contact details, and confidential pricing not needed for matching.
AI-01 annotators label intent/entities in `04_AI01_GOLD_LABELS`.
For AI-02, Technical reviewers independently score each inquiry–SKU pair in `05_AI02_RELEVANCE_LABELS`:
- 0: not relevant
- 1: weak relevance
- 2: partial/conditional relevance
- 3: high relevance supported by evidence
- UNKNOWN: insufficient evidence; do not force a 0–3 label.
Use at least two independent reviewers and an adjudicator. Record the supporting evidence ID. Keep a frozen test set untouched by model selection.

### 3. Finance transactions and demand
Finance supplies pseudonymous order references and one row per order line. Preserve original quantity/unit. Fill KG-converted quantities only when Finance has approved the conversion and a conversion evidence reference exists.
Only confirmed/fulfilled/eligible partial orders that Finance has reconciled may be used as company facts. Exclude cancelled and fully returned orders from baskets; treat line-level returns explicitly.
For AI-04, provide one row per SKU per complete Monday-start calendar week, in KG. Do not create zero-demand weeks from missing documents. Mark partial weeks, missing data, stockouts and inactive SKU weeks explicitly. The first operational forecast experiment requires at least 24 contiguous complete verified weeks per SKU.

### 4. Warehouse
Warehouse defines warehouse/bin IDs and performs a dated physical count. Opening stock requires a count reference, timestamp, lot/expiry where tracked, source unit, and verified UoM evidence. The legacy stock attestation is not a substitute for a current count.
Any SKU with pending package/UoM mapping is blocked from dispatch until resolved. The new WMS ledger is feature-flagged off by default.

### 5. Model and agent tests
Every training/evaluation run gets a run ID, code commit, dataset version/hash, split definition, sample counts, model version and approval state.
Record actual observed metrics only. The validation sheet is not a place to type target values. Agent cases must include expected/actual tool, role, grounding, policy compliance and unauthorized-action attempts.

## Offline workbook validation

Install private data-validation dependencies in an approved private environment:

```bash
python -m pip install -r requirements-data-validation.txt
python scripts/validate_company_workbook.py \
  --workbook /secure/path/Template_Data_ERP_MultiAI_PT_Liliang.xlsx \
  --output /secure/path/validation_report.json
```

The report includes workbook SHA-256, counts, schema/data-quality issues and readiness gates only. It intentionally does not echo inquiry text, customer names, order values, supplier descriptions or source documents. The script refuses to write its report inside a Git checkout.

## AI-02 private neural index

Only after written authorization and current catalog approval, run in a private machine/container with sufficient memory:

```bash
export LILIANG_NEURAL_MODEL_PATH=/secure/model/multilingual-minilm-l12-v2
export LILIANG_NEURAL_INDEX_PATH=/secure/index/company-catalog-embeddings.json
python scripts/build_private_catalog_embeddings.py \
  --authorization-record /secure/approvals/catalog-embedding-authorization.pdf \
  --output /secure/index/company-catalog-embeddings.json
```

The output is a private model directory and private vector index. Never commit either to GitHub or upload them as public CI artifacts. Then configure the ERP service to read those exact private paths. The online endpoint is `POST /v1/ai/neural-match`; it uses arbitrary inquiry text, validates full catalog coverage/fingerprints, applies hard constraints, and fuses dense + BM25 ranks with RRF. It does not claim suitability or accuracy.

## AI-03 and AI-04
AI-03 is association-rule mining, not neural supervised training. Its company output is exploratory until Finance has reconciled true invoice/order baskets and temporal future-basket evaluation has passed against a popularity baseline.
AI-04 uses verified weekly KG demand. The existing offline Ridge experiment now has an expanding-window rolling-origin validation utility comparing Ridge AR(4), four-week moving average, and last-week naive baseline. A model run remains pending human/statistical review and is not auto-deployed.

## Agent and WMS
The new `POST /v1/agent/execute` orchestrates AI-01, AI-02, AI-03, AI-04, stock read and readiness tools locally. It logs query/result hashes and tool names only; raw prompts are not persisted. It cannot approve, reserve, dispatch or adjust inventory.
The operational WMS has separate append-only movements, stock balances derived from movements, reservations, warehouse/bin masters and opening snapshots. It is disabled unless `WMS_OPERATIONAL_ENABLED=true`. Do not enable until physical count, UoM, role UAT, reconciliation and owner sign-off are complete.

## Release rule
A passing schema validator or CI suite is not scientific model validation. Promotion requires actual private dataset runs, held-out metrics, independent reviewer approval, security review, backup/restore test, operational UAT, and owner authorization.
