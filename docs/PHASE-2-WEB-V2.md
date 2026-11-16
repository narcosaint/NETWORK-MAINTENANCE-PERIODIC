# Phase 2 — Web Dashboard V2

Implementasi lokal, 13 November 2026. Mengikuti ROADMAP-V2, audit Phase 1 dan
`design/hotel-maintenance-ui-reference.png.png`. Tidak ada deployment atau Phase 3.

## Hasil

- Sidebar lima menu existing dipertahankan, dengan hijau tua dan state aktif hijau
  toska. Tim Teknisi tetap hanya supervisor; endpoint dan histori perangkat lama utuh.
- Ringkasan menghitung penugasan bulan berjalan dari koleksi server yang sudah
  dipaginasi oleh aplikasi. Total hotel, maintenance bulan berjalan, selesai,
  tertunda dan perlu review ditampilkan. Total temuan lintas hotel belum tersedia.
- Maintenance Hotel memakai periode bulan berjalan sebagai default; filter dapat
  diganti/dikosongkan. Pilih hotel → penugasan → dashboard V2 untuk periode/visit
  yang dipilih. Hotel selector dan tombol ganti periode/penugasan menjaga konteks.
- Dashboard menampilkan hotel/teknisi/periode, progress, empat kartu statistik,
  expandable card lantai, daftar titik, status, rata-rata hasil yang tersedia dan
  indikator laporan utama/dokumentasi/PIC. Detail titik dan tiga tab tetap tersedia.
- Detail Hotel menambahkan Informasi Hotel; empat tab lama dan inventaris tetap ada.
- Target default empat tetap konfigurasi/placeholder lokal; tidak membuat record.
- Warna hijau/kuning/merah/abu untuk hasil sampling; enum workflow backend utuh.

## Makna angka dan keterbatasan

Progress V2 merupakan proyeksi baca per penugasan, bukan status resmi approval.
Titik dihitung selesai hanya jika ada outcome pass/fail server, foto server dan
speedtest completed bermetrik pada direct_https + hotel_wifi terkonfirmasi, atau
run failed dengan alasan. Run terakhir dipakai; manual bandwidth, diagnostik,
running, aborted, draft lokal dan foto lokal tidak menaikkan completion.
Kondisi gagal uji beralasan tetap merah walau pemeriksaannya telah selesai.
Konfirmasi Wi-Fi browser bukan native radio verification.

Total temuan per visit adalah jumlah titik dengan outcome fail atau failed run
beralasan, satu kali per titik; bukan jumlah entri temuan terstruktur. Jumlah nol
hanya tampil bila ada titik server yang bisa dievaluasi. Tanpa titik server,
selesai/temuan ditampilkan “Belum tersedia”. Cakupan mencakup target lokal dengan
penanda “Belum tersinkron”; ini belum cakupan master resmi lintas perangkat.

Ringkasan sinyal memakai rata-rata band measured manual tersimpan; download/upload
memakai run Wi-Fi tersimpan yang memenuhi konteks di atas. Tidak ada grafik/tren
atau delta fiktif. Angka nol asli tetap diterima. Persetujuan PIC tetap “Belum
tersedia”, bukan disimpulkan dari approval supervisor atau nama PIC.

Masih membutuhkan backend: master lantai/titik tersinkron, snapshot cakupan visit,
progress/pre-submit resmi, temuan terstruktur, sinkronisasi foto/catatan lokal,
review/signature PIC dan pengukuran native Android. Tidak diimplementasikan di fase ini.

## File

- `backend/app/web/dashboard-v2.js`: proyeksi evidence dan renderer dashboard.
- `backend/app/web/dashboard-v2.css`: visual/sidebar/status dan layout responsif.
- `backend/app/web/index.html`: memuat asset baru dan versi cache asset yang diubah.
- `backend/app/web/sampling.js`: root sampling memakai dashboard baru; detail tetap.
- `backend/app/web/hotel-detail.js`: tab Informasi Hotel dan informasi profil layanan.
- `backend/app/web/app.js`: statistik Ringkasan bulan berjalan.
- `backend/app/web/hotel.js`: hanya default filter periode; form/handler tetap.
- `backend/tests/test_web.py`: asset baru dalam pemeriksaan same-origin/header.
- `tests/browser/dashboard_v2_ui.py`: evidence, empty state, disclosure, responsivitas,
  validasi dan payload save form ke fixture, screenshot.
- `tests/browser/hotel_navigation_ui.py`, `tests/browser/sampling_ui.py`: adaptasi
  tab baru dan disclosure lantai pada regresi navigasi/sampling existing.

## Verifikasi

40 test backend terarah lulus (web, health, config, modules, hotel visits, report
revision, speedtests). Database pengujian menggunakan SQLite in-memory/temporary
fixture; tidak ada koneksi database produksi atau eksekusi Alembic.

Tiga suite browser lokal memakai server statis sementara dan API fixture:
Dashboard V2, navigasi hotel, dan sampling offline. Memeriksa peran, histori lama,
inventaris hotel, default target empat, filter periode, tab/keyboard, back,
error/retry, draf/foto IndexedDB, pemisahan akun, serta lebar 360/390/768/1440 px.
Validasi dan payload penyimpanan form Nusanet diuji ke endpoint fixture, sementara
penyimpanan/validasi backend diperiksa oleh test terisolasi existing.

Seluruh kode `hotel.js` mulai `createHotelVisit()` sampai akhir identik dengan
baseline sebelum perubahan: form Nusanet, field legacy, API payload, handler save,
check-in/out dan review tidak diganti. Perubahan file hanya default periode list.

Screenshot lokal memakai data fixture berlabel QA, bukan data produksi:
`artifacts/phase2/dashboard-1440.png` dan `dashboard-390.png`.
Kesesuaian visual diperiksa terhadap referensi: sidebar hijau tua, card terang,
empat statistik, progress hijau, chip titik dan lantai expandable. Perbedaan:
jumlah lantai mengikuti fixture/data nyata, tanpa sparkline/delta, dengan penanda
lokal/unavailable dan akses laporan existing. Mobile berupa layout web responsif,
bukan layar Android native pada sisi kanan mockup.

Lingkungan browser menggunakan pustaka/font yang sudah ada di `/tmp`; tidak ada
instalasi sistem, perubahan Docker/network atau server deployment.
