# Navigasi berbasis hotel — 13 November 2026

Audit: frontend HTML/CSS/JavaScript buildless, navigasi state di app.js, laporan
hotel di hotel.js, sampling di sampling.js dan IndexedDB di sampling-service.js.
Tidak ada router SPA, package.json atau bundler. API hotel-visits memakai hotel_id,
technician_id dan planned_date. Lantai/target belum memiliki endpoint master.

Sidebar utama: Ringkasan, Maintenance Hotel, Data Hotel, Tim Teknisi dan Template
Checklist. Tim Teknisi tetap hanya untuk supervisor sesuai izin yang sudah ada.
Menu perangkat, kunjungan perangkat dan jadwal perangkat disembunyikan; handler,
API dan histori lama dipertahankan. Ringkasan menghitung penugasan hotel.

Alur: Maintenance Hotel → pilih hotel → pilih penugasan/periode PM → pilih lantai
→ pilih titik → Wi-Fi Analyzer, Speedtest, Foto & Catatan. Laporan utama, check-in,
check-out dan review masih tersedia dari sampling. Penugasan yang belum dimulai
bersifat baca sampai teknisi melakukan check-in di laporan utama.

Periode PM memakai filter bulan dan validasi tanggal penugasan hotel dalam bulan
yang dipilih, lewat API /hotel-visits existing. Ini penjadwalan per bulan oleh
supervisor, bukan generator penugasan berulang otomatis. Jadwal perangkat lama
tidak digunakan untuk PM baru, tidak dihapus dan tidak dimigrasikan otomatis.

Data Hotel → Detail Hotel mempunyai tab Lantai, Perangkat, Titik Sampling dan
Riwayat Maintenance. Inventaris difilter menurut hotel; tambah perangkat memilih
hotel aktif, CRUD tetap memakai /devices existing. Histori lama bisa dibuka dari
bagian Histori perangkat lama pada Riwayat Maintenance.

Lantai dan target default 4 (rentang 1–100) memakai key IndexedDB existing per akun
+ hotel, sehingga konfigurasi Detail Hotel dipakai kembali oleh sampling pada akun
/browser yang sama. Konfigurasi belum tersinkron antar akun atau perangkat. AP
server tidak disembunyikan hanya karena target diturunkan. Draf sampling existing
menjaga titik yang sudah memiliki draf. Tidak ada data pengukuran simulasi.

File: backend/app/web/{app.js,hotel.js,hotel-detail.js,sampling.js,index.html,
style.css,sampling.css}; backend/tests/test_web.py;
tests/browser/hotel_navigation_ui.py; dokumentasi ini.

Verifikasi: pytest 47 passed / 15 skipped, unittest scaffold 3 passed, browser
sampling existing lulus. Browser navigasi baru menguji sidebar menurut peran,
inventaris per hotel, default/konfigurasi target, tab/keyboard, histori lama,
periode PM dan penolakan tanggal di luar bulan, alur sampling, breadcrumb/back,
serta layout 360/390/768/1440 px. Fixture dicegat di browser; tidak menulis data
produksi. Tes asset diperluas untuk hotel-detail.js.

Deployment hanya frontend, dengan backup web lama dan image pemulihan
hotel-maintenance-api:before-navigation-20261113. Image sampling yang dirujuk
Compose dibangun ulang dari source agar pembaruan juga tersedia saat container
nanti dibuat ulang. Asset aktif diperbarui tanpa restart API. Tidak ada perubahan
file Compose, env, autentikasi, API, schema, migration, port atau jaringan.

Backup rilis: `/root/backups/hotel-maintenance/20261113T031213Z-hotel-navigation/`.
Tes navigasi yang sama juga lulus terhadap asset dashboard aktif pada localhost:8000
dengan fixture API dicegat di browser. Container healthy dan /health/db ok.
