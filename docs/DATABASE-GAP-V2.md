# Database Gap V2 — Phase 1

Tanggal: 13 November 2026. Status: rancangan konseptual untuk review, tanpa SQL,
file migration baru, perubahan data atau eksekusi migration.
Referensi: `AGENTS.md`, `ROADMAP-V2.md`, `ARCHITECTURE-V2.md`.

## Batas audit

Schema di bawah berasal dari `backend/app/models.py` dan
`database/migrations/versions/0001_initial.py` sampai `0009_site_report_profile.py`.
Rantai migration source linear 0001–0009. Head database berjalan, jumlah record,
drift schema, kualitas data dan index aktual belum diperiksa. Jangan menganggap
keberadaan file migration membuktikan migration sudah diterapkan di produksi.

## Inventaris existing dan penggunaan kembali

| Tabel | Fungsi/relasi penting | Keputusan V2 |
| --- | --- | --- |
| hotels | UUID, nama/alamat, customer_name, maintenance_profile JSON (0009) | Master hotel dan profil SLA tetap dipakai |
| devices | FK hotel, router/switch/ap, lokasi/IP/MAC dan identitas | Inventaris tetap; lokasi string bukan master lantai/titik |
| users | UUID, username unik, technician/supervisor, aktif | Identitas dan ownership tetap |
| login_sessions | Hash token, FK user, expiry | Pertahankan auth |
| maintenance_schedules | FK device/technician, month, status; unik device+month | Domain jadwal perangkat lama, bukan jadwal hotel V2 |
| visits | FK schedule unik, template, GPS/waktu, status/version dan pengecualian PIC | Pertahankan histori legacy; jangan campur dengan hotel_visits |
| checklist_templates | Template revision immutable, jenis perangkat | Pertahankan template legacy |
| checklist_items | FK template; unik template+position | Pertahankan isi dan urutan |
| checklist_results | FK visit/item; unik visit+item, answer dan notes | Hasil legacy tetap terbaca |
| visit_events | FK visit/aktor, version/action/snapshot; unik visit+version | Audit trail legacy tetap |
| hotel_visits | FK hotel/teknisi, planned_date, workflow/version, report/checkin/checkout JSON | Agregat utama maintenance hotel V2 |
| hotel_visit_devices | FK hotel_visit/device, snapshot, floor/point string, result JSON; unik visit+device | Pemeriksaan inventaris existing; belum identitas titik fisik |
| device_photos | FK hotel_visit_device/uploader; object_key unik, hash/ukuran/dimensi/waktu | Upload privat perangkat tetap dipakai |
| hotel_visit_events | FK hotel_visit/aktor, version/action/snapshot; unik visit+version | Audit trail hotel tetap; perlu snapshot domain baru |
| network_speedtests | FK hotel_visit_device/aktor; band, status, waktu/expiry, context/metrics/error | Pakai ulang mesin/run; butuh relasi sesi sampling |

Mayoritas FK domain menggunakan RESTRICT; login_sessions memakai CASCADE terhadap
user. UUID sudah umum tetapi dihasilkan server; ini belum kontrak sinkronisasi
UUID dari klien. JSON existing memberi fleksibilitas namun tidak menjamin FK,
unit, kepemilikan dan kelengkapan setiap pengukuran pada tingkat database.

## Gap terhadap aturan V2

| Kebutuhan | Gap dan dampak |
| --- | --- |
| Master lantai dan titik | Belum ada tabel; IndexedDB per akun/browser tidak konsisten antar teknisi |
| Empat sampling default | Hanya target/placeholder lokal; bukan empat record master/sesi persisten |
| Sesi bulanan per lokasi | floor/point string tidak stabil; unique visit+device melarang satu AP dipakai dua titik pada visit sama |
| Histori periode | planned_date tersedia, periode eksplisit dan snapshot cakupan belum ada; ubah nama/lokasi master berpotensi mengaburkan pembandingan |
| Analyzer Android | Belum ada connection/scan table, timestamp/source/permission/transport terstruktur |
| AP berdasarkan BSSID | devices.mac_address tunggal tidak cukup untuk beberapa BSSID/band/radio per AP |
| Speedtest setiap titik | Run mengacu perangkat; complete() tidak mewajibkan run; hasil manual masih diterima |
| Gagal Diuji | failed/aborted tersedia pada run, tetapi alasan input tidak selalu wajib dan belum menghasilkan finding per sesi |
| Foto sampling/utama | Foto server hanya perangkat; kategori/caption/sync metadata sampling lokal belum tersimpan backend |
| Temuan | outcome/notes dan draf lokal, belum lifecycle finding terstruktur atau agregat total resmi |
| PIC dan PDF | Pengecualian PIC tersedia; belum signature, bukti review PIC, report artifact versi tertentu |
| Offline/sync | Belum idempotency UUID klien, operasi/ack/retry, aturan konflik lintas perangkat |

