# Five-role UAT, catalog migration and audit (v0.7)

This pilot uses Render Free and Neon PostgreSQL. Do NOT commit company catalogs, customers, transaction history, secrets or passwords to the public repository.

## User account bootstrap
Admin logs in, opens UAT Role Accounts, and creates the four additional UAT accounts: Sales, Technical, Manager Operasional and Gudang. Passwords are generated randomly by the server, stored only as Argon2 hashes and displayed once over HTTPS to the logged-in Admin. The .local accounts are for UAT, not employee mailboxes. Test independent login for each role.

## Workflow
Sales creates inquiry and runs BM25 Top-5. Technical gives a 0-3 relevance label, ACCEPT/REJECT/NEEDS_INFO and a rationale. Manager may approve only after Technical ACCEPT. Gudang can update inventory. Audit Transactions records successful login and each business mutation: actor, role, timestamp, entity, event ID, before/after metadata SHA-256. The audit does not store plaintext passwords, tokens or full customer requirements.

## Archive and reset
Admin opens Catalog Migration and explicitly enters RESET DEMO ONLY, then confirms. The service atomically snapshots products, inquiries, runs, candidates and reviews in reset_archives before deleting only those demo rows. User accounts and audit logs stay. A non-demo product or imported catalog blocks the reset. The archive marker prevents restarting the demo seed.

## Supplier PDF cleansing
The user-supplied PT Li Liang catalog contains 65 pages and 1,455 numbered entries. The prepared local JSON has 1,452 unique import-ready SKU entries, with three quarantined source rows:
- 1265 and 1355: duplicate code 21200911, conflicting names Seafood Oil Flavor and Fish Oil Flavor; neither is imported.
- 1370: exact duplicate code 41100625 of row 84; one record retained.
- Three otherwise ready SKU rows have no percentage text; remain empty without invented values.

Import via Admin Catalog Migration using the downloadable catalog_import_ready.json file. Upload is private and authenticated over HTTPS; repository contains no user-provided catalog dataset. The import is transactional into empty product catalog, preserving raw type, application, percentage, page, and source row. Supplier percentages are not chemical formulation certifications. Imported stock is NULL/UNKNOWN, not a fabricated zero. Regulatory/halal suitability remains UNKNOWN pending evidence. Product PDF is not historical company sales.

## AI research integrity
BM25 online matching uses the active catalog but still requires Technical review. MiniLM 384D and RRF are a fixed offline synthetic neural benchmark that remains separated from real catalog records. AI-03 bundling and AI-04 forecasting remain synthetic until actual authorized historical sales exist. No claimed expert-validated scientific accuracy or real company fine-tuning.

## Verification
GitHub CI runs browser JavaScript syntax checks, SQLite tests, and PostgreSQL regression tests for all role logins, inquiry/match/review/approve/stock workflow, audit recording, reset/archive, duplicate import refusal, catalog persistence and fixed neural benchmark isolation. Live Admin actions are required before any destructive reset or data upload.
