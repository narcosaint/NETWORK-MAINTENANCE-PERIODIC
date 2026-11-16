# Modul backend dan deployment terkontrol

Backend telah diterapkan hingga 0008_network_speedtests pada 12 November 2026.
Lihat [catatan deployment aktif](DEPLOYMENT.md). Database tetap di jaringan internal; API memakai
bridge tambahan dan hanya dipublikasikan pada 127.0.0.1:8000 sesuai Compose saat ini.
Tidak ada koneksi atau seed ke produksi.

## Kontrak API

Semua endpoint kecuali health dan login memerlukan `Authorization: Bearer <token>`.
Dokumentasi request/response lengkap di `/docs` atau `/openapi.json`.

| Resource | Endpoint | Hak akses |
|---|---|---|
| Master Hotel | `/hotels` | Kedua role baca; supervisor tulis |
| Inventaris router/switch/AP | `/devices` | Kedua role baca; supervisor tulis |
| User | `/users` | Supervisor |
| Preventive maintenance | `/schedules` | Supervisor kelola; teknisi baca tugas sendiri |
| Kunjungan | `/visits` | Supervisor membuat; teknisi baca tugas sendiri |

Empat resource CRUD pertama memiliki POST koleksi, GET koleksi/detail, PUT detail (penggantian
penuh), DELETE detail. Koleksi mendukung `offset` dan `limit` (maksimal 100).
PATCH `/schedules/{id}/progress` memperbarui status `pending`/`completed` dan notes;
teknisi hanya dapat mengubah jadwal yang ditugaskan kepadanya.
Jadwal yang sudah memiliki kunjungan tidak dapat diganti, dihapus atau ditandai
completed melalui endpoint jadwal lama; jadwal tetap pending setelah submitted dan menjadi completed hanya saat approval.

## Penugasan dan check-in kunjungan (revision 0003)

Supervisor membuat `POST /visits` dengan `schedule_id`; satu jadwal pending hanya
boleh memiliki satu kunjungan. Assignee disalin dari jadwal dan harus teknisi aktif.
`GET /visits` dan `GET /visits/{id}` hanya memperlihatkan tugas sendiri kepada
teknisi; supervisor dapat membaca semuanya. Pagination sama seperti resource lain.
Kunjungan belum memiliki endpoint penghapusan atau penggantian penugasan.

Teknisi yang ditugaskan melakukan `POST /visits/{id}/check-in`:

```json
{
  "expected_version": 1,
  "device_time": "2026-11-11T10:00:00+07:00",
  "gps_exception_reason": "Izin lokasi ditolak oleh perangkat"
}
```

Jika GPS tersedia, kirim `latitude`, `longitude`, dan `accuracy_m` bersama-sama,
tanpa `gps_exception_reason`. Koordinat harus valid dan akurasi tidak negatif;
waktu HP harus menyertakan timezone. Jangan mengarang koordinat. Server menyimpan
`checked_in_at` sendiri dan mengubah `assigned` → `in_progress`, version 1 → 2.
Update memakai perbandingan status/version atomik. Konflik atau check-in berulang
menghasilkan 409; klien harus memuat ulang kunjungan. Jika respons terputus,
periksa GET sebelum memutuskan retry. Belum ada idempotency key/outbox offline.
GPS merupakan klaim perangkat, belum diverifikasi radius atau keaslian lokasinya.
Alasan pengecualian disimpan untuk review supervisor (revision 0005).

Checklist dan check-out ke submitted tersedia pada revision 0004 di bawah.
Revisi dan approval tersedia pada revision 0005 di bawah.

Jadwal bulanan dibuat eksplisit melalui POST: `device_id`, `technician_id`,
`month` seperti `2026-11-01`. Satu perangkat hanya boleh mempunyai satu jadwal
per bulan. Tidak ada cron atau pembuatan data otomatis. Assignee harus teknisi
aktif. Foreign key menolak penghapusan hotel/perangkat/user yang masih dirujuk.
Duplikasi/konflik relasi: 409; input tidak valid: 422; record tidak ada: 404.

