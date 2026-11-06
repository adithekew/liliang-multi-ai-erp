# PT. Liliang ERP Multi-AI — Operational inventory confirmation, 6 November 2026

## Authority and scope

The user explicitly confirmed that the \`Stock\` numbers in the uploaded \`Liliang_Report_catalog_updated.csv\` represent **physical inventory available for shipping**. This supersedes the earlier assumption that these numeric values were only an unverified reference. The supplier's product catalog and technical evidence remain marked \`CATALOG-PDF-UNVERIFIED\`; this is a **user attestation of stock availability**, not an independent stock-opname audit, nor an expert acceptance of product fitness.

Source document SHA-256: \`72d38183117d4ab3a5473de20ba4a15d60df7be02e9a4e05c7ab7884ab59deb2\`. Source generated 2026-10-30T03:28:46.628726+00:00. User physical-stock declaration date: 2026-11-06. No physical count timestamp, warehouse location, lot or expiry was provided by the user.

## Unit rules (fixed exactly as user specified)

| Product type | SKU | Packages available | Package UoM | Content per package |
|---|---:|---:|---|---|
| Powder | 339 | 91,607 | unit | 300 gram |
| Paste/Pasta | 19 | 5,159 | botol | 200 ml |
| Liquid | 607 | 155,083 | dirigen | 500 ml |
| Oil | 235 | 57,729 | UNSPECIFIED | pending |
| Seasoning | 186 | 46,601 | UNSPECIFIED | pending |
| Triacetin | 44 | 11,044 | UNSPECIFIED | pending |
| Emulsification | 13 | 3,091 | UNSPECIFIED | pending |
| Concentrate | 6 | 1,857 | UNSPECIFIED | pending |
| Solvent | 2 | 494 | UNSPECIFIED | pending |
| Emulsifikasi | 1 | 404 | UNSPECIFIED | pending |
| **Total** | **1,452** | **373,069** | *mixed package types* | |

Unspecified **487 SKUs** keep the user-confirmed physical quantity but cannot use an invented UoM or content conversion; \`dispatch_uom_status=UOM_PENDING\`.

Nominal contents from the user-provided package specifications are **not equivalent to the ERP sample KG field** and must not be combined as if they were the same measure:

- Powder: 91,607 packages × 300 g = 27,482,100 g (27,482.1 kg).
- Paste: 5,159 bottles × 200 ml = 1,031,800 ml (1,031.8 L).
- Liquid: 155,083 dirigen × 500 ml = 77,541,500 ml (77,541.5 L).
- No density assumption or g↔ml conversion.

## Neon transactional inventory migration

- \`physical_stock_confirmation\`: one authoritative confirmation record keyed by source SHA.
- \`physical_stock_before_snapshot\`: original \`products.stock\` values for **all 1,452 SKUs** before reconciliation; 1,376 NULL, 56 unchanged, and 20 replaced.
- \`physical_inventory_stock\`: physical package counts, product type, exact user-specified UoM and content-per-package, confirmation status, and UoM-pending status.
- \`products.stock\`: synchronized with the confirmed per-package quantities for all 1,452 SKUs.
- \`catalog_stock_reference\`: retains original source SHA, source references and PDF page/row; \`unit\` and stock verification status now reflect user confirmation.
- Migrated in **one SQL transaction** with 1,452 SKU integrity checks, sum 373,069, explicit 965 mapped / 487 pending mapping, and post-write \`products.stock\` consistency check. No SKU rows deleted.
- Subsequent authorized manual stock adjustments update both \`products.stock\` and \`physical_inventory_stock.qty_packages\` atomically; fractional package amounts are rejected for the mapped physical-ledger SKUs and adjustments still require audit evidence.

## Distinguish physical stock from UAT sample shipments

The **current** \`/transactions\` sample process accepts sample \`qty_kg\`, \`UAT-\` recipient/destination, and \`sample_uat_balances.qty_kg\`, and generates only a watermarked **UAT Surat Jalan**. It **must not** automatically deduct the new physical \`qty_packages\` or claim that physical shipments are implemented.

Physical-stock quantities **are available as company-declared on-hand inventory**; an actual physical dispatch flow still needs a mutually consistent sample UoM, real stock ledger reservations and warehouse reconciliation, authorized real recipient and destination, approval of document fields and safe stock deduction. This is a functional workflow integration milestone, not missing stock data.

## Scientific value

Use these records for descriptive inventory context, availability-aware **read-only** AI agents and candidate explanations. Do not present supplier-catalog descriptions as proven Technical evidence, turn BM25 scores into probabilities, treat the new stock attestation as historical sales labels, or imply that all four ML models are already validated.

## Cost

The code and data run in the existing Render Free + Neon arrangement, with no new licensed service, no paid inference and no additional hosting requested. Actual platform free-tier quotas still apply.
