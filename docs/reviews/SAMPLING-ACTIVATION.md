# Status setelah persetujuan — backend sudah aktif

18 November 2026: operator menyetujui aktivasi. Migration 0010–0012 sudah dipromosikan
ke chain Alembic dan diterapkan setelah backup/restore salinan terbukti menjaga
seluruh data lama. Source backend/Web serta gate field sampling, observasi dan
speedtest sudah aktif pada https://maintenance.inisaja.id. Tidak ada data dummy
produksi. Lihat [catatan rilis](../DEPLOYMENT.md) untuk bukti dan backup. Radio/throughput HP
masih perlu diuji teknisi; completion V2 belum diaktifkan.

Rincian di bawah mencatat implementasi dan status sebelum aktivasi.

# Perubahan cakupan review — teknisi menambah lokasi lapangan

Operator menyetujui penambahan lantai/area dan titik dari Android teknisi pada
18 November 2026. Pembatasan supervisor-only dan keharusan menyiapkan seluruh
cakupan sebelum check-in di bagian historis bawah tidak berlaku untuk endpoint
lapangan baru. Supervisor activation existing tetap kompatibel. Endpoint lapangan
mendukung bootstrap cakupan aktif atau append ke cakupan yang sudah ada, tanpa
mengubah bukti lama. Detail: [FIELD-SAMPLING.md](../FIELD-SAMPLING.md).

Tidak membutuhkan tabel tambahan di luar draft 0010–0012. Audit/replay memakai
HotelVisitEvent existing. Aktivasi juga memerlukan SAMPLING_FIELD_ENABLED=true.
Rencana backup/restore, review DDL dan persetujuan release produksi tetap berlaku.
Belum ada migration atau deployment source backend pada langkah implementasi ini.

Catatan review sebelumnya di bawah merupakan riwayat cakupan awal.

# Review aktivasi sampling — 18 November 2026

## Penyebab fitur APK belum aktif

Audit read-only deployment membuktikan API aktif belum mempunyai route sampling,
lantai atau capabilities. Schema produksi tetap `0009_site_report_profile`, tanpa
tabel hotel_floors atau sampling_*. APK bisa login tetapi memakai kunjungan legacy.
Tombol native analyzer sebelumnya ikut tergantung sesi server; kini diperbaiki agar
capture radio tersedia untuk draf lokal di kunjungan legacy yang masih editable.
Speedtest tiap titik tetap membutuhkan sesi server untuk relasi bukti yang benar.
Tidak memakai satu hasil AP untuk semua lokasi atau membuat record titik fiktif.

Lantai/master titik dikelola supervisor lewat Web sesuai ROADMAP-V2.md. Android
teknisi tidak diberi akses administrasi master secara diam-diam. Default target
4 titik tidak otomatis membuat nama/lokasi nyata atau seed produksi.

## Perbaikan APK tanpa migration

Login hanya username/password. Origin native ditentukan build dengan default
https://maintenance.inisaja.id; tidak ada kolom/pengaturan origin di layar login.
Build Web development tetap memakai proxy /api jika VITE_API_URL kosong.

Analyzer/koneksi native bisa dibaca tanpa sesi server pada kunjungan editable;
hasil dipersist dalam scope akun/origin/visit/titik dan ditandai tersimpan lokal.
AP dikenali dari MAC snapshot jika ada. Tanpa sesi server, tidak ada sinkronisasi
observasi atau klaim sampling selesai. Read-only/check-in dan permission Android
existing tetap berlaku. Perilaku radio fisik masih harus dibuktikan di HP.

## Perubahan database yang dimintakan review

Lihat [SQL hasil kompilasi offline](SAMPLING-0010-0012.sql) dan draft pada
`docs/migrations/`. Ketiganya masih di luar head Alembic aktif.

- 0010: hotel_floors, sampling_points, sampling_coverages,
  sampling_coverage_floors, sampling_sessions (5 tabel).
- 0011: sampling_observations (1 tabel, catatan/radio berversi append-only).
- 0012: sampling_speedtest_attempts (1 tabel, relasi run per titik/UUID replay).

Seluruhnya additive: CREATE TABLE/index/constraint, tidak ada DELETE/DROP, seed,
backfill atau penulisan ulang hasil lama. FK menggunakan RESTRICT. Histori tidak
dihapus lewat downgrade. Ada indeks unik nama master aktif, scope floor/coverage,
UUID idempotent serta UNIQUE run_id supaya satu speedtest tidak dibagi.
Kolom/tabel legacy dan laporan Backbone FO/wireless/LAN dipertahankan.

Risiko: lock singkat FK pada parent table saat DDL, waktu deployment API serta
sinkronisasi versi visit/sesi. Backup database+foto yang konsisten dan uji restore
harus selesai sebelum migrasi utama. Jangan menjalankan SQL review langsung dan
melupakan version ledger Alembic. Promosi draft ke head dilakukan sebagai langkah
release yang eksplisit setelah persetujuan; test head/draft diperbarui bersamaan.

## Release yang perlu persetujuan terpisah

1. Backup database+foto, restore ke PostgreSQL terisolasi, uji upgrade 0009 ke
   0012 dan bandingkan fingerprint semua data lama. Tanpa data dummy produksi.
2. Review SQL dan hasil restore, lalu promosikan migration additive ke chain
   Alembic. Jalankan migration satu kali, bukan dari semua worker API.
3. Deploy backend/source Web terbaru yang sudah diuji. Pertahankan IP privat,
   volume dan sertifikat aktif. PUBLIC_SPEEDTEST_ORIGIN=https://maintenance.inisaja.id.
   Pastikan forwarded HTTPS hanya dipercaya dari proxy yang diketahui.
4. Aktifkan SAMPLING_MASTER_ENABLED, SAMPLING_OBSERVATIONS_ENABLED dan
   SAMPLING_SPEEDTEST_ENABLED setelah schema tersedia.
5. Supervisor memasukkan lantai/titik/AP nyata, lalu membekukan cakupan kunjungan
   saat status assigned dan sebelum check-in. Kunjungan legacy yang sudah mulai
   tidak diberi snapshot retroaktif atau dibackfill otomatis; perlu penugasan
   berikutnya yang disiapkan dengan cakupan sampling.
6. Verifikasi API/scope/legacy di deployment serta pengukuran aktual dari HP.

Rollback aplikasi tidak menghapus tujuh tabel/histori. Matikan gate write bila
perlu dan gunakan recovery maju; jangan restore backup di atas data baru tanpa
review. Submit V2 belum diaktifkan karena foto per sesi dan PIC belum lengkap.

Tidak ada perubahan schema, gate atau deployment source backend dalam perbaikan
APK ini. Perubahan produksi menunggu persetujuan sesuai AGENTS.md.

## Hasil pengujian perbaikan APK

Build/typecheck/lint dan 36 test frontend lulus. Regresi browser Android serta
Web → API → SQLite → Android lulus. Regresi Android juga memeriksa tombol
pembacaan radio pada kunjungan legacy tersedia dan browser mengembalikan
unavailable tanpa membuat pengukuran/API write fiktif. 20 test PostgreSQL 18.6
terisolasi dan 13 test SQL draft/origin/scaffold lulus. Database produksi tidak
dipakai sebagai data uji. Build APK: artifacts/android/hotel-maintenance-https-debug.apk.

APK debug signature serta aset LibreSpeed terverifikasi. SHA-256:
`c12ccf853cfd0ca8a293c379e4e97ae55b53bce7a7566e391662f6ca3bc2ec2f`.