Username dinormalisasi lowercase, unik; password 12–128 karakter di-hash scrypt
dengan salt acak. Respons tidak mengandung password/hash. Login memberikan token
acak 256-bit, masa berlaku 8 jam; database hanya menyimpan SHA-256 token. Logout,
perubahan user/password/role, penonaktifan dan penghapusan mencabut sesi.
Supervisor tidak dapat menghapus/menonaktifkan/menurunkan role dirinya sendiri.
Tidak ada registrasi publik atau kredensial bawaan.
Login dibatasi 20 percobaan/menit per source IP per proses, dengan penyimpanan
memori terbatas. Untuk banyak worker/replica, operator perlu rate limiter bersama
atau gateway yang telah ditinjau. Jangan mencatat token atau password di log.
Akses jarak jauh harus melalui saluran terenkripsi yang disetujui; tetap pertahankan
binding localhost saat ini. Endpoint health tetap terbuka untuk probe lokal.

## Validasi sebelum deployment

```bash
.venv/bin/pytest -q
.venv/bin/python -m unittest discover -s tests -v
POSTGRES_PASSWORD=offline-only .venv/bin/alembic upgrade head --sql > /tmp/hotel-migration.sql
```

Tes CRUD memakai SQLite in-memory dan FK aktif; tidak memakai konfigurasi database
produksi. Constraint PostgreSQL untuk hari pertama bulan diuji lewat SQL migration
serta validator API, bukan dieksekusi di SQLite. Tes PostgreSQL yang tersedia hanya
SELECT 1, opsional melalui TEST_DATABASE_URL. Jalankan migration dan tes penerimaan
pada PostgreSQL staging terpisah sebelum produksi: upgrade schema dari revision
0001 dengan data hotel/perangkat yang telah ada, cek data tetap utuh, duplikasi
bulan ditolak, FK menolak delete, dan semua alur autentikasi/role berhasil.
Validasi DDL PostgreSQL nyata belum dibuktikan oleh tes SQLite/offline.

## Deployment aman oleh operator (bukan dijalankan otomatis)

1. Tinjau source dan SQL revision `0002_maintenance`, backup database dan uji restore.
   Jangan gunakan drop/reset schema/database atau `docker compose down -v`.
2. Uji image serta migrasi pada staging terisolasi. Pisahkan role runtime (DML)
   dari role migrasi (DDL) sesuai kebijakan operator. Compose saat ini tetap utuh;
   pemisahan kredensial perlu konfigurasi operator sebelum produksi.
3. Jadwalkan maintenance window, hentikan API untuk mencegah request berjalan saat
   perubahan schema. Jalankan secara eksplisit setelah persetujuan deployment:

   ```bash
   docker compose config --quiet
   docker compose build api migrate
   docker compose stop api
   docker compose run --rm migrate
   docker compose up -d --no-deps api
   curl --fail http://127.0.0.1:8000/health/db
   ```

   Bila migrasi gagal, jangan start API baru; periksa log dan perbaiki melalui
   migration lanjutan. Hindari downgrade destruktif sebagai rollback produksi.
4. Untuk database tanpa user, operator membuat supervisor pertama secara interaktif:
   `docker compose exec api python -m app.bootstrap`. Password diminta tanpa echo,
   tidak diteruskan di command line. Perintah menolak bila user sudah ada, memakai
   transaksi dan lock untuk mencegah bootstrap ganda. Ini tindakan operator
   eksplisit, bukan seed otomatis. User selanjutnya dikelola supervisor via API.
5. Periksa login, CRUD, pembatasan role dan health melalui localhost; jangan membuka
   port publik atau mengubah SSH/firewall. Hapus sesi kedaluwarsa secara berkala
   memakai prosedur operator yang ditinjau (tidak ada job otomatis saat ini).

