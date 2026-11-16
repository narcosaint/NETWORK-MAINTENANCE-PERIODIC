# Architecture V2 — Audit & Alignment (Phase 1)

Tanggal audit: 13 November 2026. Status: hasil audit source dan usulan untuk review;
bukan implementasi Phase 2 atau persetujuan migration/deployment.

## Cakupan dan bukti

Acuan utama: `AGENTS.md` dan `docs/ROADMAP-V2.md`. Roadmap tetap dipertahankan.
Gambar yang tersedia adalah `docs/design/hotel-maintenance-ui-reference.png.png`
(ekstensi ganda), bukan path `.png` dalam permintaan. Gambar telah diperiksa visual.
Dokumentasi lama (`NAVIGATION.md`, `SAMPLING_AUDIT.md`, `TEMPLATE_MAPPING.md`,
`SPEEDTEST.md`) dipakai sebagai konteks, lalu dicocokkan dengan source sekarang.
Istilah Phase A/B dalam dokumen sampling lama bukan penanda selesainya fase V2.
Jika berbeda, roadmap V2 dan instruksi saat ini menjadi acuan.

Audit database terbatas pada SQLAlchemy dan sembilan file migration sampai
`0009_site_report_profile`. Tidak mengakses database berjalan, tabel pelanggan,
credential, atau `alembic_version`; kesesuaian schema produksi belum diverifikasi.
Tidak menjalankan server, migration, Docker, speedtest nyata, atau deployment.
Penilaian visual existing didasarkan pada markup/CSS; bukan uji screenshot live.

## Arsitektur existing

| Lapisan | Kondisi source | Bukti utama |
| --- | --- | --- |
| Web | HTML/CSS/JavaScript biasa, tanpa bundler/framework React; state dan navigasi di browser | `backend/app/web/index.html`, `app.js` |
| Penyajian | FastAPI menyajikan `/` dan `/assets`; API satu origin | `backend/app/main.py` |
| Backend | FastAPI, Pydantic, SQLAlchemy; auth bearer, peran technician/supervisor | `api.py`, `security.py`, `schemas.py` |
| Data | PostgreSQL melalui psycopg; migration Alembic | `database.py`, `config.py`, `models.py`, `database/migrations/` |
| Laporan hotel | Penugasan, check-in/out, laporan JSON, snapshot perangkat, foto privat, revisi dan approval | `hotel_api.py`, `hotel_schemas.py` |
| Sampling web | Dashboard/lantai/detail titik, tab analyzer/speedtest/foto; sebagian state hanya lokal | `sampling.js`, `sampling-service.js`, `hotel-detail.js` |
| Speedtest | Worker LibreSpeed vendored dan endpoint transfer FastAPI; run dan provenance tersimpan | `speedtest.js`, `speedtest_api.py`, `web/librespeed/SOURCE.json` |
| Android | Tidak ditemukan package React/Capacitor, Gradle atau plugin Kotlin/Java | Inventaris file repository |
| Offline | IndexedDB untuk konfigurasi lantai, draf catatan dan Blob foto; belum sinkronisasi end-to-end | `sampling-service.js`, `sampling.js` |

Token web berada di memori. Foto server diambil melalui akses terautentikasi;
file foto dikelola melalui storage backend. API menerapkan pembatasan akses dan
versi laporan (`expected_version`) untuk konflik. Draf IndexedDB dipisahkan dengan
key akun/hotel/visit/titik, tetapi bukan enkripsi atau pemisahan akses tingkat OS.
Data lokal masih ada setelah logout. Membuka aplikasi ulang tanpa server belum
didukung sebagai aplikasi offline penuh.

Dua domain kunjungan hidup berdampingan: `visits` berbasis jadwal perangkat lama,
dan `hotel_visits` berbasis hotel. Jangan menyamakan ID keduanya. Domain hotel
menjadi basis V2; jalur perangkat tetap untuk kompatibilitas dan histori.

## Kesesuaian roadmap dan referensi UI

| Area | Sudah tersedia | Perbaikan / belum tersedia |
| --- | --- | --- |
| Sidebar | Lima menu utama sesuai roadmap; menu perangkat lama tidak masuk `mainPages`; Tim Teknisi dibatasi supervisor | Pertahankan handler/API lama dan kontrol peran |
| Ringkasan | Total hotel, kunjungan aktif, menunggu review, PM hotel selesai | Belum KPI lengkap bulan berjalan, tertunda, total temuan dan progress teknisi |
| Maintenance Hotel | Pilih hotel, filter periode, penugasan, akses laporan dan sampling | Belum tampilan terpadu sesuai referensi: progress total, kartu KPI, baris lantai expandable dan ringkasan metrik |
| Detail Hotel | Tab Lantai, Perangkat, Titik Sampling, Riwayat Maintenance; nama/alamat di header | Tab Informasi Hotel belum ada; lantai/target hanya konfigurasi lokal; rename/urutan master belum lengkap |
| Sampling | Default target empat per lantai, detail titik dan tiga tab | Placeholder bukan titik tersimpan; master antarperangkat dan progress resmi belum tersedia |
| Connected Network | Kartu menyatakan unavailable secara jujur | SSID/BSSID/frequency/channel/band/RSSI/link speed/IP/gateway aktual dan pencocokan AP belum tersedia |
| Wi-Fi scanner | Pilihan band 2.4/5 GHz, empty state | Tidak ada native scan, jumlah jaringan, grafik, overlap atau persistence scan |
| Speedtest | Download/upload/ping/jitter, start/finish/apply, konteks dan riwayat | Terikat AP kunjungan; belum jaminan tiap titik fisik, native Wi-Fi binding dan syarat submit per titik |
| Foto/catatan | Upload foto perangkat server; thumbnail dua kolom serta catatan/foto sampling lokal | Kategori/caption lokal belum tersinkron; dokumentasi visit mandiri dan temuan terstruktur belum tersedia |
| Review/PIC/PDF | Check-out, revisi, submit ulang, approval supervisor dan event snapshot | PIC memakai alasan pengecualian tanda tangan; belum review PIC, signature image atau generator PDF |
| Integrasi lanjutan | Tidak ditemukan implementasi Google Sheets/Drive | Target Phase 7, tidak dikerjakan sekarang |

