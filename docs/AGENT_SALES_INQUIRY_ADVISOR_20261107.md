# PT Liliang — AI Agent Inquiry Intelligence Advisor (7 November 2026)

## Intended functionality
This is the next incremental capability after the successful Groq-controlled-case pilot and read-only access to 1,452 SKU physical-stock records.

**Scope is an authenticated read-only analysis of a saved inquiry initiated by Sales.** It is not a replacement for the official Sales/Technical/Manager/Gudang workflow or a scientific claim that all four AI models are trained and validated.

### Input–Process–Output

| Stage | Input | Process | Output |
|---|---|---|---|
| Sales | Persisted inquiry ID, requirement, owner | Role authorization; local rule-based AI-01 interpretation | Extracted flavor/application/form; UNKNOWN halal and regulatory |
| Product Matching | Latest **active** matching run & Top-5 candidate table | Read saved BM25 ranking and provenance | Rank, SKU, score, product description; never report as a probability |
| Expert Review | Latest Technical decision and label for each SKU | Read-only reconciliation of relevance label 0–3 | PENDING / ACCEPT / NEEDS_INFO / REJECT; no auto-accept |
| Stock Context | Company-declared physical inventory per SKU | Read package quantity, UoM, pack content and verification status | Risk flag for zero/unknown stock and missing UoM |
| Orchestration | Persisted inquiry/sample-request status | Deterministic next-actor policy | Sales/Technical/Manager/Gudang next action with no writes |

### New endpoints and pages
- `GET /v1/agent/inquiries?limit=50` — role-scoped inquiry IDs, status and creation time only. Sales can see only own.
- `GET /v1/agent/inquiry/{id}/advice` — role-scoped deterministic advisory using existing persisted BM25 output, latest Technical review and stock. No user data is passed to Groq.
- `GET /ai/inquiry-advisor` — dedicated responsive advisory dashboard; session required to load protected content.
- Per-transaction deep link in `/transactions/{id}` to the advisory; sidebar and main Agent dashboard link added.

### Strict controls
1. Latest matching run is displayed only when the inquiry is not NEW/RETURNED; saved historical runs are ignored after a revision. An unprocessed inquiry cannot be treated as matched.
2. SQL is parameterized; no database inserts, updates, approvals or physical-stock deductions occur in the advisory.
3. PII fields `customer_ref`, `recipient` and `destination` are not included in advisory API output; requirement remains accessible only to authorized logged-in roles. The UI escapes candidate text.
4. All candidates retain uncertain halal, regulatory, datasheet and product-suitability flags until independent Technical verification. A Technical ACCEPT with label 3 is evidence of judged relevance, not manufacturer compliance.
5. The live Groq test-case route remains **separate** and uses only fixed research inputs. ERP inquiry text and physical stock are **not sent to the external model**.
6. Physical packaging: Powder = 300 g/unit, Paste = 200 ml/botol, Liquid = 500 ml/dirigen. Other types retain UOM_PENDING. No density is assumed. UAT sample transaction quantity in KG is not converted into approved shipment quantities.
7. No paid inference fallback; local advisory runs within existing Render/Neon resources.

### Acceptance testing
- Login, role checks, Sales ownership isolation, Gudang denied.
- Inquiry NEW -> no active candidates -> Sales instructed to run matching.
- MATCHED -> Top-5 persisted run and physical stock read-only.
- Sales sample submit -> Technical next actor.
- Technical ACCEPT relevance label 3 and submit -> Manager next actor; still no technical suitability approval claim.
- No stock changes, no sample dispatch, no analysis database writes, no external Groq invocation.
- Stale run ignored after inquiry revision.
- JavaScript syntax check; PostgreSQL smoke.

### Research methodology
This implementation provides a deterministic business-rule orchestration layer and local information-retrieval baseline. It can be evaluated for workflow correctness, RBAC, data provenance, latency and completeness of risk flags. It is **not** evidence of LLM reasoning over live company records or of training/validation of AI-01/03/04. For final manuscript, keep the original retrieval-focused hypothesis (BM25 vs MiniLM vs RRF with held-out Technical 0–3 relevance judgments) separate from exploratory ERP Agent support.

### Demo flow
1. Login Sales; create and match an inquiry at /transactions.
2. Open its Inquiry Intelligence Advisor. Show status, parsed need, ranking, stock packages, risk flags and next workflow actor.
3. Sales submits; Technical reviews and submits. Reload advisory and show next actor has changed to Manager.
4. Separately, in AI Agent Orchestrator, run the fixed Groq test case to show actual provider response and four-tool trace, or use local baseline if Free limits are exhausted.
5. Archive screenshots and output JSON separately. Do not claim live Groq tool calls based solely on this read-only page or GitHub CI.

