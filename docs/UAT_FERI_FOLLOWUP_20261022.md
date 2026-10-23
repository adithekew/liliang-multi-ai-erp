# Third UAT Follow-up: Feri Irawan, 22 October 2026

Document evaluated: `20261022-Laporan UAT-Liliang_ERP.pdf` (8 pages; 9 listed steps PASS).
The report predates 23 October's prior UAT remediation and includes screenshots from its own testing. It is historical evidence, not a scientific AI performance benchmark.

## Reconciliation with deployed software

| Report and evidence | Observed state | Resolution |
|---|---|---|
| PDF p.1-2: 9 PASS steps for Admin, Sales, Technical, Manager and Gudang | Five-role workflow broadly works | Preserve operational flow; add targeted API and UI regression |
| PDF p.3-5: inquiry #10 / matching run #13 (UAT-ANON) | Single matching run shared by Sales and Technical | Existing atomic match idempotency retained |
| PDF p.5: historical Technical `ACCEPT / relevance 2`, `REJECT / relevance 3` | UAT label-decision contradiction | Pre-existing patch prevents future invalid combinations. Read-only API/UI now **flags** incompatible legacy review combinations without editing historical records. UAT excluded from academic evaluation |
| PDF p.4-5: Top-5 Mango Powder while beverage intent, requested form 'Belum ditentukan' | User did not explicitly require liquid. This is not an automatically proven error | Preserve form-aware Sales field; expose SKU product-form metadata in candidate ranking; require Technical suitability review; unknown form remains UNKNOWN |
| PDF p.7: Gudang `/inquiries` shows IDs, status and 'Restricted' columns | Redaction insufficient for strict company inquiry RBAC | Gudang no longer can call GET /v1/inquiries (403), see inquiry sidebar entry or navigate from Dashboard. Distinct unauthorized requests audit logged |
| PDF p.1,7: supplier catalog 1,452 SKUs and stock UNKNOWN | No audited opening balance; UAT must not write simulated stock | For supplier-import catalog: reject `uat-*` writers; require stock count reference + date for any future authorized change; log evidence reference and date. Still not a full WMS or independent physical-count approval |
| PDF p.1,8: UAT review separate, research VALIDATED=0 | Scientific scope correctly isolated | No changes to held-out scientific claim, no UAT-to-training promotion |
| PDF p.1: AI-03/AI-04 synthetic, MiniLM+RRF fixed synthetic | Operational models not yet real-sales trained | Keep status labels, no claims of live online neural performance |

## Regression controls

- `tests/test_pilot.py`: Gudang inquiry read must return 403 (not redacted data).
- `tests/test_z_feri_uat.py`: isolated ephemeral database verifies RBAC, label-conflict warning, catalog stock UAT blockade, evidence+date-required physical count updates, and audit.
- Existing `tests/test_uat_remediation.py`: new invalid Technical decisions rejected; repeat Manager APPROVE blocked; UAT reviews excluded from research counts.
- CI must pass `python tests/extract_ui_js.py`, `node --check`, Python unit suite and disposable PostgreSQL integration.
- Live smoke checks verify cloud deployment, but do not authenticate five roles or prove trained AI accuracy.

## Non-destructive release boundaries

1. Never reset catalog or demo/Neon databases to fix UAT records.
2. Do not edit inquiry #10, matching run #13, or older contradictory Technical review rows: preserve as audit evidence.
3. Never fabricate physical counts. A reference+date is an *attestation*, not an independent check; later WMS must implement stock-count submission and Manager approval.
4. The 2025 sales history cannot be interpreted as real order-basket association or accurate demand forecasting without transaction IDs, missing months, and Finance validation.
5. New rules protect **future** state changes; previous UAT approvals remain historical and must not be construed as scientific gold labels.

## Post-deployment manual retest

- Gudang: sidebar excludes Inquiry & Matching; direct URL redirects to a permitted page; API /v1/inquiries returns 403; catalog and inventory forecast remain visible.
- Sales: create `UAT-ANON` inquiry with physical form selected, run once; Technical and Manager see exact same run ID.
- Technical: review a grade-2 candidate with NEEDS_INFO; reject ACCEPT+2 and REJECT+3; grade-3 ACCEPT only after verifying available evidence.
- Admin: open a historical pre-patch UAT run with inconsistent labels, confirm conflict flag; verify records are unchanged in audit/report.
- UAT Gudang: attempt an authorized-URL stock update using UAT account with fabricated evidence; receive 403 and leave all physical stock UNKNOWN.
- Authorized stock keeper (only with real physical-count document): test on controlled environment, check evidence reference and date audit, never use dummy stock on live company catalog.
- Confirm AI Research Evidence still excludes UAT labels and module claims remain labeled synthetic/unverified.