Referensi web menampilkan sidebar hijau tua, bidang terang, aksen hijau/toska,
kartu statistik lantai/titik/selesai/temuan, chip lokasi dan progress per lantai.
CSS existing sudah mempunyai sidebar gelap dan card responsif; modul sampling
masih mempunyai aksen biru/navy dan susunan berbeda. Penyelarasan perlu menjaga
tema hijau existing serta alur hotel → periode/visit → lantai → titik.

Referensi Android menampilkan header konteks, Connected Network, band selector,
grafik channel, metrik speedtest, dua foto dan catatan. Roadmap menambahkan tiga
tab detail dan informasi lebih lengkap; gabungkan hierarki visual referensi dengan
tab roadmap. Angka/nama hotel/AP, kurva sinyal, persentase perubahan dan foto dalam
gambar hanya contoh desain. Jangan dijadikan seed, hasil pengukuran atau default
produksi. Grafik/tren hanya muncul ketika data aktual dan pembanding tersedia.

## Template Nusanet dan validasi existing

`hotel_schemas.py` menyimpan PIC/kontak, customer, backbone FO/wireless, LAN,
ringkasan, status pekerjaan, feedback dan solusi. Field legacy seperti agreement,
speedtest, signal, TX/RX dan CCQ tetap ada. Form versi 2 memakai profil SLA hotel,
download/upload, perhitungan conformity server dan `link_test_radio`.
Komponen `maintenanceItem` memberi nomor huruf otomatis, dropdown dan label
“Keterangan” terpisah; pola ini harus dipertahankan. Jangan menghilangkan field
legacy saat menyelaraskan tampilan. Kualitas link wireless belum mempunyai enum
terstruktur tersendiri. `docs/TEMPLATE_MAPPING.md` menyediakan pemetaan PDF;
audit ini tidak memvalidasi ulang PDF asli yang dirujuk dokumen tersebut.

`hotel_api.complete()` memvalidasi laporan, alasan pending, PIC/pengecualian,
backbone/LAN, minimal satu AP, outcome, foto server dan hasil/alasan band AP.
Validasi belum memeriksa seluruh lantai/titik yang direncanakan karena master
tersebut belum ada. Nilai bandwidth manual masih bisa memenuhi aturan existing;
tidak ada syarat keberadaan run LibreSpeed sukses atau gagal beralasan pada setiap
titik. Foto lokal tidak memenuhi kewajiban foto server. Approval supervisor tidak
setara dengan persetujuan PIC, dan approval pekerjaan pending bukan PM selesai.

Status workflow existing: `assigned`, `in_progress`, `submitted`,
`revision_requested`, `approved`; status pekerjaan: `completed`/`pending`.
Status sampling lokal: `untested`, `good`, `attention`, `problem`.
Kelima status roadmap perlu proyeksi tampilan terpisah, bukan mengganti enum API:

| Label V2 | Usulan dasar proyeksi |
| --- | --- |
| Belum Dikerjakan | `assigned` |
| Dalam Proses | `in_progress`; pekerjaan pending ditandai terpisah |
| Perlu Review | `submitted` atau `revision_requested`, dengan detail alasan |
| Selesai | Pekerjaan completed, pemeriksaan lengkap dan approval sesuai kebijakan |
| Selesai dengan Temuan | Syarat selesai terpenuhi dan ada temuan aktual |

Aturan prioritas label dan apakah PIC wajib sebelum approval harus direview.
Jangan menghitung status terakhir dari catatan lokal yang belum tersinkron.

## Audit API dan batas integrasi

| Kelompok | Kontrak existing |
| --- | --- |
| Auth/master | `/auth/login`, `/auth/logout`, `/auth/me`; CRUD `/hotels`, `/devices`, `/users`, `/schedules`; `/checklist-templates` |
| Legacy | `/visits`, detail, check-in/out, checklist, template, resubmit, review, history; `/schedules/{id}/progress` |
| Hotel | `/hotel-visits`, detail, check-in/out, report, samples tambah/hapus, devices/{item}/result, photos, resubmit/review/history |
| Speedtest | POST `/hotel-visits/{id}/devices/{item}/speedtests`; `/network-speedtests/{run}/finish`, GET run; POST apply pada perangkat/visit; transfer ping/download/upload |
| Kesehatan | `/health`, `/health/db` |

