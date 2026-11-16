# Phase 3 — Android UI

Implementasi lokal 13 November 2026, sesuai AGENTS, ROADMAP-V2, ARCHITECTURE-V2,
DATABASE-GAP-V2 dan desain `design/hotel-maintenance-ui-reference.png.png`.
Phase 2.1 Web tetap dipertahankan. Tidak ada perubahan backend atau database.

## Hasil

Source baru: `android-app/`, React + TypeScript + Vite, Capacitor 8, host Android
Java/Gradle. Header hijau tua, background terang, rounded card, statistik dua kolom,
bottom navigation empat menu, step navigation kunjungan dan tiga tab sampling.
Ikon lokal dari lucide-react, tanpa CDN/font eksternal atau pengukuran dekoratif.

| Halaman | Fungsi Phase 3 |
| --- | --- |
| Login | Username/password API existing, alamat HTTPS server, koneksi perangkat, loading/error, teknisi saja |
| Dashboard/Jadwal | Hotel yang ditugaskan, pagination seluruh jadwal, workflow/progress pekerjaan, cache dan retry |
| Detail Hotel | Informasi hotel, periode, teknisi/PIC, progress sampling, check-in lokasi aktual atau alasan GPS |
| Laporan Utama | Backbone FO/wireless, LAN a–e + keterangan, field Nusanet lama/baru, draf dan save server berversi |
| Sampling | Lantai dari AP kunjungan, default empat target, status/progress dari evidence server, expandable card |
| Detail Sampling | Connected Network, band selector, analyzer/speedtest/foto-catatan; informasi belum tersedia ditandai |
| Review | Ringkasan server, titik selesai/belum, temuan server/lokal terpisah, PIC belum tersedia |
| Profil | Identitas teknisi, jumlah draf/foto lokal aktual, status sinkronisasi, logout |

Komponen reusable dan API/service terpisah dari halaman. Semua input pengguna
menggunakan React text rendering atau value, tanpa innerHTML/dangerouslySetInnerHTML.
Form memiliki label aksesibel, keyboard tablist, touch target minimum 44px,
safe-area padding dan tombol Back Android. Session/token tidak dipersistenkan.
Cleartext/mixed content dan backup native dimatikan; izin GPS/network disiapkan.
API native melalui CapacitorHttp menghindari kebutuhan perubahan CORS backend.

## Kompatibilitas dan persistence

Tidak membuat/mengubah endpoint atau schema. Save laporan memakai PUT dan
expected_version, mempertahankan field lama termasuk LAN notes dan metrik lama.
Pilihan koneksi menentukan branch yang dikirim, draf tetap mempertahankan isinya.
Konflik 409 tidak mengganti versi draf. Tidak otomatis mengirim ulang perubahan.

IndexedDB Android terpisah dari web, key per origin API/akun/kunjungan/titik.
Persistence diantre agar pergantian halaman tidak memotong write. Draf/foto bertahan
logout dan tidak berpindah ke akun lain. Error/quota ditampilkan sebagai kegagalan,
bukan status tersinkron. Token/password tidak masuk ke IndexedDB/localStorage.
Cache dan draf offline hanya untuk sesi yang sudah login; login offline/cold-start
belum tersedia. Tidak ada migrasi atau penghapusan data browser web existing.

Cakupan default empat adalah placeholder UI, bukan record produksi. Master lantai
belum tersinkron; konfigurasi lokal web tidak dibaca lintas aplikasi. Completion
memerlukan outcome pass/fail, foto server dan run Wi-Fi completed bermetrik pada
konteks yang diterima, atau failed dengan alasan. Manual/diagnostik/draf/foto lokal
bukan completion. Konfirmasi Wi-Fi riwayat browser bukan bukti radio native.

## Fitur yang belum terintegrasi

- Wi-Fi connection/scanner native, BSSID/AP matching, grafik sinyal/overlap: Phase 4;
  hanya kontrak WifiService, tidak ada plugin radio/angka simulasi.
- Start LibreSpeed Android per titik dan binding/validasi koneksi: Phase 5; hanya
  interface dan riwayat server, tombol start belum tersedia.
- Master lantai/titik dan snapshot cakupan backend; sinkronisasi catatan/foto,
  dokumentasi utama, temuan terstruktur dan offline-sync end-to-end.
- Review/signature PIC, native submit V2 dan PDF. Approval supervisor existing
  tidak ditampilkan sebagai persetujuan PIC. Workflow web existing tetap tersedia.
- Pengujian perangkat untuk kamera, GPS, permission, WebView/TLS/network dan
  lifecycle/restart. Plugin kamera/GPS sudah disiapkan, belum diklaim lolos native.

## Pengujian

- `npm run build`: lulus (TypeScript strict + bundle Vite).
- `npm run typecheck`: lulus.
- `npm run lint`: lulus; checklist skill React best practices diterapkan.
- `npm test`: 13 test lulus: evidence, default empat, missing/zero, gagal beralasan,
  legacy payload, ownership, scope akun/server, antrean persistence, layanan
  unavailable, origin validation, pagination, verb/version save, 409/401.
- `npm run android:sync`: lulus; host Android dan empat plugin tersinkron.
- 47 test backend terisolasi lulus; PostgreSQL/staging opt-in tidak dijalankan.
- `tests/browser/android_phase3_ui.py`: lulus dengan static build/API intercept.
  Mencakup login salah/benar, jadwal, GPS fixture aktual dari browser dan penolakan
  izin + alasan, payload Nusanet/legacy/expected_version, konflik 409/draf bertahan,
  offline catatan/foto, pergantian halaman, storage failure/recovery, missing native,
  XSS hotel/lantai/titik/textarea, read-only approval, review/PIC, 401/logout,
  isolasi draf/foto akun kedua, empty state dan lebar 360/390/430/768px tanpa overflow.

Test backend tidak menerapkan migration. Semua data browser berasal dari fixture
QA yang diintercept; tidak ada fixture/akun dummy pada database produksi. Browser
memakai server statis loopback sementara dan pustaka Chromium existing di `/tmp`;
tidak mengubah port publik, Docker atau konfigurasi jaringan. Tidak ada deployment.

Screenshot lokal diperiksa terhadap tema mockup:

- `artifacts/phase3/dashboard-390.png`
- `artifacts/phase3/sampling-notes-390.png`
- `artifacts/phase3/review-390.png`

Teks injeksi keamanan sengaja terlihat sebagai teks pada fixture; bukan konten
produksi. Screenshot foto berupa gambar QA, bukan hasil perangkat lapangan.

Build tools sempat memiliki advisori critical pada test runner; telah diperbarui.
Audit terakhir menyisakan 10 advisori moderate di dependency tree tooling lint
(minimatch); bukan runtime aplikasi. Lockfile disertakan agar hasil reproducible.

## Build APK

Ikuti `android-app/README.md`: Node 22.13+, JDK 21, Android SDK 36, konfigurasi
origin HTTPS non-secret, npm ci, android:sync, lalu gradlew assembleDebug.
APK debug akan berada di `android/app/build/outputs/apk/debug/app-debug.apk`.
Environment saat ini tidak memiliki JDK/Android SDK/emulator, sehingga belum ada
APK dibangun atau uji native/perangkat fisik. Tidak ada release/signing/deployment.
Phase 4 tidak dikerjakan dan menunggu persetujuan terpisah.
