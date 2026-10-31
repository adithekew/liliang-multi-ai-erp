# ERP Multi-AI PT. Liliang — Demo Release Candidate (31 Oktober 2026)

## Scope, evidence, and safety

The demonstrated ERP has five authenticated roles on Render / Neon. This release:
- Makes the existing business workflow **operationally testable** with Manager feedback, RETURN, Sales revision, fresh BM25 rematch, fresh Technical review, and final Manager APPROVE (or another RETURN).
- Adds independent **UAT WMS sandbox** with virtual UAT-SKU inbound, outbound, virtual KG balance, duplicate-ref rejection, authorization, and PDF/CSV/JSON report. The WMS demo **NEVER updates** `products.stock`, Sale Orders, invoices, or existing audited warehouse counts.
- Preserves all historical inquiry runs, review decisions, audit events and company catalogue. Conflicting old UAT labels remain flagged, not silently rewritten.
- Leaves real Stock/Inbound/Outbound/SO/Invoice as PENDING. Real AI-02 neural inference, company AI-03/AI-04 training, and learning analytics remain PENDING as described in the existing research status view.

The code is released from a separate branch after green 5-role CI using disposable SQLite and temporary PostgreSQL. Do **not** substitute the synthetic scores/data for official company results.

## Full input → process → output demonstration (20 minutes)

| Minutes | Role | Input / action | Process | Output/evidence |
|---|---|---|---|---|
| 0–2 | Admin | Log in, open Dashboard and /ai/data-readiness | Read permissions and readiness | Current role/session, source classifications |
| 2–5 | Sales | New inquiry with `UAT-` anonymous reference and permitted strawberry/beverage text | Save NEW, run online constraint-aware BM25 once | New inquiry ID, matching run ID, Top-5 or NO_MATCH, explainable matching evidence |
| 5–8 | Technical | Open latest matching, mark candidate NEEDS_INFO with relevance 2 and rationale | Store expert review in audit (not scientific gold label) | Inquiry becomes TECH_REVIEWED |
| 8–10 | Manager | Choose RETURN, enter a substantive reason | Save RETURNED + reason in transaction event | Inquiry decision, reason in report and Sales feedback |
| 10–12 | Sales | Open RETURNED record, view Manager reason, correct the inquiry description | Revision writes new requirement, status NEW, keeps prior run history | Same inquiry ID eligible for a **new** BM25 run |
| 12–14 | Sales + Technical | Run BM25 again, open latest run, mark ACCEPT grade 3 with rationale | Old review cannot be reused for new run; fresh current label saved | New run ID and TECH_REVIEWED |
| 14–15 | Manager | APPROVE with reason | Check latest-run ACCEPT grade 3, persist reason and status | APPROVED + append-only audit event |
| 15–17 | Gudang | Open /wms/sandbox, input `IN` virtual KG using `UAT-WMS-...` reference, then `OUT` with another ref | Check virtual balance and prevent overspend; **no changes to company stock** | Virtual WMS ledger, new saldo, dedicated PDF/CSV |
| 17–19 | Admin/Manager | Open reports, export per-inquiry PDF, Manager decisions and WMS sandbox | Server generates exports on demand | Proof of actions/revisions and manager reasons |
| 19–20 | Presenter | Display AI-03/04 and Learning Center | Explain controls/source boundaries | Synthetic association/forecast and learning prototype correctly labeled |

## Preconditions and no-go

- Open `/healthz` then `/readyz` 10–15 minutes before presentation; wait for Render Free cold start and ensure PostgreSQL `ready:true`.
- Log in with real UAT accounts for Sales, Technical, Manager, Gudang and Admin (one browser profile each, preferably separate sessions). Do not display passwords.
- Use **only fictional inquiry texts and sandbox IDs**; preserve anonymous customer references. Do not use real client secrets.
- Demo WMS SKUs are `UAT-WMS-STRAW`, `UAT-WMS-VANILLA`, `UAT-WMS-MANGO`. They do **not** map to 1,452 actual catalogue SKUs or validated physical quantities. Use unique `UAT-` references.
- Stop any live mutation if a real product SKU or customer invoice appears on the UAT screen.
- If `/readyz` fails or role/session expires during presentation, switch to presentation deck and rerun login off-screen.
- Do not present zero SO records as a company sales-intelligence success. `/v1/ai/bundling-company` and `forecast-company` must show insufficient data until independently validated inputs exist.

## Expected output checks (after completing demo)

1. Inquiry Status = APPROVED and two matching runs saved for the **same** inquiry ID.
2. At least one return and one approval transaction event, both containing a Manager `reason`; Sales may view own Manager feedback.
3. PDF inquiry report includes two matching runs, review notes, RETURN/REVISION/APPROVE histories and Manager reasons.
4. WMS virtual `IN 25KG`, `OUT 10KG` yields virtual 15KG. OUT greater than virtual stock and duplicate references are rejected.
5. Catalogue stock in `products` is unchanged; WMS demo uses dedicated `wms_demo_movements` table.
6. Five-role RBAC denies Gudang customer inquiry and denies Sales/Technical access to WMS demo; Manager can view WMS but only Admin/Gudang can create virtual movements.
7. AI modules disclose whether rules, BM25, neural benchmark, association rules and forecasts are validated or synthetic.

## Repository and audit

Code: `feature/demo-end-to-end-workflow-wms-sandbox-20261031`. Run `python -m unittest discover -s tests -v` on disposable SQLite, plus `tests/postgres_integration.py` against CI's temporary PostgreSQL 16. Static JavaScript check `tests/check_ui_js.py` and Render page smoke are required before merging.

Limitations and remaining real-world prerequisites:
- No verified inbound/outbound against actual physical lots, no purchase or sales order linkage, and no real available-to-promise calculation.
- AI-02 MiniLM/RRF company training needs independent expert labels, data permissions, frozen holdout, and evaluation. AI-03/04 company modules need real transaction dates/order IDs/weekly series and Finance review.
- Historical inconsistent UAT reviews remain visible as flagged records, not retroactively altered.
- Render Free may spin down on idle; browser demo is subject to cold start and network conditions.
