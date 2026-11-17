# Review migration fondasi sampling V2

Tanggal: 16 November 2026. Status: rancangan untuk review, belum menjadi revision
Alembic aktif dan belum diterapkan. Draft executable tersedia di
`docs/migrations/0010_sampling_foundation.py`, sengaja di luar direktori versions
agar tidak ikut `upgrade head`. Aturan dasar sampling disetujui untuk dilanjutkan
dalam percakapan; persetujuan itu tidak mencakup eksekusi migration/deployment.

Referensi: ROADMAP-V2.md, DATABASE-GAP-V2.md, models.py dan migration 0001–0009.
Head dan ukuran database produksi belum diperiksa. Nama revision kandidat:
`0010_sampling_foundation`, parent source `0009_site_report_profile`.

## Hasil yang dituju

Supervisor mengelola lantai dan titik dari server. Kunjungan V2 mempunyai cakupan
tersendiri yang membekukan lantai, titik, target dan periode. Dua titik pada AP
yang sama tetap mempunyai dua sesi pemeriksaan. Perubahan master tidak mengubah
kunjungan yang sudah dibuat. Tidak membuat titik contoh atau menafsirkan string
lokasi existing menjadi master secara otomatis.

## Batas tahap pertama

Tambahkan lima tabel baru berikut. Semua ID UUID, waktu `timestamptz`, FK memakai
`ON DELETE RESTRICT`; tidak ada DROP, rename, backfill, seed, atau perubahan enum
existing. UUID record dapat disediakan klien dan divalidasi server. Timestamp
server memakai `now()`; waktu pengamatan perangkat kelak disimpan terpisah.

| Tabel | Kolom dan aturan minimum |
| --- | --- |
| `hotel_floors` | `id` PK, `hotel_id` FK hotels, `name varchar(100)` nonblank, `position integer >= 0`, `default_sampling_count integer > 0 DEFAULT 4`, `version integer >= 1 DEFAULT 1`, `created_at`, nullable `archived_at` |
| `sampling_points` | `id` PK, `floor_id` FK hotel_floors, `name varchar(200)` nonblank, nullable `location text`, `position integer >= 0`, nullable `device_id` FK devices, `version >= 1 DEFAULT 1`, `created_at`, nullable `archived_at` |
| `sampling_coverages` | `id` PK, `hotel_visit_id` FK hotel_visits UNIQUE, `period date` CHECK hari pertama bulan, `hotel_snapshot jsonb NOT NULL`, `photo_policy_snapshot jsonb NOT NULL`, `schema_version integer DEFAULT 1 CHECK = 1`, `created_by` FK users, `created_at` |
| `sampling_coverage_floors` | `id` PK, `coverage_id` FK sampling_coverages, `floor_id` FK hotel_floors, `name_snapshot varchar(100)`, `position_snapshot integer >= 0`, `target_count integer > 0`, UNIQUE(coverage_id, floor_id), UNIQUE(id, coverage_id) |
| `sampling_sessions` | `id` PK, `coverage_id` FK sampling_coverages, `coverage_floor_id`, `sampling_point_id` FK sampling_points, `point_snapshot jsonb NOT NULL`, `position_snapshot integer >= 0`, `status varchar(20) DEFAULT 'untested'`, `version integer >= 1 DEFAULT 1`, `created_at`, nullable `observed_at`; UNIQUE(coverage_id, sampling_point_id); composite FK(coverage_floor_id, coverage_id) ke sampling_coverage_floors(id, coverage_id) |

Status sesi: `untested`, `good`, `attention`, `problem`, dengan CHECK. Status ini
adalah hasil kondisi titik, bukan bukti bahwa pemeriksaan lengkap atau submit sah.
API tahap awal belum boleh menerima perubahan status menjadi selesai tanpa
validator evidence yang diimplementasikan pada tahap pengukuran berikutnya.

Snapshot hotel berisi ID/nama/alamat pelanggan; snapshot titik berisi ID/nama/lokasi
titik serta ID/identitas AP opsional. Gunakan versi format dan validasi Pydantic;
JSON tidak menggantikan relasi atau aturan kepemilikan. Target per lantai tetap
disimpan meski belum ada titik, supaya kekurangan konfigurasi tidak tersembunyi.

### Constraint dan indeks