## Status verifikasi 11 November 2026

- Pytest: 13 passed, 1 skipped (koneksi PostgreSQL belum tersedia).
- Unittest scaffold: 3 passed; Compose config valid.
- Migration 0003 diperiksa lewat SQL offline; belum diterapkan ke PostgreSQL.
- Akses daemon dari workspace ditolak pada `/run/podman/podman.sock`.
  Tidak ada build/start container, migrasi database nyata, atau bootstrap user
  yang dilakukan pada kelanjutan ini.
- Pengujian SQLite mencakup kepemilikan kunjungan, duplikasi, stale version,
  check-in ulang, validasi GPS/pengecualian dan perlindungan jadwal terkait.
  Semantik row lock dan konkurensi PostgreSQL masih memerlukan tes staging.


## Checklist dan check-out (revision 0004, 12 November 2026)

- Supervisor membuat `POST /checklist-templates` dengan `name`, `device_type`
  (`router`/`switch`/`ap`) dan `items` (1–100), masing-masing `label` dan
  `required` (default true). GET koleksi/detail tersedia untuk kedua role;
  pagination sama seperti resource lain. Tidak ada update/delete: perubahan
  template dibuat sebagai ID baru sehingga kunjungan lama tetap konsisten.
- `POST /visits` menerima `template_id` opsional untuk kompatibilitas kunjungan
  lama. Template harus sesuai jenis perangkat jadwal. Supervisor dapat mengikat
  template sekali melalui `PUT /visits/{id}/template` dengan `template_id` dan
  `expected_version`. Hanya boleh saat assigned/in_progress dan template masih
  kosong; template yang sudah terikat tidak dapat diganti.
- `GET /visits/{id}/checklist` mengembalikan version, template dan jawaban.
  Teknisi hanya dapat membaca kunjungannya sendiri; supervisor dapat membaca semua.
- Teknisi penanggung jawab menyimpan jawaban saat in_progress melalui
  `PUT /visits/{id}/checklist`: `expected_version` dan `answers` berisi `item_id`,
  `answer` (`pass`/`fail`/`not_applicable`), serta `notes`. Fail/not_applicable wajib
  mempunyai alasan atau catatan tindakan. Setiap item harus berasal dari template
  kunjungan; item ganda dalam request ditolak. Item yang dikirim diperbarui,
  jawaban lain dipertahankan. Item opsional boleh tidak dijawab.
- `POST /visits/{id}/check-out` menggunakan field GPS/waktu/expected_version yang
  sama dengan check-in, ditambah `pic_exception_reason` wajib. Endpoint ini belum
  menerima foto/tanda tangan: alasan pengecualian PIC wajib ditinjau supervisor
  melalui modul approval. Foto wajib per item belum didukung; jangan
  menggunakan tahap ini untuk template yang mewajibkan bukti foto.
- Check-out menolak template kosong atau item required yang belum dijawab.
  Jawaban fail tetap dapat diajukan untuk review; submitted tidak berarti lulus.
  Status berubah in_progress → submitted, menyimpan waktu server dan bukti GPS
  check-out terpisah dari check-in. Jadwal tetap pending. Submitted tidak dapat
  diedit atau di-check-out ulang; supervisor harus meminta revisi dahulu.
- Semua mutasi template/jawaban/check-out menaikkan version. Versi basi/status
  salah menghasilkan 409. Update version atomik mengunci row kunjungan sebelum
  menulis jawaban atau memeriksa kelengkapannya. Error membatalkan seluruh transaksi.
  Setelah respons terputus, GET ulang; idempotency/offline outbox belum tersedia.
- Data lama tetap utuh: kolom baru nullable; tidak ada seed atau pengisian
  template otomatis. Downgrade 0004 sengaja ditolak agar bukti tidak terhapus.

Contoh simpan jawaban (gunakan ID/version dari respons API):

