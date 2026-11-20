# Status setelah persetujuan — backend sudah aktif

18 November 2026: operator menyetujui aktivasi. Migration 0010–0012 sudah dipromosikan
ke chain Alembic dan diterapkan setelah backup/restore salinan terbukti menjaga
seluruh data lama. Source backend/Web serta gate field sampling, observasi dan
speedtest sudah aktif pada https://maintenance.inisaja.id. Tidak ada data dummy
produksi. Lihat [catatan rilis](DEPLOYMENT.md) untuk bukti dan backup. Radio/throughput HP
masih perlu diuji teknisi; completion V2 belum diaktifkan.

Rincian di bawah mencatat implementasi dan status sebelum aktivasi.

# Lokasi sampling dinamis dari Android teknisi

18 November 2026. Implementasi source lokal atas perubahan kebutuhan operator.
Tidak menjalankan migration/deployment produksi atau memasukkan data dummy.

## Alur

Setelah check-in, teknisi yang ditugaskan membuka Sampling → Tambah lantai /
titik sampling. Pilih lantai yang sudah ada pada kunjungan atau nama lantai/area
baru. Isi nama/lokasi titik nyata, AP dari inventaris hotel jika dikenali, dan
alasan penambahan. Form awal 4 baris; baris kosong tidak menjadi record. Minimal
satu titik nyata per kiriman, maksimal 32. Target awal lantai tetap 4 dan naik
bila jumlah titik nyata melebihi target. Progress menghitung target yang belum
terpenuhi tanpa membuat sesi fiktif.

Form tersimpan dalam IndexedDB per akun/origin/kunjungan, dapat diisi offline.
Pengiriman memerlukan koneksi dan fitur server aktif. Sebelum request, UUID dan
payload dibekukan dalam outbox. Respons hilang mengunci perubahan kiriman dan
menawarkan kirim ulang payload sama. Penolakan definitif membuka draf untuk
review; konflik versi memuat ulang visit tanpa retry otomatis. Tidak menyimpan
tiket atau kredensial dalam outbox. Hasil API diterapkan ke cache visit.

AP tidak dikenal boleh ditambahkan sebagai lokasi, tetapi start speedtest tetap
memerlukan AP inventaris aktual yang dapat dicocokkan. Analyzer native dapat
membaca radio; bila speedtest tidak dapat dilakukan, catat gagal uji beralasan.
Tidak membuat perangkat/AP palsu atau memakai satu hasil untuk beberapa titik.

## API dan audit

- GET `/hotel-visits/{identifier}/sampling-inventory`: AP hotel kunjungan untuk
  teknisi yang ditugaskan.
- POST `/hotel-visits/{identifier}/sampling-locations`: UUID, versi visit,
  coverage_floor_id atau floor_name (pilih salah satu), alasan, daftar titik.

Hanya teknisi pemilik visit dalam status in_progress/revision_requested yang
boleh menambah lokasi. Supervisor dan teknisi lain tidak mendapat mutasi lapangan
ini. Status assigned perlu check-in dulu, submitted/approved ditolak. Replay
request tersimpan tetap read-only, termasuk setelah visit selesai.

Mutasi mengunci visit lalu hotel, memeriksa versi serta ownership ulang, dan
menambahkan master lantai/titik nyata bila belum ada. Master existing tidak
ditulis ulang. Session menyimpan snapshot pemetaan lokasi/AP aktual per kunjungan;
kunjungan lain dapat memakai mapping berbeda tanpa mengubah histori sebelumnya.

Cakupan yang belum ada bisa dibuat saat visit aktif secara eksplisit lewat form.
Kunjungan/device/laporan AP lama tetap ada; hasil AP tidak disalin menjadi bukti
sampling. Cakupan awal lapangan mencakup lokasi yang diinput, dengan kebijakan
foto titik AP+area. Cakupan sebelumnya, jika ada, dipertahankan dan hanya ditambah.

Audit `HotelVisitEvent` menyimpan UUID request, actor, alasan, versi visit baru,
payload, daftar session tambahan dan snapshot hasil transaksi. UUID payload
berbeda/scoped berbeda ditolak. Floor asing, AP hotel lain/non-AP, duplikasi titik,
versi stale dan status terkunci ditolak atomik tanpa penambahan sebagian.

Tidak ada schema/migration baru selain tujuh tabel pada draft 0010–0012. FK
sampling_point_id tetap menghubungkan lokasi nyata, sedangkan metadata aktual
ada di snapshot session. Gate tambahan default mati:
SAMPLING_FIELD_ENABLED=true bersama SAMPLING_MASTER_ENABLED=true. Capabilities
dan detail coverage mengumumkan gate. Mematikan gate tidak menghapus histori.

Submit/completion V2 tetap belum aktif sampai dokumentasi per sesi dan PIC siap.
Tidak ada klaim lokasi selesai hanya karena form tambah lokasi tersimpan.

## Verifikasi

Tes backend: ownership/status/gate, atomic rejection, default target 4, UUID replay,
audit, append pada cakupan lama, versi stale serta pemetaan kunjungan berikut yang
tidak mengubah snapshot/master sebelumnya. PostgreSQL terisolasi juga memeriksa
replay konkuren dengan satu hasil. Test frontend menguji outbox lost acknowledgment,
penolakan definitif, gagal persist dan isolasi scope.

Regresi browser Web → FastAPI → SQLite → Android melakukan tambah lantai dan
titik oleh teknisi, memilih AP, kehilangan respons, replay tanpa duplikasi, append
lagi, target 4 dan cache offline. Seluruh fixture berada di database sementara.
Pengujian radio/throughput HP bukan bagian fixture ini. Backend produksi masih
0009 dan source baru belum terpasang; form menyatakan server belum aktif sampai
release backend/schema/gate yang direview dan disetujui selesai.

Hasil akhir lokal: 79 test backend lulus (25 opt-in dilewati pada suite default),
24 test PostgreSQL 18.6 terisolasi lulus, 40 test frontend lulus, build/typecheck/lint
dan kedua regresi browser lulus. APK debug versi 1.1.0 (versionCode 2) disiapkan
untuk pembaruan APK sebelumnya; radio fisik/throughput tetap memerlukan uji HP
setelah backend aktif. Tidak ada migrasi/deployment produksi pada tahap ini.

APK signature/version terverifikasi. SHA-256:
`c68bea0d73ff5f47325e17044a53a5638b2c8731713f6438ee9070fa75d17938`.