Nama tabel dalam roadmap adalah kandidat, bukan kewajiban membuat tabel duplikat.
Khusus speedtest_results, pilih perluasan `network_speedtests` daripada membuat
dua sumber kebenaran metrik yang sama.

## Model konseptual additive yang diusulkan

Semua nama/kolom berikut usulan; tipe, constraint dan migration detail harus
direview sebelum implementasi. Gunakan UUID, timestamp timezone-aware dan FK
RESTRICT untuk histori. Archive master daripada menghapus data yang dirujuk.

| Entitas | Kolom/relasi minimum yang diusulkan | Integritas/indeks utama |
| --- | --- | --- |
| hotel_floors | id, hotel_id, name, position, default_sampling_count=4, archived_at, version | FK hotel; target positif; urutan stabil, aturan nama aktif unik per hotel |
| sampling_points | id, floor_id, name/location, position, optional device_id, archived_at, version | FK floor; AP opsional harus satu hotel; satu AP boleh banyak titik |
| sampling_sessions | id UUID klien, hotel_visit_id, sampling_point_id, snapshot hotel/floor/point/period, status, observed_at, actor_id, version, catatan/tindakan/rekomendasi | Satu sesi kanonis visit+point; attempt pengukuran terpisah; indeks visit+status dan point+periode |
| wifi_connection_results | id, session_id, observed_at, source, SSID/BSSID, optional matched_device_id, frequency/channel/band, RSSI, link speed, IP/gateway, transport, permission state | FK sesi; unit/range tervalidasi; unavailable tidak diisi angka palsu; indeks sesi+waktu |
| wifi_scan_results | id, session_id, scan_batch_id, observed_at, OS timestamp, cached/source, SSID/BSSID, frequency/channel/band, RSSI | Satu baris jaringan per batch; batch menyimpan waktu/izin/status agar scan kosong/gagal tetap tercatat |
| network_speedtests (perluasan) | Nullable sampling_session_id untuk kompatibilitas, transport/BSSID saat mulai/selesai dalam konteks terversi, failure reason, accepted run reference | FK sesi; kunjungan/perangkat cocok; indeks sesi+waktu; setiap attempt immutable setelah finish |
| sampling_photos | id UUID klien, session_id, category, captured_at, notes, uploader, object_key/hash/size/dimensions | FK sesi; object key unik; metadata dan upload lengkap sebelum acknowledged |
| maintenance_findings | id, hotel_visit_id, optional session_id/device_id, category/severity, description, action, recommendation, status, actor/time | Jika session diisi harus pada visit sama; indeks visit+status |
| maintenance_signatures | id, hotel_visit_id, report_version, PIC name/position, signed_at, signature object/hash, reviewed snapshot/hash | Ikat bukti ke versi laporan; perubahan setelah tanda tangan perlu review ulang |
| maintenance_reports | id, hotel_visit_id, report_version, snapshot/schema_version, generated_at, state, object_key/hash/error | Unik visit+versi+jenis artifact; PDF dari snapshot yang ditinjau |

Tambahan pendukung yang perlu dipilih dalam review: `device_bssids` (device_id,
BSSID normalisasi, radio/band) untuk AP multi-radio; scan batch metadata; serta
dokumentasi utama visit. Dokumentasi utama dapat memakai tabel attachment bersama
dengan scope visit/session/device yang tegas, atau tabel terpisah. Jangan
memaksakan foto rack/backbone menjadi foto sebuah AP atau membuat FK polymorphic
tanpa validasi. Kebijakan kewajiban foto per kategori juga belum menjadi konfigurasi.

Periode awal dapat diturunkan dari planned_date untuk tampilan. Untuk histori
bulanan stabil, usulkan periode snapshot pada cakupan visit/sesi (bulan hari pertama)
serta snapshot label hotel/lantai/titik/AP. Tentukan timezone hotel dan aturan
revisit. Jangan menambahkan unique hotel+bulan sebelum kebutuhan beberapa visit
dan penugasan teknisi pada bulan yang sama diputuskan.

Hubungan utama: hotel → floor → point; hotel → hotel_visit → sampling_session →
connection/scan/speedtest/photo. Session merujuk point dan membekukan konteks
periode kunjungan. FK terpisah saja tidak menjamin point dan visit satu hotel:
pilih composite FK/constraint yang tepat dan validasi transaksi server. Jangan
menduplikasi hotel/floor/period di setiap child tanpa aturan konsistensi.

## Aturan bisnis dan kontrak data untuk direview

