# P7 — Demo operasional ERP Multi-AI, bukti penerimaan dan skenario cadangan

**27 Oktober 2026 — capstone PT Liliang, Kelompok 3.**
**Klasifikasi:** deliverable P7 selesai (journey, matriks kompetensi, assessment, dashboard wireframe, UI, review heuristik internal). Bukan hasil belajar cohort / kelayakan model AI.

## A. Pemeriksaan live yang benar-benar dijalankan
- Pemeriksaan HTTP via browser 27 Okt 2026: `/healthz` **HTTP 200** (`status:ok`, `persistent_database:true`, `database_backend:postgresql`); `/readyz` **HTTP 200**, `ready:true`.
- Route publik `/learning/center`, `/inquiries`, `/ai/status`, `/` dan `/branding/logo` **HTTP 200** dengan branding PT Liliang.
- **Penting:** `/learning/center` yang belum login secara sengaja menampilkan halaman login. Konten Learning Center dan kuis akan tampil **setelah login UAT yang sah**. HTTP 200 di publik tidak membuktikan lima-role UAT interaktif.
- Repo sudah memiliki regresi end-to-end dengan database sementara (`tests/test_pilot.py`): Admin membuat empat role, Sales buat inquiry sintetis → BM25 Top-5, Technical label 0/3, Manager tidak bisa approve sebelum review, Gudang terblokir dari metadata inquiry, PDF/CSV report, access guards. UAT ini **bukan** uji manusia terhadap Render/Neon; bukan skor akurasi AI-02.
- *Demo gate* tambahan memastikan `/learning/center` memuat navigasi serta materi lima role dan kuis lokal tanpa persistensi.

## B. Review heuristik internal P7 — diterapkan ke slide
| Aspek | Temuan | Penyelesaian P7 |
|---|---|---|
| Navigasi role | Role berasal dari akun login, bukan dropdown role | Slide demo diperbaiki agar login UAT Sales lebih dulu |
| Risiko cold start | Render Free sempat 503 sebelum sehat | Prewarm dan cek `/healthz` + `/readyz` sebelum paparan |
| Safety eksperimen | Katalog perusahaan belum diverifikasi penuh | Demo hanya data sintetis/berizin dan inquiry UAT anonim; stok tidak diubah |
| Claim AI | BM25 online ≠ neural AI terlatih; MiniLM+RRF offline lab | Jelaskan status tepat pada slide & UI, tidak berikan angka accuracy rekaan |
| P7 learning KPI | Dashboard merupakan desain indikator tanpa pengukuran peserta | Tandai spesifikasi selesai; hasil numerik hanya setelah studi pengguna berizin |
| User feedback | Review internal berbeda dari sign-off pakar/pengguna | Register heuristik ini sebagai review internal; external participant study menjadi P8/P11 |

**Keputusan:** artefak milestone P7 **SELESAI dan sudah submitted for grading**. Tidak ada label Draft/Pending pada matriks P7. Sign-off pengguna/pengukuran nyata tidak digantikan dengan bukti buatan.

## C. Preflight wajib sebelum presentasi — 10–15 menit sebelumnya
1. Nyalakan Render Free dengan akses `https://liliang-multi-ai-erp-pilot.onrender.com/healthz` lalu `/readyz`; verifikasi JSON 200/PostgreSQL. Bila 503, ulangi beberapa saat; jangan memulai demo transaksi.
2. Siapkan **akun UAT yang telah dibuat** di jendela/profil browser yang berbeda untuk **Sales, Technical, Manager Operasional**. Login dan prewarm *ketiganya* saat di luar layar presentasi; jangan bagikan password. Perhatikan timeout idle 15 menit; lakukan navigasi aktif beberapa menit sebelum paparan.
3. Buka `/learning/center` menggunakan akun Sales. Karena login dinamis, halaman publik akan tampak seperti login sampai sesi aktif.
4. Buka inquiry UAT sintetis yang sudah tersimpan dengan Top-5 yang benar-benar ada, catat nomor inquiry dan run ID; cek latest-match dan insight, jangan gunakan transaksi perusahaan nyata.
5. Siapkan screenshot dari revisi UAT dengan bukti grade Technical 3 dan approval Manager. Jika belum ada test data yang memadai, **tampilkan alur berurutan dan batas validasi, tanpa melakukan perubahan stok/approval perusahaan**.
6. Tab bukti `/ai/evidence` dan `/ai/data-readiness` hanya setelah login role Admin/Technical/Manager. Jangan menampilkan informasi identitas pelanggan atau tab password.
7. Siapkan deck PDF offline dan video/screenshot cadangan pada komputer presenter (rencana, belum dinyatakan sudah direkam).

## D. Script aman 4 menit 30 detik
- **00:00–00:40:** Sales UAT login sebelumnya → buka Learning Center; tunjukkan learning journey per role.
- **00:40–01:25:** Inquiry UAT tersimpan → BM25 Top-5 + insight dan pembacaan UNKNOWN/NO_MATCH.
- **01:25–02:10:** Buktikan aturan label Technical 0–3, grade 3 ACCEPT baru memungkinkan approval Manager. Gunakan bukti UAT pada database uji, bukan data pelanggan.
- **02:10–02:55:** Kuis tiga soal berjalan lokal, dashboard menampilkan *definisi KPI* bukan nilai pengguna.
- **02:55–03:40:** Research Evidence menjelaskan approval/labelling gate dan judged holdout E1–E5; belum ada validasi akurasi ilmiah.
- **03:40–04:30:** Matriks capaian P7, kerja tim P8, dan timeline paper.

## E. Fallback / STOP
| Kondisi | Langkah |
|---|---|
| Healthz/readyz gagal atau 503 berulang | **NO-GO transaksi langsung:** presentasikan screenshot dan PPTX/PDF, simpan log waktu/status |
| Login expired (401) | Login ulang *off-screen*, jangan ketik password pada proyektor |
| Katalog tak memuat SKU tepat | Jangan pilih SKU palsu; gunakan screenshot UAT tervalidasi dan jelaskan NO_MATCH |
| Login role tidak tersedia | Demo wireframe dan bukti CI; jangan klaim real five-role live UAT |
| Technical review belum ada bukti ahli independen | Jelaskan dua jenis review: UAT workflow vs gold label ilmiah, jangan campur |
| Setiap upaya mengubah stock atau order perusahaan | **STOP**; gunakan lingkungan tes sementara yang tidak bersumber dari Neon |

## F. Penutupan riset
Kriteria bukti untuk P8 tetap terpisah: demo Sprint-1, link source code & pembagian modul, bukti API/data/model, screenshot pengujian, daftar blocker dan rencana penanganan. Penulisan paper berfokus AI-02: E1 BM25, E2 dense, E3 RRF hybrid, E4 gated fine-tuned, E5 evidence + expert-in-loop, nDCG@5/MRR@5/Recall@5 pada frozen holdout berlabel pakar dan berizin. Angka hasil penelitian belum diklaim.
