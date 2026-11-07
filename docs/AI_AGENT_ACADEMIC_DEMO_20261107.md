# AI Agent ERP PT. Liliang — Panduan Demonstrasi Akademik

Tanggal: 7 November 2026. Scope: penelitian DSRM dan demonstrasi prototipe.

## Narasi demonstrasi (4–5 menit)

**00:00–00:40 | Konteks bisnis.** Sales menerima inquiry flavor dari pelanggan B2B. Sistem memiliki alur Sales → kandidat AI-02 → review Technical → approval Manager Operasional → Gudang. ERP dan halaman AI Agent dipisahkan agar status riset tidak disalahartikan sebagai transaksi komersial.

**00:40–01:20 | Empat modul.** AI-01 melakukan interpretasi atribut kebutuhan, AI-02 memeringkat kandidat memakai BM25 sebagai baseline, AI-03 mengeksplorasi asosiasi pembelian, AI-04 menghasilkan baseline peramalan. MiniLM dan RRF tetap merupakan eksperimen retrieval terpisah, bukan inference online yang sudah dipromosikan.

**01:20–02:30 | Groq/PydanticAI.** Buka halaman `/ai/agent-pilot`, pilih Strawberry Flavor · Dairy Beverage, dan aktifkan Groq · GPT-OSS 20B. Jalankan **AI Analysis**. Paparkan input inquiry, output empat modul dan penjelasan terintegrasi.

**02:30–03:25 | Hasil & validitas.** Contoh hasil awal: AI-01 strawberry/beverage/dairy; AI-02 SKU FLV-STRAW-01 BM25 18.3824; AI-03 strawberry→vanilla confidence 0.857; AI-04 baseline 62 unit/minggu untuk 4 minggu. Angka ini hanya untuk kasus uji terkontrol; jangan menyebutnya metrik validasi data perusahaan.

**03:25–04:20 | Jejak pemanggilan alat.** Periksa indikator `tool_trace`: empat alat baru dapat diklaim terpanggil jika catatan runtime benar-benar mengandung AI-01 sampai AI-04. Ekspor **Bukti UAT** untuk bukti akademik. Penjelasan LLM bukan pengganti pembuktian precision/recall, nDCG, relevansi Technical maupun WMAPE pada dataset riil.

**04:20–05:00 | Rencana penelitian.** Validasi inquiry–SKU berdasar expert label 0–3; evaluasi BM25/MiniLM/RRF pada held-out set; perbaiki penggunaan constraints/evidence; selesaikan pengujian bundling dan forecasting pada data yang sah; lalu evaluasi Agent (tool selection accuracy, faithfulness, latency, kuota).

## Pernyataan integritas

- Groq API bekerja sebagai lapisan LLM orkestrasi, bukan bukti empat model sudah dilatih.
- Demo memakai lima kasus pengujian yang ditentukan sebelumnya dan beberapa SKU uji, **bukan** inquiry nyata atau stok fisik perusahaan.
- Katalog dan stok operasional PT. Liliang memiliki sumber serta izin tersendiri; indikator kesiapan stok ERP pada dashboard hanya dibaca sebagai ringkasan dan **tidak dikirim ke Groq**.
- Technical masih harus memverifikasi kesesuaian produk, regulatory, halal, dan datasheet; Manager memegang approval.
- Snapshot JSON asli (termasuk penanda sumber) tetap dipertahankan dalam ekspor bukti sehingga laporan akademik dapat diaudit.
- Tidak ada pengiriman sampel atau penurunan stok fisik yang dipicu Agent pada tahap ini.

## Source code demonstrasi

- `agent_pilot.py`: kontrak API, batas peran, fungsi AI, Groq tool orchestration, jejak tool call.
- `agent_dashboard_ui.py`: UI hasil terstruktur, tanpa menampilkan payload JSON mentah secara default.
- `multi_ai.py`: fungsi baseline AI-01 sampai AI-04.
- `research/`: protokol retrieval neural, evaluasi ranking, dan eksperimen.
- `tests/test_agent_academic_demo.py`: validasi JavaScript, empat panel dan pernyataan sumber.
- `tests/test_agent_pilot.py`: autentikasi, kontrak hasil, dan proteksi tidak mengubah transaksi.

## Catatan tampilan

Halaman untuk presentasi menggunakan terminologi **dataset pengujian terkontrol** yang tidak ditonjolkan sebagai judul besar, tetapi fakta sumber dan ketidaktersediaan validasi ilmiah tetap ditampilkan. Tujuannya agar dosen mendapat kesan profesional tanpa mengganti makna akademik.