Route web adalah state JavaScript, bukan URL router SPA. Daftar API mendukung
pagination offset/limit; agregat dashboard harus memakai seluruh cakupan data yang
diizinkan, bukan menganggap halaman pertama sebagai total global.

LibreSpeed sudah nyata di source, bukan sekadar tombol mock. Namun `radio_verified`
masih false dan hasil `browser_reported`. `hotel_wifi` memakai konfirmasi pengguna
dan observed type browser; bukan pembuktian native. Apply mensyaratkan completed,
direct HTTPS sesuai origin terkonfigurasi, Wi-Fi terkonfirmasi dan item/aktor cocok.
Run tunnel/local hanya diagnostik. Status failed/aborted tidak menyimpan metrik
selesai, tetapi alasan gagal belum wajib untuk semua jalur input. Kuota/tiket run
aktif berada di memori proses; restart/multiworker perlu analisis kemudian.
Tidak mengubah jaringan/origin untuk mengatasi batas ini dalam Phase 1.

## Arsitektur target dan kontrak tambahan (usulan)

Pertahankan FastAPI/PostgreSQL/Alembic dan web vanilla existing. Android terpisah
memakai React + Capacitor dengan API/domain backend yang sama. Plugin native
Kotlin/Java mengumpulkan WifiManager/API terkait, permission, waktu/source scan
dan transport aktual. Nilai tidak tersedia tetap unavailable, bukan nol/simulasi.
AP tak cocok BSSID menampilkan “AP Belum Teridentifikasi”.

Gunakan master hotel → lantai → titik; snapshot sesi per hotel_visit/periode
membekukan cakupan pekerjaan bulanan. Inventaris AP opsional pada titik/sesi:
satu AP dapat melayani beberapa lokasi. Hasil connection, scan, speedtest dan foto
harus mengikuti sesi titik aktif. Detail rancangan ada di `DATABASE-GAP-V2.md`.

Kandidat API additive, belum dibuat:

- Master lantai/titik per hotel: tambah/ubah nama, lokasi, urutan, target default
  empat; archive tanpa memutus histori.
- Sesi titik per hotel visit: daftar cakupan, hasil, progress dan riwayat; validasi
  hotel/lantai/titik/visit pada server.
- Hasil connection/scan native: source, waktu pengamatan, permission dan transport;
  jangan menerima data browser sebagai pengukuran native.
- Speedtest per sesi: gunakan ulang worker/transfer, tambah asosiasi sesi,
  status gagal beralasan dan pencatatan temuan. Kebijakan latest/accepted run jelas.
- Dokumentasi visit dan sampling, catatan/temuan/tindakan/rekomendasi; upload foto
  privat dengan UUID dan idempotency.
- Agregat dashboard dan pre-submit validation; review PIC/signature; PDF versi
  laporan immutable. Implementasi mengikuti fase masing-masing.
- Sinkronisasi batch/resume dengan UUID klien, expected_version, acknowledgment
  per operasi, konflik eksplisit dan retry idempotent; Blob diunggah terpisah.

## Dampak dan prioritas setelah persetujuan

Phase 2 disarankan fokus penyelarasan web: tab Informasi Hotel, dashboard periode
berjalan, layout progress lantai sesuai gambar, status dan indikator sumber data.
Pertahankan auth, histori legacy, form Nusanet dan fungsi save yang berjalan.
Tampilkan “belum tersedia” jika agregat resmi tidak dapat dihitung; jangan
mempromosikan draf lokal menjadi progress server atau membuat grafik dekoratif.

Master lintas perangkat dan progress seluruh titik bergantung pada schema/API baru.
Jika dimasukkan ke Phase 2, rancangan migration dan kontrak harus direview terlebih
dahulu; persetujuan UI saja tidak memberi izin menjalankan migration.
Phase 3 membuat host Android; Phase 4 native Wi-Fi; Phase 5 memperkuat LibreSpeed
per titik; Phase 6 dokumentasi/signature; Phase 7 PDF/integrasi. Pengujian relevan
tetap wajib pada setiap fase, bukan menunggu Phase 8.

Acceptance Phase 2: lima menu dan histori kompatibel, konteks periode/hotel jelas,
tab lengkap, target empat tidak mengubah data lama, status/progress bersumber
jelas, empty/error/loading state, akses per peran serta layout HP/desktop diuji.
Perubahan schema tidak boleh terselip dalam pekerjaan UI.

## Verifikasi Phase 1

Perubahan hanya dua dokumen audit. Pemeriksaan terarah menggunakan test web dan
health dengan ASGI/mock serta config unit test, tanpa koneksi database nyata.
Hasil eksekusi dicatat dalam laporan akhir. Native Android, radio, speedtest
lapangan, PDF dan kesesuaian schema live belum diuji dalam audit ini.
Phase 2 belum dimulai dan menunggu persetujuan pengguna.