- Nama aktif unik per hotel untuk lantai, per lantai untuk titik: partial unique
  index `(hotel_id, lower(btrim(name))) WHERE archived_at IS NULL`, dan bentuk
  ekuivalen pada `(floor_id, lower(btrim(name)))`.
- Indeks urutan aktif `(hotel_id, position, id)` pada lantai dan
  `(floor_id, position, id)` pada titik, keduanya partial untuk master aktif.
  Posisi boleh sama; ID menjadi tie-breaker agar reorder tidak memerlukan
  constraint deferred. API menerima urutan lengkap lalu menulis dalam transaksi.
- Tambahkan indeks FK penuh `hotel_floors(hotel_id)`,
  `sampling_points(floor_id)`, `sampling_points(device_id)`: indeks aktif saja
  tidak mencakup histori archive untuk pemeriksaan FK.
- UNIQUE coverage hotel_visit sudah mencakup pencarian FK tersebut. UNIQUE
  coverage_floors(coverage_id, floor_id) mencakup filter coverage; tambahkan
  indeks `sampling_coverage_floors(floor_id)`.
- Tambahkan indeks `sampling_coverages(created_by)`,
  `sampling_sessions(coverage_floor_id, coverage_id)`,
  `sampling_sessions(sampling_point_id)`, dan
  `sampling_sessions(coverage_id, status)` untuk relasi/progress.
- UNIQUE sesi tidak memasukkan device_id: satu AP boleh melayani banyak titik.
  device_id boleh NULL; jangan membuat AP fiktif untuk melengkapi FK.

### Integritas yang wajib ditangani API

FK di atas belum membuktikan hotel visit sama dengan hotel master lantai atau AP.
Saat membuat coverage, lock baris kunjungan dan master terkait dalam urutan tetap;
validasi semua floor/point/device satu hotel, aktif, dan point berada di floor
yang dipilih. Tolak AP jenis selain `ap`. Pemindahan hotel/floor induk setelah
pembuatan master dilarang melalui API; pindah lokasi dilakukan dengan archive
dan record baru. Endpoint perubahan hotel perangkat existing juga harus menolak
pemindahan AP yang direferensikan titik. Uji transaksi bersamaan wajib dilakukan.

Jangan memakai CHECK lintas tabel. Alternatif composite FK lintas semua induk
memerlukan UNIQUE tambahan pada tabel existing dan analisis lock terpisah;
tidak disisipkan ke migration ini. Penulisan langsung SQL di luar API tetap
memerlukan prosedur operator yang menjaga aturan lintas hotel tersebut.

## Perilaku dan kompatibilitas

1. Master baru kosong. Membuat lantai memberi target empat, bukan membuat empat
   record lokasi tanpa nama. Supervisor mengisi lokasi nyata sebelum kunjungan V2.
2. Buat coverage dan seluruh floor/session dalam satu transaksi untuk kunjungan
   `assigned` yang belum check-in. Copy semua lantai/titik aktif; target sesi per
   lantai `max(default_sampling_count, jumlah titik aktif)`. Tolak aktivasi jika
   ada lantai kurang titik, hotel tanpa lantai, atau foto wajib belum dikonfigurasi.
3. Period adalah tanggal awal bulan dari planned_date, disalin saat aktivasi.
   Banyak kunjungan per hotel per bulan tetap boleh; tidak ada UNIQUE hotel+bulan.
4. Coverage immutable setelah aktivasi. Rename/archive master tidak mengubahnya;
   penambahan cakupan sesudah check-in membutuhkan rancangan revisi terpisah.
   Perubahan planned_date ke bulan lain pada visit bercakupan ditolak di API.
5. Request aktivasi ulang dengan cakupan sama mengembalikan coverage existing;
   cakupan berbeda menghasilkan 409. Compare payload yang dinormalisasi di dalam
   transaksi. UNIQUE hotel_visit mencegah coverage ganda pada request bersamaan.
6. Visit lama tanpa coverage tetap memakai jalur legacy, tidak otomatis diberi
   label memenuhi V2. Existing models/API belum diubah oleh dokumen ini.
7. Saat API V2 diimplementasikan, check-out/resubmit existing wajib mengenali
   coverage: gunakan validator V2 atau tolak submit dengan pesan belum tersedia
   sampai validator siap. Jangan izinkan jalur legacy melewati kewajiban V2.