```json
{
  "expected_version": 3,
  "answers": [{"item_id": "<UUID item>", "answer": "fail", "notes": "Kabel rusak; perlu penggantian"}]
}
```

Verifikasi 12 November 2026: pytest 15 passed, 1 skipped (PostgreSQL opsional),
unittest scaffold 3 passed. SQL upgrade sampai 0004 diperiksa offline.
Tes mencakup kelengkapan wajib, kepemilikan, versi basi, rollback saat input salah,
immutability template, binding kunjungan lama, status submitted dan jadwal pending.
Belum ada deployment atau migrasi pada PostgreSQL nyata; konkurensi/row lock
PostgreSQL serta migrasi dengan data lama masih wajib diuji pada staging.


## Review, revisi dan approval (revision 0005, 12 November 2026)

Alur: assigned → in_progress → submitted → approved, atau submitted →
revision_requested → submitted. Jadwal tetap pending sampai approval; transisi
kunjungan, penyelesaian jadwal dan penambahan riwayat berada dalam satu transaksi.

- `POST /visits/{id}/review` khusus supervisor, menerima `expected_version`,
  `decision` (`revision_requested` atau `approved`) dan `reason` tidak kosong
  (maksimal 5000 karakter). Hanya menerima kunjungan submitted dengan jadwal
  pending; versi basi, keputusan berulang dan status lain menghasilkan 409.
  Supervisor meninjau hasil gagal, pengecualian GPS serta PIC sebelum menyetujui
  dan mencatat pertimbangannya pada reason. Hasil fail tidak otomatis menolak
  approval: keputusan operasional tetap milik supervisor.
- Pada revision_requested, teknisi penanggung jawab dapat memperbaiki jawaban
  melalui endpoint checklist yang sama, lalu `POST /visits/{id}/resubmit` dengan
  `expected_version`. Kelengkapan wajib diperiksa lagi. GPS dan waktu check-out
  awal dipertahankan: pengiriman ulang ini revisi laporan, bukan kunjungan baru.
  Revisi tidak mewajibkan perubahan jawaban jika supervisor hanya memerlukan
  peninjauan ulang. Bukti GPS/PIC yang keliru belum dapat dikoreksi lewat API.
- Approval mengunci laporan dan menyelesaikan jadwal. Tidak ada endpoint untuk
  membuka kembali approved; koreksi setelah approval sebagai revisi laporan baru
  merupakan tahap berikutnya. Endpoint jadwal lama tidak dapat melewati workflow.
- `GET /visits/{id}/history` tersedia bagi supervisor dan teknisi pemilik tugas,
  dengan offset/limit (default 50, maksimal 100), berurutan berdasarkan version.
  Setiap event berisi aktor, waktu server, alasan, aksi dan snapshot kunjungan,
  template, jawaban, jadwal, perangkat dan hotel. Tidak ada endpoint update/delete
  riwayat. Perubahan master/jawaban berikutnya tidak mengubah JSON snapshot lama.
  Snapshot ini fondasi laporan; PDF dan ekspor Google belum tersedia.
- Setiap pengajuan awal setelah 0005 menyimpan event submitted; setiap pengiriman
  ulang dan review menyimpan event baru dengan version unik per kunjungan.
  Versi boleh melompat karena edit jawaban menaikkan version tanpa event workflow.
  Kunjungan yang sudah submitted sebelum upgrade tetap bisa direview; riwayatnya
  dimulai saat review pertama dan tidak mengarang pengajuan historis.
- Review mengunci jadwal lalu melakukan update status/version kunjungan atomik.
  Ini mencegah dua keputusan bersamaan sama-sama berhasil. Constraint/FK
  mempertahankan aktor dan objek yang dirujuk; downgrade 0005 ditolak untuk
  menghindari penghapusan riwayat. Tidak ada seed atau backfill.

Contoh keputusan supervisor:

```json
{
  "expected_version": 5,
  "decision": "revision_requested",
  "reason": "Lengkapi catatan tindakan untuk kabel yang gagal pemeriksaan"
}
```

