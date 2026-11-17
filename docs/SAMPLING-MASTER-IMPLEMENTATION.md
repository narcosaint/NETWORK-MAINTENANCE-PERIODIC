# Master lantai dan titik — implementasi lokal

16 November 2026. Backend dan integrasi Web/Android tersedia di source; belum
deployment atau migration aktif.

## Cakupan

- Model `HotelFloor` dan `SamplingPoint`, default target empat tanpa seed titik.
- GET/POST `/hotels/{hotel_id}/floors` dan PATCH `/{floor_id}`.
- GET/POST `/{floor_id}/sampling-points` dan PATCH `/{point_id}`.
- GET memakai offset/limit (maksimal 100), urutan position lalu ID dan opsi
  include_archived. Supervisor mengelola master; teknisi hanya membaca master hotel
  yang mempunyai kunjungan ditugaskan kepadanya.
- PATCH menggunakan expected_version dan menaikkan versi atomik; stale mendapat
  409. Name/position/target tidak menerima null. device_id dan location boleh null.
- Archive mempertahankan record; tidak ada endpoint delete/restore. Induk archived
  menolak mutasi titik. Pergantian induk hotel/lantai tidak tersedia.
- UUID POST yang diulang dengan payload identik mengembalikan record sama; UUID
  berbeda isi mendapat 409. Request create bersamaan bisa mendapat 409 dari unique
  constraint dan dapat dibaca/diulang setelah request pertama selesai.
- Satu AP boleh dirujuk banyak titik. AP lintas hotel dan perangkat non-AP ditolak;
  perubahan hotel/jenis AP yang direferensikan ditolak di endpoint inventaris.

## Aktivasi

Route memakai `SAMPLING_MASTER_ENABLED=true` sebagai gate eksplisit. Default
nonaktif memberi 503 setelah autentikasi, tanpa membaca tabel sampling. Tidak ada
perubahan environment server dalam implementasi ini. API existing tetap tersedia
pada schema lama. Jangan aktifkan sebelum schema terpasang dan terverifikasi.

Draft migration tetap di `docs/migrations/`, bukan Alembic versions. Head aktif
tetap 0009. Kelima tabel draft sudah mempunyai model; coverage mempunyai API baca
dan aktivasi. Review/promosi revision harus dilakukan eksplisit, bukan menjalankan
autogenerate atau upgrade head untuk memasang draft.

## Snapshot kunjungan dan integrasi UI

- GET `/sampling-capabilities` mengembalikan gate master/coverage dan status
  pengukuran yang masih nonaktif. Klien baru tetap bekerja dengan server lama
  yang belum mempunyai endpoint ini.
- GET `/hotel-visits/{id}/sampling-coverage` mengembalikan snapshot atau null
  untuk visit legacy. Supervisor dan teknisi pemilik boleh membaca.
- POST pada path sama khusus supervisor, sebelum check-in, memakai expected_version
  visit serta daftar ID/versi lantai dan titik yang ditinjau. Server mengunci visit,
  hotel, master dan AP, lalu memvalidasi cakupan utuh sebelum menulis transaksi.
- Snapshot menyimpan periode awal bulan, nama/lokasi, AP inventaris opsional, target
  dan foto wajib yang dipilih supervisor. Array kategori harus dikirim eksplisit;
  array kosong berarti kategori tidak wajib. Tidak ada kategori wajib tersembunyi.
- Empat lokasi nyata harus dipenuhi untuk target empat. Semua titik tambahan ikut
  denominator. Satu AP dapat dirujuk banyak sesi; AP tak dikenal tetap NULL.
- UUID coverage/floor/session dibuat server. Replay POST identik mengembalikan
  snapshot sama; request berbeda mendapat 409. Aktivasi menaikkan versi visit.
  Rename/archive master tidak mengubah snapshot. Revisit bulan sama tetap boleh.
- Detail visit juga membawa `sampling_coverage` jika ada, termasuk saat gate
  dimatikan. Android memakai cache visit existing untuk akses snapshot offline.
- Web Detail Hotel mengganti konfigurasi lokal dengan master server ketika gate
  tersedia. Supervisor bisa menambah/edit/archive lantai/titik dan memilih AP.
  Dashboard kunjungan menyediakan preview cakupan, pilihan foto wajib dan tindakan
  bekukan eksplisit. Kunjungan existing tidak otomatis diubah menjadi V2.
- Web dan Android memakai sesi snapshot sebagai daftar titik pada visit V2.
  Evidence perangkat legacy tidak disalin ke sesi, sehingga hasil satu AP tidak
  menaikkan progress beberapa lokasi. UI menyatakan pengukuran/submit V2 belum siap.
- Check-out/resubmit V2 sengaja ditolak sampai validator evidence per sesi dan PIC
  tersedia. Guard tetap berlaku saat feature gate mati; visit legacy tidak berubah.
  Snapshot turut masuk detail yang dipakai audit event existing.

## Pengujian dan batas

Test SQLite mencakup gate tanpa schema, peran/scope, default empat tanpa dummy,
UUID retry/conflict, unique nama aktif, archive, pagination, versi stale, dua titik
satu AP, AP lintas hotel/non-AP, dan laporan kunjungan tidak berubah.

`test_sampling_postgres.py` memakai fixture PostgreSQL terisolasi existing dengan
guard database `_test`/`_staging`, schema acak dan opt-in HOTEL_STAGING_DATABASE_URL.
Test menerapkan draft hanya pada schema uji, memeriksa lima tabel kosong dan head
aktif tetap 0009, lalu menjalankan alur master dan coverage terhadap DDL PostgreSQL.
Tanpa URL pengujian, test dilewati; hasil SQLite/SQL offline bukan bukti PostgreSQL.

`tests/browser/sampling_foundation_ui.py` menghubungkan Web dan Android ke FastAPI
sebenarnya melalui bridge ASGI serta SQLite terisolasi, bukan respons API fixture.
Skenario: buat lantai dan empat titik melalui Web, bekukan snapshot, rename master,
baca snapshot sama dari Android, cek progress sesi, layout mobile, XSS, dan cache
offline. Ini tidak membuktikan perilaku native Android atau PostgreSQL.

Catatan/observasi sesi dan antrean kiriman manual telah ditambahkan dalam
[SAMPLING-OBSERVATIONS.md](SAMPLING-OBSERVATIONS.md), dengan draft schema 0011
dan gate write terpisah. Ini belum menyelesaikan pengukuran atau submit V2.

Belum termasuk reorder batch atomik, progress resmi tervalidasi,
hasil Wi-Fi, speedtest per sesi, sync mutasi offline, signature/PDF.
Perubahan position per record tersedia; reorder banyak record perlu endpoint
batch berikutnya. Backbone FO/wireless dan LAN existing tidak diubah.

Dokumen review: [SAMPLING-FOUNDATION-MIGRATION-REVIEW.md](SAMPLING-FOUNDATION-MIGRATION-REVIEW.md).
