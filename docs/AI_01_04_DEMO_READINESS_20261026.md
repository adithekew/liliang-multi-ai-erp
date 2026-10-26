# Release candidate: AI-01–AI-04 Demo Readiness + Company Sales Facts (26 Oct 2026)

## Scope / release decision

This change does NOT claim that every AI model is trained, independently evaluated, or production-ready. It protects the existing Render/Neon research pilot. No existing stock, UAT inquiry, Technical review, catalog, or historic audit is reset or rewritten.

| Feature | Pilot state after this PR |
| --- | --- |
| AI-01 Requirement Interpreter | Existing rule-based bilingual parser online; read-only preflight case |
| AI-02 Product Matching | Existing BM25 and saved Top-5 + Technical / Manager workflow; preflight checks non-empty catalog matching |
| AI-02 Neural | MiniLM + RRF **only** previously generated synthetic fixed-query fixtures, not online company-catalog neural inference |
| AI-03 Bundling | Existing synthetic 16-basket demo **unchanged**; **new** distinct company-attested order-fact association endpoint only after ≥10 eligible orders |
| AI-04 Forecast | Existing synthetic 24-week demo **unchanged**; **new** distinct company-attested 4-week moving average only after ≥8 contiguous actually observed weekly order buckets per SKU |
| Order history | New private append-only `ai_sales_orders` and `ai_sales_lines` tables on Neon/PostgreSQL (plus disposable SQLite in CI) |
| Reports | New AI Sales Facts Register, Company Basket Rules, and Company Forecast Readiness exports (PDF/CSV/JSON); old 12 reports remain |
| Demo | New /ai/data-readiness page, separate statuses for smoke vs scientific validation; role-gated Admin import and read-only checks |

## Validation of data

- Import can be executed only by a non-UAT Admin, with an explicit `source_authorized:true`, `confirmation`, an 8+ character documentary reference and append-only unique pseudonymous order references. The backend verifies SKUs against the current catalogue, quantities >0, nonfuture dates, duplicate rows and dates.
- Supported measurement unit: **KG only**. Other units must be converted with Finance's source evidence before import. For accuracy, mixed unit conversions, returns, cancellations, FX/invoice semantics and missing weeks require independent reconciliation.
- Only `CONFIRMED` and `FULFILLED` lines are eligible. `CANCELLED` and `RETURNED` are excluded from forecasting and association baskets.
- Data status is `COMPANY_ATTESTED`, not `COMPANY_VERIFIED`: an authorized administrator's source reference is not an independent Finance sign-off or legal clearance.
- Missing weekly records are **not** interpreted as zero; the system returns `NOT_READY`.
- A working baseline is not AI training. There is no company fine-tuning, automated retraining, inventory reorder, or automatic sales action.
- Company data must be imported only into a private database; **never into GitHub, a shared Drive folder or screenshots**.

## Example JSON format (schema illustration — NOT a real sales dataset)

```json
{
  "orders": [{
    "order_ref": "ANON-FIN-001",
    "order_date": "2026-01-05",
    "status": "FULFILLED",
    "lines": [{"sku": "SKU-FROM-VERIFIED-CATALOG", "qty": 12.5, "unit": "KG"}]
  }]
}
```

The example **must not** be imported as company data. It will fail if the SKU is not in the live catalogue. The UI requires a separate Finance document register ID and explicit confirmation. Import is append-only: duplicates fail with HTTP 409.

## Demo plan: show four real functions without scientific overclaim

1. Open /ai/data-readiness with Admin or Manager: check **DEMO FUNCTIONAL SMOKE**, read AI modes.
2. Sales creates an anonymous inquiry with confirmed flavor and product form, runs BM25 exactly once.
3. Technical reviews Top-5 with relevance 0–3; label 2 stays NEEDS_INFO; label 3 ACCEPT requires product evidence.
4. Manager approves only after the latest grade-3 ACCEPT; repeat decision rejected with HTTP 409.
5. AI-03 shows synthetic association rules and, **separately**, any company-attested rules if the input threshold is met.
6. AI-04 shows synthetic 4-week moving average and, **separately**, company-attested forecasts if enough contiguous real weekly records exist.
7. Admin exports three additional source-labeled reports and checks audit; Gudang checks catalog/forecast only, without inquiry metadata.
8. Demonstrate missing-data `NOT_READY`: no false company prediction and no silent synthetic fallback.

## Automated validation and publication gate

- All pre-existing tests must pass (including RBAC, UAT, audit events, reports, catalog and PDF).
- New tests use a disposable, local database with **test-only** orders and require auth, provenance, SKU validation, duplicate rejection, company vs synthetic isolation, AI03 association, AI04 4-week backtest and report accessibility.
- CI runs the same APIs on temporary PostgreSQL 16.
- A live Render smoke verifies the revised UI is actually deployed; this is distinct from five-role interactive sign-off.
- PR merge and any resulting automatic Render deploy should happen only with green CI.
- Final claims: operational demo ready with independent user retest pending; validated AI model performance still **PENDING**.

## Further work before a company production release

Document identity and permissions; Finance reconciled SO/invoices for all months incl. June; real inquiry–SKU Technical expert labels 0–3; frozen dataset and held-out nDCG@5/MRR@5; multilingual online neural retrieval if warranted by experiment; WMS inbound/outbound/lot/QC/FEFO and stock ledger; forecast demand backtesting (vs orders with stockout correction); pipeline versioning, model registry and explicit approval gates.