Verifikasi terbaru: pytest 18 passed, 1 skipped; unittest scaffold 3 passed.
SQL upgrade sampai 0005 diperiksa offline. Tes mencakup siklus revisi/pengiriman
ulang/approval, pembatasan role/kepemilikan, versi basi, alasan kosong, snapshot
sebelum dan setelah revisi, laporan terkunci, serta rollback seluruh approval
jika penyimpanan riwayat gagal. PostgreSQL nyata, migrasi data lama dan perlombaan
transaksi paralel masih perlu diuji di staging. Belum dilakukan deployment.

## Pengujian PostgreSQL staging terisolasi

Suite opsional tersedia di `backend/tests/test_staging.py`. Siapkan **database
khusus pengujian** dengan nama berakhiran `_test` atau `_staging`, role yang dapat
membuat schema, serta driver `postgresql+psycopg`. Jangan gunakan URL produksi.
Masukkan `HOTEL_STAGING_DATABASE_URL` lewat environment/secret lokal tanpa
mencatat URL/password dalam source, chat atau log. Parameter query URL ditolak
agar tidak dapat mengubah database tujuan melalui parameter koneksi.

Setelah environment tersedia, jalankan:

```bash
.venv/bin/pytest -q backend/tests/test_staging.py
```

Setiap tes membuat schema acak `hotel_test_<hex>` di database tersebut; search_path
koneksi, tabel aplikasi dan alembic_version hanya memakai schema itu. Setelah tes,
suite menghapus hanya schema acak yang dibuatnya. Tidak menjalankan Compose,
bootstrap produksi atau migrasi pada database aplikasi. Kredensial/data contoh
di fixture hanya digunakan pada schema uji. Gunakan role khusus database uji.

Cakupan: upgrade dari 0001 dengan hotel/perangkat lama, upgrade berulang tanpa
perubahan data, alur revisi sampai approval, otorisasi, rollback riwayat gagal,
constraint PostgreSQL (hari pertama bulan, duplikasi jadwal dan FK), serta dua
keputusan supervisor serentak. Hanya satu keputusan boleh sukses; jadwal dan
riwayat harus mengikuti keputusan pemenang. Migrasi menerima connection khusus
melalui Alembic Config attributes untuk pengujian; CLI/Compose tetap memakai
konfigurasi koneksi normal.

Status eksekusi terbaru, 12 November 2026: **6 tes staging lulus pada
PostgreSQL 17.6** dalam container sementara dengan data tmpfs, nama acak dan
port acak yang hanya dipublikasikan di 127.0.0.1. Container dihentikan setelah
pengujian dan data sementaranya dibersihkan. Container aplikasi/database yang
sudah berjalan tidak diubah. Hasil ini memverifikasi migrasi dan workflow pada
PostgreSQL uji, bukan penerapan source terbaru ke aplikasi yang berjalan.

Docker Engine 29.9.3 aktif. Akses sesi telah diperluas; kesalahan konfigurasi
DOCKER_HOST yang menunjuk socket Podman tidak tersedia diperbaiki untuk shell
root melalui .profile dan .bashrc, dengan backup konfigurasi sebelumnya.
Shell baru menggunakan unix:///var/run/docker.sock dan Compose berhasil diakses.
Proses lama yang masih mewarisi DOCKER_HOST Podman perlu membuka shell login
baru atau memilih socket Docker secara eksplisit.


## Penerapan backend terbaru

