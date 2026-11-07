# AI Agent PT Liliang — Integration Verification & Catalog Read-only
Date: 7 November 2026 · Project: Capstone ERP Multi-AI.

## Verification status
An earlier authenticated Groq UAT user screenshot and exported response already demonstrated an online LLM response with AI-01..AI-04 baseline outputs. However, that historical response **did not include an audited per-tool runtime trace**, so it must not be cited as proof that all four PydanticAI tool functions were invoked. The present backend exposes `tool_trace` and `all_four_tools_called` on every new Groq request. A runtime call is fully evidenced **only when** `all_four_tools_called=true` and the trace includes all four IDs.

## Internal company-data tools

- `GET /v1/agent/readiness`: read-only local checks of four baseline response shapes over five controlled cases; aggregate physical-stock ledger count; includes no external LLM call.
- `POST /v1/agent/catalog-preview` with `{"case_id":"STRAWBERRY_DAIRY"}`: BM25 baseline ranking across the ERP company catalog; output includes the top candidate SKUs, read-only `physical_inventory_stock` package counts, size/UoM, source and evidence limitations.
- `GET /v1/agent/stock/{sku}`: exact-SKU read-only physical stock by package. Uses parameterized SQL, no broad search from untrusted user content.
- Every endpoint requires ERP session authentication and authorized role (Admin, Sales, Technical or Manager); Gudang's dedicated stock screens remain separate.
- **No company catalog/physical stock is sent to Groq.** The prior `/v1/agent/demo` request still uses only the five fixed evaluation inquiries and its isolated test catalog. There is no automatic approval, inventory reservation, stock deduction, or document generation.

## Interpreting source evidence

The user confirmed physical stock counts for 1,452 SKUs in the uploaded CSV on 6 Nov 2026. The 965 mapped SKUs have packaging definitions (Powder 300 gram/unit, Paste 200 ml/botol, Liquid 500 ml/dirigen); 487 other SKUs are pending unit mapping. `qty_packages` is a **count of physical packages**, not kilograms or liters; do not convert between grams and milliliters without density.

BM25 is an uncalibrated candidate ranking function. Product fitness, technical datasheets, regulatory and halal suitability remain subject to Technical review. AI-03 association rules and AI-04 baseline forecasts in the Groq UAT remain based on controlled test data rather than independently validated company orders. None of this implies model training or scientific accuracy claims.

## Lecturer demo checklist

1. Sign in to the ERP as Admin/Sales/Technical/Manager; open `/ai/agent-pilot` using the same browser tab/session.
2. In **Jalankan Analisis AI Agent**, choose Strawberry Flavor, inference Groq, and execute once. Inspect `tool_trace` and `all_four_tools_called`; if incomplete, accurately describe as a partial LLM explanation, not successful four-tool execution.
3. Open the **Analisis Kandidat & Ketersediaan Stok ERP** panel; click *Lihat Kandidat dari Katalog ERP*. Review Top-5 local BM25 with physical package quantities. No actual SKU list is transmitted to Groq.
4. Enter a SKU from the returned table into *Periksa SKU*. Check `package_uom`, `pack_size`, `stock_status` and `package_mapping_status`.
5. Download the controlled UAT evidence JSON to archive input, tool trace and baseline output; the inventory-readonly response is local and should be recorded separately under company governance.
6. Check `/v1/agent/readiness` if authorized. It verifies **local baseline functions**, NOT a live Groq request. Do not confuse a configured API key with a successful inference.
7. If Groq fails, use local baseline mode; don't switch to a paid inference provider. The application provider attempt cap remains enabled.

## Evidence requirements for research

- For Agent orchestration: exact four-tool trace, successful request, response completeness, repeated trials per fixed query, latency, and faithfulness assessed independently.
- For AI-02: expert relevance labels 0–3, fixed candidate universe, held-out test set and nDCG@5 / Recall@5; compare BM25 vs MiniLM vs RRF, marking offline versus online paths accurately.
- For AI-03/AI-04: separate real-data training and evaluation protocol. Do not treat LLM-generated executive summaries as performance metrics.

## Deployment validation

CI runs all unit tests and PostgreSQL smoke tests; a successful deploy proves the code is live, but it does not by itself prove the private Groq API can still respond after deployment. A fresh authenticated browser run is required for that final provider assertion.