8. Angka progress resmi berasal dari cakupan server dan evidence diterima,
   bukan status lokal. Penambahan sesi ke snapshot event wajib sebelum submit V2.

## Kontrak API yang akan diimplementasikan sesudah review

| Operasi | Kontrak kandidat |
| --- | --- |
| Master lantai | GET/POST `/hotels/{id}/floors`, PATCH `/hotels/{id}/floors/{floor_id}` |
| Master titik | GET/POST `/hotels/{id}/floors/{floor_id}/sampling-points`, PATCH pada `/{point_id}` |
| Archive/reorder | PATCH master dengan `expected_version`; reorder seluruh daftar aktif dalam transaksi |
| Aktivasi cakupan | POST `/hotel-visits/{id}/sampling-coverage`, supervisor, expected_version visit dan versi master yang ditinjau |
| Baca cakupan | GET `/hotel-visits/{id}/sampling-coverage`, supervisor atau teknisi pemilik kunjungan |

GET daftar tetap berpaginasi. Semua mutasi master hanya supervisor. Ownership
teknisi mengikuti backend existing. PATCH versi stale menghasilkan 409 tanpa
overwrite. UUID yang sama untuk resource/payload berbeda menghasilkan konflik.
Foto wajib belum diputuskan kategorinya: aktivasi V2 harus menunggu konfigurasi
eksplisit supervisor; jangan menetapkan kategori wajib secara diam-diam.

## Tahap lanjutan yang tidak termasuk revision ini

- Connection/scan native beserta source, timestamp, izin dan BSSID multi-radio.
- Relasi run LibreSpeed ke sesi dan dukungan AP tak dikenal. Kolom
  network_speedtests.visit_device_id existing masih NOT NULL; perlu rancangan
  additive khusus, bukan memaksakan inventaris AP.
- Pemilihan accepted run per sesi; completed harus bermetrik aktual dan koneksi
  Wi-Fi tervalidasi, gagal wajib alasan dan finding. Aborted bukan gagal beralasan.
- Foto privat per sesi/visit, temuan, retry UUID/idempotency dan konflik offline.
- PIC/signature terikat versi snapshot, kemudian PDF dan integrasi Google.

## Dampak operasional dan verifikasi sebelum penerapan

Tabel baru kosong menghindari rewrite/backfill data lama. DDL tetap membutuhkan
lock pada tabel yang direferensikan FK; durasi tidak dapat dijamin sebelum audit
database aktual. Tinjau SQL offline, gunakan lock_timeout yang disepakati dan
transaksi migration singkat. Kegagalan harus membatalkan transaksi, bukan diteruskan.
Tidak ada perubahan Docker, network, credential, atau permission database di sini.

Sebelum revision diterapkan: review kode Alembic/SQL, backup dan bukti restore,
verifikasi head aktual 0009 serta schema drift, lalu uji database PostgreSQL
terisolasi. Downgrade yang menghapus tabel berisi histori tidak disediakan;
pemulihan aplikasi memakai pembaca legacy dan perbaikan schema forward yang
direview. Jangan mengubah head Alembic secara manual.

Acceptance test untuk implementasi:

- Upgrade dari 0009 dengan record legacy tetap utuh; tidak ada seed produksi.
- FK, CHECK, partial uniqueness dan archive diuji pada PostgreSQL nyata.
- Dua titik satu AP berhasil; lintas hotel, salah floor dan AP non-AP ditolak.
- Target empat/lebih, lantai kosong dan master archived memberi hasil yang benar.
- Rename/reorder master tidak mengubah snapshot; revisit bulan sama tetap boleh.
- Aktivasi bersamaan/retry tidak menggandakan sesi; versi stale memberi 409.
- Teknisi tidak bisa mutasi master atau membaca visit teknisi lain.
- Visit bercakupan tidak dapat submit lewat validator legacy.
- Seluruh suite backend existing tetap lulus; Web/Android lama tetap membaca visit
  tanpa coverage. Uji Web/Android V2 dilakukan saat integrasi API tersedia.

Draft diuji melalui kompilasi SQL PostgreSQL offline, termasuk pemeriksaan bahwa
head aktif tetap 0009. Ini belum membuktikan DDL berhasil pada PostgreSQL nyata.
Belum ada schema/model/API baru yang aktif atau klaim fondasi sudah terimplementasi.
