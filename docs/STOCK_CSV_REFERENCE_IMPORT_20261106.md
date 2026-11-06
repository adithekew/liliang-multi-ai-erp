# PT. Liliang — Rekonsiliasi stok referensi CSV (6 November 2026)

## File yang diperiksa
- Nama: \`Liliang_Report_catalog_updated.csv\`
- SHA-256 file: \`72d38183117d4ab3a5473de20ba4a15d60df7be02e9a4e05c7ab7884ab59deb2\`
- Header CSV: \`SKU, Product, Type, Applications, Stock, Source, PDF Page, PDF Row\`
- Metadata asal: \`SUPPLIER_CATALOG_PDF_UNVERIFIED\`
- Generated UTC menurut file: \`2026-10-30T03:28:46.628726+00:00\`
- Detail sumber tiap baris: \`CATALOG-PDF-UNVERIFIED\`.

## QA import
- 1.452 SKU unik, 0 SKU duplikat.
- 1.452 numerik Stock terisi, semua bilangan bulat positif (minimum 13, maksimum 500).
- SUM kolom Stock = 373.069, **bukan KG** karena tidak tercantum unit.
- Semua 1.452 SKU berhasil dicocokkan dengan \`products.sku\` dalam Neon.
- Sebelum impor, kolom \`products.stock\` berisi angka untuk 76 SKU; 1.376 lainnya NULL.
- Data CSV diimpor secara idempoten ke **catalog_stock_reference**, bukan menimpa \`products.stock\`.
- Tabel \`catalog_stock_import_batches\` menyimpan fingerprint dan metadata sumber. Source data per SKU tidak di-commit ke repository GitHub publik.

## Evidence and governance boundary
- Stock column is **not** independently confirmed warehouse on-hand, nor approved available-to-promise.
- Unit of measure is **UNSPECIFIED**. Do **not** coerce reported stock numbers to KG, units or cartons without evidence.
- All imported records flagged \`UNVERIFIED\`.
- Existing \`products.stock\`, verified physical counts, \`sample_uat_balances\`, \`sample_uat_movements\`, commercial order records and real shipment states were **not changed** by the import.
- New read-only UI at \`/stock/reference\` and authenticated \`/v1/catalog/stock-reference\` shows CSV data with their provenance and status.
- Sales/Technical/Manager/Gudang UAT sample dispatch still **requires its isolated virtual balance** and does not take the imported CSV quantity as physical stock.

## Remaining physical-inventory validation
For a future authorized physical stock import, obtain at least: SKU, physical quantity, standardized UoM, warehouse/location, stock date/time, batch/lot (when applicable), material condition and expiry details, and signed inventory-count evidence. Reconcile company-owned inventory versus supplier catalog SKUs and require Gudang/Technical approval.

This milestone is a **data staging/import verification**, not inventory accuracy certification or financial inventory valuation.

## Source code
- \`catalog_stock_reference.py\`: reference schema, paginated API and stock page.
- \`app.py\`: safe bootstrap/mount.
- \`rich_ui.py\`: sidebar navigation.
- \`sample_flow.py\`: shows CSV reported number separately from virtual UAT KG in transaction Overview.
- \`tests/test_stock_reference.py\`: auth, provenance, separation of stocks and JavaScript syntax.
