# PT. Liliang ERP Multi-AI — Weekly Capstone Update (23 Oktober 2026)

**Program:** Magister Teknik Informatika, Universitas Pradita  
**Mata kuliah:** IT40513 Enterprise Architecture & Digital Blueprint  
**Kelompok:** 3 — kontribusi topik ERP Multi-AI PT. Liliang  
**Periode laporan:** 16–23 Oktober 2026  
**Format:** 22-slide presentation and speaker notes.

## Berkas pengumpulan resmi

- [PowerPoint asli — 22 slides, editable](https://docs.google.com/presentation/d/1n0TulHPVLWHUBMm-gmALBJEQCoIUE2VR/edit)
- [PDF asli — 22 slides](https://drive.google.com/file/d/1qDwD0oGrw8mgf_-JT1KLcU00NQ4sRSBM/view)
- [Google Slides — ringkasan 22 slides, editable online](https://docs.google.com/presentation/d/1sao9LQOE8YcBKOpIp60idlk0qL2SR2vWuB6BBT9j8Zs/edit)
- [PDF panduan presenter](https://drive.google.com/file/d/1ug2j7r1pQ1i943TYPfuYMroyv0CNg3vI/view)
- [Catatan pembicara Google Docs](https://docs.google.com/document/d/1hGOjirRWTnCoQe9Y9Z7kfDCMfxVGgbTiGShFSZdFW-o/edit)
- [Indeks pengumpulan Kelompok 3](https://docs.google.com/document/d/1KS0MC8_HycF6UzH_QSqNKuumWtBiEWXRr4YVxtRI7Bo/edit)

### Integritas berkas asli

| Berkas | SHA-256 |
| --- | --- |
| `PT_Liliang_Capstone_Weekly_Update_23_Oktober_2026.pptx` | `13622182ff2c9ac1bbf971a23361f4d8bbff21fe1d2aa0024856b38300005912` |
| `PT_Liliang_Capstone_Weekly_Update_23_Oktober_2026.pdf` | `589bdb8bc4a9940420e575d6afb521b6d4968d332a4b552b2b2d565ec5912b6f` |
| `PT_Liliang_Panduan_Paparan_Malam_23_Oktober_2026.pdf` | `b8f20d9c54187ad9fa5749598b9774243979929e54040b6f5fd9825a3299b9fa` |

## Ringkasan progres tim, capstone, dan aplikasi

1. **Pekerjaan 16–23 Oktober:** perapihan arsitektur, matching BM25 serta insight SKU, ekstraksi sales 2025, tiga laporan UAT, dan PR #20/#21 untuk remediasi. Atribusi individu belum diverifikasi.
2. **Capaian capstone:** blueprint end-to-end, alur lima role, katalog PDF pemasok 1.452 SKU di Neon (UNVERIFIED), baseline AI-01/02, ekstraksi item penjualan dan quality gate untuk penelitian.
3. **Update aplikasi:** login dan RBAC lima role, BM25 online, 12 report PDF/CSV, branding, pembatasan Gudang, guard review/approval dan audit; CI + live smoke PASS.
4. **Batas kesiapan:** AI-03/04 masih contoh sintetis; MiniLM + RRF hanya offline fixed-query lab; data penjualan 2025 belum direkonsiliasi Finance; WMS ledger/laporan belum dikembangkan sepenuhnya; label Technical independen dan held-out testing masih diperlukan.

## Isi 22 slide (outline tekstual, identik secara substansi dengan versi Google Slides)

### Slide 01 — ERP Multi-AI PT. Liliang International

PAPARAN CAPSTONE — 23 OKTOBER 2026


Magister Teknik Informatika · Universitas Pradita


Progres tim, arsitektur ERP, AI/ML, data engineering, dan User Acceptance Test.


Fokus riset: AI-Assisted Semantic Product Matching untuk inquiry flavor B2B.

### Slide 02 — Executive Update: Evidence vs Claims

KODE: CI dan tes PostgreSQL lulus; temuan UAT diremediasi dalam PR #20 dan #21.


DEPLOYMENT: Render live smoke PASS untuk health, branding, dan revisi UI.


RISET: Validasi pakar independen dan eksperimen held-out belum tersedia.


Kesimpulan: pilot operasional teruji; presisi ilmiah belum boleh diklaim.

### Slide 03 — Pekerjaan Tim: 16–23 Oktober 2026

16–18 Okt: finalisasi ruang lingkup, alur bisnis lima role, arsitektur data/API/cloud/AI.


19–20 Okt: perbaikan AI-02 BM25, insight tiap kandidat, logo, dan regresi relevansi.


21–22 Okt: ekstraksi data penjualan 2025; tiga UAT lintas role.


23 Okt: perbaikan RBAC, validasi Technical, audit, stok, dan CI/live smoke.


Atribusi kontribusi individu masih perlu konfirmasi tim.

### Slide 04 — Capaian Capstone Mingguan

1. Arsitektur end-to-end: FastAPI + Render + Neon + komponen AI.


2. Workflow lima role dengan expert-in-the-loop dan audit.


3. Katalog 1.452 SKU tersimpan, masih UNVERIFIED.


4. AI-01 rule NLP dan AI-02 BM25 berjalan online.


5. Ekstraksi 1.016 item penjualan; bagian Juni (91) dipisah.


6. UAT dan perbaikan kode dengan bukti CI.

### Slide 05 — Update Aplikasi ERP Multi-AI

SUDAH AKTIF: login lima role, katalog Neon, inquiry/matching BM25, insight SKU, logo, 12 report PDF/CSV.


REMEDIASI: satu matching run; validasi label 0–3; guard Manager; audit 403/409; pembatasan Gudang; referensi stok fisik.


BELUM: MiniLM online penuh, training dengan label perusahaan, AI-03/04 berbasis invoice nyata, serta WMS lengkap.

### Slide 06 — Bukti UAT dan Readiness Dataset

UAT: 24/24, 16/16, dan 9/9 skenario dinyatakan PASS dengan catatan; ini pengujian workflow.


EKSTRAKSI 2025: 1.107 baris item total, 1.016 bagian penjualan, 91 baris Juni terkait jatuh tempo (bukan otomatis penjualan), 209 SKU tertulis.


DATA LANJUTAN: inquiry berizin, label Technical 0–3, SO/invoice asli, tanggal/retur, stok & lead time.

### Slide 07 — Penelitian: Masalah dan Tujuan

Masalah: pencarian manual flavor B2B memerlukan interpretasi kebutuhan pelanggan, sinonim ID/EN, variasi ejaan, bentuk fisik, dan aplikasi produk.


Target bisnis: dari pencarian manual >2 jam ke shortlist hitungan detik.


Target tersebut masih hipotesis, belum hasil uji lapangan.


Evaluasi: relevansi Top-5, waktu pencarian, pelanggaran constraints, dan kemudahan audit.

### Slide 08 — Human-in-the-Loop: Lima Role ERP

Sales membuat inquiry dan konfirmasi profil/bentuk flavor.


AI-01 memetakan atribut; AI-02 BM25 memberi shortlist Top-5 atau NO_MATCH.


Technical memberi label 0–3, alasan dan memeriksa evidence.


Manager memutuskan APPROVE atau RETURN sesuai review.


Gudang menangani data katalog/stok tanpa akses detail inquiry.


Admin mengelola user, audit dan laporan.

### Slide 09 — Arsitektur Sistem End-to-End

FRONTEND: aplikasi multi-page di browser; sesi dan RBAC lima role.


APPLICATION/API: FastAPI, workflow inquiry, matching, keputusan, insight, reports, audit.


DATABASE: Neon PostgreSQL untuk katalog SKU dan transaksi.


AI: BM25 di runtime; MiniLM 384-D hanya eksperimen offline.


OPS: Render Free, healthz/readyz, CI, live smoke dan observability.

### Slide 10 — Data Governance & Lineage

Katalog pemasok: 1.452 SKU dari PDF, belum diverifikasi Technical; status halal/regulasi/formulasi = UNKNOWN tanpa dokumen.


UAT: inquiry/review untuk uji alur, bukan ground truth penelitian.


Sales history 2025: sudah diekstraksi, belum direkonsiliasi terhadap SO/invoice/retur.


Prinsip: provenance, izin, anonimisasi, pemisahan data sintetis vs perusahaan, dan audit.

### Slide 11 — AI-01: Requirement Interpreter

INPUT: misalnya 'butuh bubuk rasa strowbery untuk bakery, tidak boleh liquid'.


NORMALISASI: ejaan dan istilah bilingual.


ATRIBUT: flavor=strawberry; form=powder; application=bakery; negative constraint=not liquid.


Implementasi sekarang: rule-based NLP yang interpretabel.


Belum menggunakan LLM ataupun supervised fine-tuning perusahaan.

### Slide 12 — AI-02: Product Matching BM25

1. Parse dan normalisasi flavor/form/aplikasi.


2. Penerapan hard constraints agar mismatch eksplisit ditolak.


3. BM25 pada katalog aktif untuk ranking kandidat.


4. Tampilkan insight dan alasan/risk per SKU.


5. Technical menilai 0–3 sebelum keputusan Manager.


BM25 score = kemiripan leksikal, bukan probabilitas akurasi.

### Slide 13 — AI-02: Hybrid MiniLM + RRF

Baseline BM25: online untuk inquiry teks bebas.


Multilingual MiniLM: pretrained embeddings 384-D pada 10 query / 5 produk sintetis, dihitung offline.


RRF(k=60): gabungan peringkat leksikal dan dense dalam eksperimen tetap.


Belum tersedia online neural inference pada 1.452 SKU dan belum ada evaluasi pakar independen.

### Slide 14 — AI-03 dan AI-04: Use Case Pendukung

AI-03 PRODUCT BUNDLING: association rules support/confidence/lift, saat ini 16 keranjang sintetis. Perlu order_id asli, baris pembelian, status dan retur.


AI-04 DEMAND FORECAST: baseline moving average 4 minggu dengan data simulasi 24 SKU-week. Perlu histori harian/bulanan nyata dan backtest temporal.


Keduanya bukan model produksi terlatih perusahaan.

### Slide 15 — Data Engineering untuk Penelitian

SOURCE: katalog supplier + inquiry berizin + histori pesanan.


CLEAN: validasi kolom, normalisasi bilingual, missing, duplikat, outlier.


LINK: SKU, alias produk, taxonomy dan dokumen pendukung.


LABEL: Technical relevansi 0–3.


SPLIT: berdasarkan customer/proyek dan waktu untuk mencegah leakage.


VERSION: hash dataset, provenance dan audit.

### Slide 16 — Strategi Model, RAG, dan Fine-Tuning

Saat ini: rule-based NLP + BM25 sebagai baseline interpretable.


RAG berbasis COA, datasheet, halal/MSDS hanya jika dokumen resmi tersedia dan penggunaannya diizinkan; hasil harus mencantumkan sumber.


Fine-tuning bi-encoder hanya jika pasangan inquiry–SKU berlabel independen dan held-out split cukup.


Jangan mengadopsi LLM tanpa nilai eksperimen.

### Slide 17 — Desain Eksperimen E1–E5

E1 BM25 baseline; E2 frozen dense MiniLM; E3 hybrid BM25+dense RRF;


E4 fine-tuned encoder (bersyarat dataset); E5 constraints + expert-in-loop.


Uji pada inquiry dan label pakar independen yang sama.


Metrik: nDCG@5, MRR@5, Recall@5, P50/P95 latency, time-to-shortlist, violations, agreement reviewer.


Belum ada hasil held-out valid.

### Slide 18 — Runbook Demonstrasi

1. Login sebagai Sales; bukti logo, sesi, dan menu berbasis role.


2. Buat inquiry anonim dengan rasa, aplikasi, serta bentuk yang dikonfirmasi.


3. Jalankan matching satu kali; lihat Top-5/NO_MATCH + insight.


4. Technical memberi relevansi 0–3 dan alasan.


5. Manager menyetujui hanya kandidat ACCEPT label 3.


6. Admin cek laporan dan audit; Gudang tetap tanpa detail inquiry.

### Slide 19 — Risk Register dan Quality Gates

HIGH: katalog 1.452 SKU belum expert-verified → validasi datasheet/Technical.


HIGH: label pakar independen belum siap → rubrik dan adjudikasi.


HIGH: AI-03/04 masih sintetis → validasi invoice dan temporal split.


MED: MiniLM hanya fixed fixture → eksperimen corpus/test set riil.


MED: UI/deployment regressions → GitHub CI, live smoke, UAT lima role.

### Slide 20 — Kesimpulan dan Next Action

TERSEDIA: alur lima role, katalog Neon, AI-01 & BM25 online, insight kandidat, branding, laporan, audit, sales history 2025 diekstraksi, PR #20/21 PASS.


LANJUTAN: expert labels, konfirmasi data Juni dan SO/invoice, eksperimen E1–E5, pengukuran latency/waktu pencarian, desain WMS ledger + laporan, re-UAT sign-off.


Fokus riset tetap semantic product matching.

### Slide 21 — Pertanyaan Kritis untuk Dosen

AI sudah ditraining? MiniLM pretrained diuji offline pada data sintetis; belum fine-tuning perusahaan.


Akurasi? Belum ada nDCG@5/MRR@5 held-out yang sah.


Kenapa tidak LLM? BM25 dapat diaudit; RAG jika datasheet valid.


Apakah bundling/forecast nyata? Masih simulasi; histori 2025 baru diekstraksi dan perlu rekonsiliasi.

### Slide 22 — Traceability: Bukti & Sumber

Repo: github.com/adithekew/liliang-multi-ai-erp


Branding: PR #19; UAT remediasi: PR #20 dan #21.


Live smoke: github.com/adithekew/liliang-multi-ai-erp/actions/runs/39928474643


CI: github.com/adithekew/liliang-multi-ai-erp/actions/runs/39928474701


Metodologi: docs/AI_TRAINING_EVALUATION_PROTOCOL.md dan docs/HYBRID_SEMANTIC_RESEARCH.md


UAT sukses ≠ validasi presisi.


## Evidence GitHub

- [Branding PR #19](https://github.com/adithekew/liliang-multi-ai-erp/pull/19)
- [UAT remediation PR #20](https://github.com/adithekew/liliang-multi-ai-erp/pull/20)
- [UAT follow-up Feri PR #21](https://github.com/adithekew/liliang-multi-ai-erp/pull/21)
- [CI PASS](https://github.com/adithekew/liliang-multi-ai-erp/actions/runs/39928474701)
- [Live revision smoke PASS](https://github.com/adithekew/liliang-multi-ai-erp/actions/runs/39928474643)

**Research integrity:** UAT PASS ≠ validated model accuracy. Do not publish company financial line-items, credentials, customer identities, or private Technical data into this public repository. The sales 2025 extracts remain outside the public submission package until authorization, minimization and anonymization.
