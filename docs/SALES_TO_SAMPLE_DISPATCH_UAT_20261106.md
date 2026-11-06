# PT Liliang ERP Multi-AI — Sales-first transaction & sample dispatch workflow

**Date:** 2026-11-06 · **Scope:** UAT research only · **Cost:** Rp0 additional subscriptions.

## Final approval line (per inquiry)

1. **Sales** creates an anonymous customer inquiry, triggers AI-01 normalization + AI-02 BM25 Top-5, requests sample KG and **submits** to Technical.
2. **Technical** reviews the **latest matching run**, records decision / expert label 0–3 and rationale, selects one candidate with **latest ACCEPT + label 3**, then **submits** to Manager.
3. **Manager Operasional** reviews the selected candidate and Technical evidence; **APPROVE** sends to Gudang or **RETURN** sends inquiry back to Sales for revision and fresh matching. Historical grades from prior runs cannot approve a new inquiry revision.
4. **Gudang** checks sample availability **before dispatch**, simulates stock IN if necessary (isolated virtual UAT SKU ledger), verifies available quantity, and dispatches only if stock is adequate; atomic stock deduction prevents overspend and double dispatch.
5. **Completed (UAT)** after Gudang issues the watermarked PDF **Surat Jalan UAT** with document number, SKU, KG, fictitious destination, date and acknowledgment placeholders.

**Admin/Superadmin** manages users/master data/audit; not a routine approval stage. ERP has five roles: Admin, Sales, Technical, Manager, Gudang. Only Sales starts a normal new inquiry in the new transaction UX.

### Separate pages per transaction

- List: \`/transactions\`
- Detail: \`/transactions/{inquiry_id}\`
- Breadcrumb, title, current status, **five-step approval timeline** with completed/active/pending visual states, role-specific action panel.
- Tabs: **Overview**, **AI Matching**, **Surat Jalan**, **Audit Trail**.
- Old research and company catalog pages remain unchanged, preserving DSRM E1–E5 and dataset provenance.

### API additions

| Method | Endpoint | Role | Preconditions |
|---|---|---|---|
| GET | \`/v1/transactions\` | authenticated | Sales sees own; Gudang only Manager-approved sample requests |
| GET | \`/v1/transactions/{id}\` | authenticated | Sales own; Gudang approved sample only; inquiry requirement redacted from Gudang |
| POST | \`/v1/transactions/{id}/sales-submit\` | Sales | Existing fresh nonempty BM25 shortlist, qty>0, fictitious UAT recipient/destination |
| POST | \`/v1/matches/{run_id}/review\` | Technical | Existing Technical judgment 0–3 |
| POST | \`/v1/transactions/{id}/technical-submit\` | Technical | Latest-run ACCEPT label 3 for selected SKU, Sales stage submitted |
| POST | \`/v1/inquiries/{id}/decision\` | Manager | For sample requests, Technical-submit status and same SKU accepted in latest run |
| POST | \`/v1/sample-stock/uat-in\` | Gudang | Virtual ledger only, unique UAT reference and explicit acknowledgment |
| POST | \`/v1/transactions/{id}/warehouse-check\` | Gudang | Manager-approved; virtual on-hand quantity >= sample quantity |
| POST | \`/v1/transactions/{id}/warehouse-dispatch\` | Gudang | Virtual stock available and atomic deduction, no duplicate |
| GET | \`/v1/transactions/{id}/surat-jalan\` | authorized | Available only after UAT dispatch; printable PDF with **NOT VALID FOR PHYSICAL SHIPMENT** |

### Research data/safety boundary

The imported supplier catalog is unverified. Product suitability, halal, registration, technical datasheets and **physical stock** are not yet attested. The new \`sample_uat_balances\`, \`sample_uat_movements\`, and \`sample_requests\` tables are **additive and isolated**. No live physical stock changes, invoices, commercial SO or confirmed deliveries are created. This is not a real Warehouse Management System, shipping authorization, or official tax/shipping document.

**Do not print the UAT document for customer shipment.** A production cutover requires physical inventory attestation, SKU/lot traceability, sample inventory reservation, validated shipping address with consent, real transaction IDs, fiscal/legal document authorization, independent five-role UAT and audit sign-off.

### Reproducible UAT

- Create Sales/Technical/Manager/Gudang accounts using Admin; login in separate browser sessions.
- Sales creates a \`UAT-\` customer inquiry, runs BM25 and submits sample quantity.
- Technical records ACCEPT/label3 on one Top-5 SKU and then submits that exact SKU.
- Manager approves; Gudang views only approved sample request.
- Before virtual stock IN, warehouse-check responds 409 (insufficient).
- Gudang inserts virtual stock (reference \`UAT-...\`), checks quantity, dispatches once.
- PDF download shows \`UAT-SJ-...\`; subsequent dispatch 409. \`products.stock\` stays unchanged.
- Confirm explicit role denial 403 and anonymous API denial 401.

Automated tests: \`python -m unittest tests/test_sample_workflow.py -v\`; full suite: \`python -m unittest discover -s tests -v\`. GitHub Actions additionally checks PostgreSQL integration.

**Scientific note:** neither existing BM25, MiniLM, RRF, rules, forecasts nor the Agent is promoted to a validated company-trained model. No expert relevance datasets are fabricated.