Pada 12 November 2026, backup database 0001_initial berhasil dipulihkan ke
PostgreSQL 17.6 terpisah, lalu dimigrasikan sampai 0005_reviews. Fingerprint
seluruh row hotel/perangkat sama sebelum dan setelah migrasi uji maupun utama.
Database utama kemudian dimigrasikan dan API terbaru dijalankan dengan
compose.release.yaml. Health, koneksi database, kontrak OpenAPI endpoint baru,
penolakan akses anonim dan login dengan kredensial salah lolos pemeriksaan.
API/database healthy; API hanya bind 127.0.0.1:8000 dan DB tidak dipublikasikan.
Login positif/role/workflow telah diuji pada staging; belum dijalankan memakai
akun produksi karena tabel users masih kosong. Tidak ada akun atau data dummy
produksi yang dibuat. Bootstrap supervisor pertama memerlukan input operator
melalui terminal; lihat DEPLOYMENT.md. Pernyataan belum deploy pada catatan
verifikasi historis di atas menggambarkan status sebelum penerapan ini.


## Detail inventaris (revision 0006)

POST/PUT /devices menerima brand/model (maksimal 100), location (200), ip_address
(IPv4/IPv6 tanpa zone identifier), mac_address (6 pasang hex), notes (5000), semua
opsional. String kosong menjadi NULL; whitespace dibuang. MAC huruf kecil dengan
pemisah titik dua; IPv6 dikompresi. PUT adalah penggantian penuh, bukan PATCH.
Output koleksi/detail memuat field tersebut; supervisor yang menulis, kedua peran
membaca. Snapshot event baru menyertakan identitas perangkat lengkap; JSON event
lama tidak diubah/backfill. Kolom baru nullable, tanpa seed ataupun perubahan data
lama. Downgrade ditolak untuk menghindari kehilangan detail inventaris.

Migrasi telah diuji pada backup restore serta diterapkan. Verifikasi 27 backend,
7 PostgreSQL staging, 3 scaffold dan alur browser lulus. Delapan tes integrasi
dilewati pada suite default tanpa variabel koneksi staging. Record deployment dan
backup tercatat pada DEPLOYMENT.md; rancangan field lanjutan di DATA_REQUIREMENTS.md.


## Kunjungan hotel dan foto (0007)

Endpoint baru /hotel-visits berjalan berdampingan dengan endpoint perangkat lama,
tanpa backfill/konversi historis. Aturan foto wajib berlaku pada alur hotel baru;
router/switch dicakup dari inventaris saat penugasan, AP dipilih teknisi sebagai
sampling per lantai/titik. Bukti privat, hasil per perangkat, laporan utama,
FO/wireless sendiri/keduanya/failover/bonding dan riwayat snapshot tersedia.
Approval pending tidak menyelesaikan pekerjaan. Detail kontrak, ukuran foto,
penyimpanan/backup, pengujian dan batas fitur: HOTEL_VISITS.md.


## Speedtest (0008)

Worker LibreSpeed terpin mengukur download/upload/ping/jitter melalui transfer
FastAPI berbasis tiket khusus. Record metrik dan konteks disimpan pada
network_speedtests. Hanya hasil completed + HTTPS origin terkonfigurasi + Wi-Fi
yang dikonfirmasi dapat diterapkan ke AP terkait, memakai version check. Hasil
diagnostik/seluler/gagal/cancel tidak menjadi bandwidth AP. Sinyal/channel tidak
ditimpa. Aturan jaringan/transport, pembatasan transfer, credential in-memory,
endpoint dan cakupan pengujian di SPEEDTEST.md. PUBLIC_SPEEDTEST_ORIGIN belum
diaktifkan pada server saat ini; domain HTTPS masih dibutuhkan.


## Revisi laporan utama (0009)

Form terkini memakai nama pelanggan otomatis dari site, profil bandwidth/ambang
sekali per site dan penilaian download+upload otomatis. TX/RX/CCQ tidak lagi tampil
pada form baru, ditambah hasil link test radio dan lima keterangan LAN/Wireless/
Hotspot yang wajib. Tidak ada ambang default atau data produksi yang diisi rekaan.
REPORT_FORM.md menjadi petunjuk terbaru untuk bagian laporan utama; bagian di
atas yang menggambarkan form lama merupakan riwayat tahap sebelumnya.
