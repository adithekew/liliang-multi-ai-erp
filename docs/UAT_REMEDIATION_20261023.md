# UAT Remediation Register — PT. Li Liang Multi-AI

Date: 23 October 2026. Scope: 21 October 2026 two uploaded UAT reports, five-role research pilot.

**Evidence must not be confused with model validation:** 24/24 checklist scenarios in the first report and 16/16 steps in the later report passed with observations. These are workflow tests, NOT held-out nDCG/precision or proof of model training.

| ID | UAT observation | Action in this change | Verification |
|---|---|---|---|
| UAT-01 | Duplicate BM25 runs | Existing atomic NEW → MATCHED guard retained; add immediate client-side double-click lock | Existing `test_pilot.py` and new UAT regression |
| UAT-02 | Lemon powder smoke mismatch | Use parsed catalog product type from description, rather than requiring `powder` in product display name | `test_uat_remediation.py`, verified pass |
| UAT-03 | Powder Top-5 for beverage inquiry | Require Sales to explicitly choose physical form when known. Do not infer that all beverages require liquid. UI appends confirmed form to requirement for constraint-aware matching | Regression of matched/unknown forms is future expert UAT |
| UAT-04 | Technical label 2 accepted and approved | Future ACCEPT requires relevance grade 3. Grade 2 should be NEEDS_INFO; grade 0 requires REJECT. Manager approval requires latest grade-3 ACCEPT, not stale rejected review | New API tests |
| UAT-05 | Wrong message on repeated approval | Explicit 409 'already decided' without status mutation | New API tests |
| UAT-06 | Missing rejected 403/409 actions in audit | Log authenticated denied or conflict HTTP events with method, path, status, no token/body/customer text | New API tests |
| UAT-07 | Identical hashes for repeated events | v2 SHA-256 hashes bind UUID, persisted metadata and canonical before/after JSON. **Old events remain unchanged and use legacy payload hash** | New API tests |
| UAT-08 | Idle logout not distinguished | Record server idle-session expiration and client IDLE vs manual logout | Existing CI plus re-UAT recommended |
| UAT-09 | Duplicate login clicks, invisible errors | Disable button while login pending, add password visibility toggle and prominent inline error | Browser JS syntax CI |
| UAT-10 | Browser prompt decision dialogs | Accessible modal forms for Technical and Manager; validation on server as authority | Browser JS syntax CI |
| UAT-11 | Sidebar label duplication | Separate Applied BI & Inventory grouping | Browser JS syntax CI |
| UAT-12 | KPI Expert Reviews=0 despite UAT review | **By design**, research KPI excludes UAT; display both research-qualified and UAT review counts independently | Existing dashboard API tests |
| UAT-13 | Pop-up blocker for print | Download authenticated PDF instead of opening new window; print using PDF viewer | Browser UAT needed |
| UAT-14 | Manual refresh needed | Add refresh button and conservative active-user 45-second polling on Inquiry page; suppress polling while form being edited | Browser UAT needed |
| UAT-15 | 15-min idle warning absent | 60-second countdown and 'Tetap masuk' API revalidation; do not silently keep abandoned sessions active | Browser UAT needed |

## Preservation and limitations

- No schema migration, no reset, no re-seeding, no stock update, no company dataset committed.
- Historical approved UAT inquiry records are preserved. Stricter approval rules apply to **future decisions** only.
- Do not promote UAT acceptance into scientific training/evaluation. Preserve research exclusions.
- Catalog source remains unverified and inventory balances remain UNKNOWN until authorized physical counts.
- MiniLM/Q01–Q10 remains offline synthetic; no company-trained model, actual invoice-driven bundling or production-grade forecast is claimed.
- This patch is not the WMS implementation, live hybrid search, authenticated visual UAT, or expert validation.

## Required user acceptance retest

1. Login once (double click), show/hide password, test invalid input message.
2. Open Sales inquiry and select powder vs liquid explicitly; test lemon powder bakery and mango liquid beverage. Where catalog metadata is UNKNOWN, treat suitability as unknown.
3. Double click Run BM25; ensure only one persisted run.
4. For grade 2 choose NEEDS_INFO; verify ACCEPT+2 is HTTP 422. Use ACCEPT+3 then Manager approval once. Repeat approval → friendly 'already decided' 409; records remain unchanged.
5. As unauthorized role request a protected API → 403 and unique audit trace. Check that no password or free-text inquiry is logged.
6. Test session warning after 14 minutes, confirm active continuation, then allow true 15-minute idle expiry; audit differentiates.
7. Validate 13 role routes and reports PDF/CSV; test browser printing without popup.
8. Compare /ai/evidence research label counts vs /dashboard UAT review counts. Do not treat any UAT result as model accuracy.

## CI

Run `ERP Pilot CI` (syntax, SQLite tests, disposable PostgreSQL integration tests).
Do not infer Render rollout solely from GitHub CI; verify the live pilot post-merge.