1. Empat adalah default konfigurasi lantai baru, bukan batas maksimum atau alasan
   membuat dummy pada hotel existing. Buat cakupan sesi dari titik yang disetujui;
   titik/lantai tambahan harus ikut denominator progress. Perubahan master tidak
   boleh diam-diam mengubah cakupan kunjungan yang telah ditinjau.
2. Satu speedtest untuk satu sesi titik. Completed harus mempunyai metrik aktual,
   server, timestamp dan bukti koneksi Wi-Fi yang dituju; failed wajib alasan dan
   finding. aborted/running bukan sukses. Nilai nol sah bila hasil nyata; missing
   memakai null/status. Jitter nullable ketika mesin tidak menyediakannya (schema
   existing masih mewajibkan jitter untuk completed).
3. Simpan attempt pengujian dan sumber hasil; pilih accepted run secara eksplisit,
   jangan menghitung run lama yang tidak relevan. Constraint legacy band_24/band_5
   tetap, tanpa mengklaim band lain atau radio_verified dari konfirmasi browser.
4. Status sampling Baik/Perlu Perhatian/Bermasalah/Belum Diperiksa terpisah dari
   status uji dan workflow visit. Rumus progress resmi perlu syarat laporan,
   semua sesi, speedtest atau gagal beralasan, foto, temuan dan review PIC.
5. Kegagalan/penolakan permission, cache scan dan offline dicatat sebagai kondisi
   nyata. SSID tersembunyi/tidak tersedia bukan alasan mengarang identitas.
6. Offline memakai UUID klien dan idempotency key unik per scope/operasi; retry
   payload sama menghasilkan record sama, payload berbeda memberi konflik.
   Perubahan memakai expected_version, bukan last-write-wins diam-diam. Simpan
   captured_at terpisah dari received_at; jangan percaya jam HP sebagai jam server.
7. Signature/PDF merujuk versi snapshot yang sama. Perluasan snapshot event harus
   mencakup sesi, temuan dan bukti baru agar revisi dapat diaudit.
8. File privat memerlukan ownership, kategori, batas ukuran, hash dan lifecycle
   upload. Status lokal pending/uploading/synced/failed bukan bukti server telah
   menerima foto sampai ada acknowledgment. Kebijakan retensi draf perangkat
   bersama perlu ditentukan tanpa menghapus data secara otomatis sekarang.

## Strategi kompatibilitas dan review migration

Tahap pertama kelak: tabel baru dan kolom nullable; endpoint lama, JSON report
versi 1/2, tabel legacy dan riwayat foto/speedtest tetap dibaca. Tidak rename/drop
tabel/kolom atau mengganti enum workflow lama untuk label UI baru.

Jangan backfill otomatis floor/point string menjadi master: perbedaan ejaan,
duplikasi, lokasi/AP berganti dan snapshot kunjungan memerlukan inventaris data
read-only serta pemetaan yang disetujui. Record lama tanpa pengukuran native/run
tidak boleh diberi status sudah memenuhi V2. Labeli sebagai histori legacy.
Jika perlu memperluas relasi speedtest agar AP tidak dikenal dapat diuji, rancang
nullable visit_device_id dan constraint hubungan secara additive dengan review
kompatibilitas; jangan membuat inventaris AP fiktif untuk memenuhi FK lama.

Sebelum migration diajukan: konfirmasi periode/revisit, cakupan snapshot, AP banyak
BSSID, mandatory photo, status/approval PIC, sync conflict dan otorisasi teknisi.
Lalu review SQL upgrade, FK/unique/check/index, lock/backfill pada ukuran data nyata,
kompatibilitas pembaca lama dan rencana pemulihan tanpa drop data baru. Uji di
database terisolasi dengan data uji, termasuk dua titik pada satu AP, lintas hotel,
retry UUID, konflik versi, gagal speedtest, file belum synced dan histori bulanan.
Review rancangan tidak sama dengan izin menjalankan migration produksi.

## Prioritas dan batas Phase 2

Prioritas fondasi berikutnya: master lantai/titik dan snapshot sesi → agregat/progress
→ koneksi/scan native → asosiasi speedtest per titik → foto/temuan/signature → PDF.
Urutan implementasi mengikuti fase roadmap dan persetujuan pengguna; fondasi yang
menjadi dependensi UI harus diajukan secara eksplisit sebelum perubahan backend.
Phase 2 dapat menyelaraskan tampilan existing dengan penanda lokal/unavailable,
tetapi tidak dapat menjanjikan progress lintas perangkat tanpa fondasi tersebut.

Tidak ada perubahan database, migration, Docker, jaringan atau deployment pada
Phase 1. Phase 2 belum dimulai.
