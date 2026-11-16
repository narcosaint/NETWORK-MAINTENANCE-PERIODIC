# Kunjungan hotel dan bukti foto — revision 0007

Sudah diterapkan pada 12 November 2026. Gunakan menu **Kunjungan hotel** untuk
penugasan baru. Satu kunjungan menghasilkan satu laporan hotel dengan hasil
router/switch/LAN dan AP sampling. Fitur kunjungan/jadwal per perangkat lama tetap
tersimpan dan dapat ditinjau/diselesaikan lewat menu terpisah. Dashboard tidak
lagi menawarkan pembuatan jadwal/kunjungan baru melalui alur perangkat lama;
endpoint lama tetap tersedia untuk kompatibilitas, bukan cakupan aturan foto baru.

## Supervisor

1. Pastikan inventaris hotel berisi router, switch dan AP dengan identitas nyata.
2. Pilih **Kunjungan hotel → Jadwalkan kunjungan hotel**: hotel, teknisi aktif,
   tanggal rencana. Semua router/switch yang terdaftar saat itu di-snapshot menjadi
   cakupan. Minimal satu router atau switch diperlukan. Penambahan/perubahan
   inventaris kemudian tidak mengubah cakupan atau identitas perangkat snapshot.
3. Teknisi memilih AP sampling pada saat pemeriksaan. Tidak ada kuota 4+2 yang
   dipaksakan. Setiap AP dipilih sekali, harus milik hotel tersebut, dengan lantai
   dan kamar/koridor/titik yang diisi. AP yang belum ada perlu didaftarkan melalui
   inventaris. AP yang tidak dipilih tidak dianggap telah diperiksa.
4. Review laporan submitted beserta setiap foto, hasil, alasan dan pengecualian.
   Minta revisi atau setujui dengan catatan. Approved mengunci perubahan.
   **Approval pekerjaan pending tidak berarti maintenance selesai.** Untuk tindak
   lanjut, supervisor dapat membuat kunjungan hotel baru; tautan formal antar
   kunjungan/follow-up otomatis belum tersedia.

## Teknisi

1. Masuk sebagai teknisi yang ditugaskan; buka kunjungan lalu check-in. GPS/waktu
   server dicatat, atau alasan sebenarnya bila GPS tidak tersedia.
2. Pilih AP sampling dan isi lantai serta kamar/koridor. AP tanpa hasil/foto boleh
   dibatalkan saat in_progress. Sampel yang sudah diperiksa/difoto tidak dapat
   dihapus, dan sampel pada fase revisi tidak dapat dibuang.
3. Setiap router/switch/AP sampel: isi hasil baik/bermasalah/tidak berlaku dan
   catatan tindakan/alasan jika bukan baik. Unggah **minimal satu foto kondisi**
   pada perangkat itu, pada kunjungan ini. Tidak ada bypass foto melalui alasan.
4. Untuk AP: isi pengukuran band 2,4 dan/atau 5 GHz secara manual, dengan sinyal,
   channel, bandwidth, SSID/BSSID opsional. Tandai band tidak tersedia/belum diuji
   dan beri alasan; jangan mengisi angka rekaan. Hasil parsial yang tidak tersedia
   perlu alasan. Jika AP mati dan kedua band tidak bisa diuji, hasil perangkat
   harus bermasalah, ada alasan per band, dan pekerjaan dicatat pending.
5. Isi laporan utama: koneksi FO saja/wireless saja/keduanya/failover/bonding,
   hasil tiap koneksi yang dipakai, konektor router/switch, signal test LAN,
   blank spot, hotspot, PIC, ringkasan serta status pekerjaan. Speedtest backbone
   yang tidak tersedia diberi alasan. Keputusan kesesuaian bandwidth masih manual;
   belum ada klasifikasi/ambang otomatis yang disepakati.
6. Tanda tangan belum tersedia: nama PIC dan alasan pengecualian wajib dicatat
   untuk review, tanpa membuat tanda tangan palsu. Isi feedback/solusi bila ada.
7. Check-out/kirim setelah semua hasil/foto tersimpan. Minimal satu AP sampel
   diperlukan pada alur hotel ini. Laporan tanpa foto/bukti/hasil wajib ditolak
   server, seluruh mutasi status/version dibatalkan dan draft tetap tersimpan.
8. Saat revisi, perbaiki hasil/laporan dan tambahkan foto bila diperlukan, lalu
   kirim ulang. Waktu/lokasi check-out awal dipertahankan. Approved tidak dapat
   diedit atau ditambah foto.

Setiap edit menaikkan version; konflik menghasilkan 409, bukan overwrite diam-diam.
Reload untuk memeriksa status jika respons koneksi terputus. Belum ada outbox,
idempotency key, auto-retry upload atau mode offline. Simpan form sebelum pindah
halaman; browser token hanya di memori dan reload memerlukan login kembali.

## Foto privat

- JPEG/PNG/WebP statis, input maksimal 10 MiB, sisi minimal 32 px, maksimal 20 MP;
  maksimal 10 foto per perangkat per kunjungan. Format berkas benar-benar dibaca,
  bukan hanya ekstensi/MIME. Gambar animasi/SVG dan MIME palsu ditolak.
- Server merotasi sesuai EXIF lalu menyimpan JPEG yang dinormalisasi tanpa metadata
  EXIF. SHA-256, ukuran, dimensi, uploader dan waktu penerimaan server dicatat.
  Waktu penerimaan bukan jaminan waktu pengambilan. Kamera versus galeri belum
  dibatasi sebagai kebijakan; capture hint browser tidak menjamin sumber kamera.
- Nama berkas dibuat server; nama file pengguna tidak dipakai. Berkas tidak masuk
  static assets/public URL. GET foto memerlukan Bearer milik teknisi penanggung
  jawab atau supervisor. UI mengambil blob dengan Authorization tanpa token URL.
- Foto tidak bisa dihapus/ditimpa melalui API. Snapshot pengajuan/review memuat
  metadata/checksum foto dan seluruh hasil. Snapshot lama tidak diubah saat revisi.
- Berkas disimpan pada volume permanen `hotel-maintenance_photos`, mount
  `/app/storage/photos`, bukan writable layer container. File mode 0600. Volume
  telah diuji tulis/baca lintas container sebagai user app non-root.
- Jika commit metadata gagal, file baru dibersihkan dan version transaksi rollback.
  Crash proses tepat sebelum commit dapat menyisakan orphan file; belum ada job
  rekonsiliasi/retensi otomatis. Jangan menghapus volume/file bukti secara manual.
- Pengajuan/approval memeriksa keberadaan foto; bila berkas bukti hilang, pulihkan
  dari backup yang cocok dengan database sebelum melanjutkan. Metadata saja tidak
  menggantikan bukti. Backup rutin harus mencakup **database dan volume foto**
  dari waktu yang konsisten. Salinan off-host/retensi otomatis belum dikonfigurasi.

## Kontrak API ringkas

- POST/GET `/hotel-visits`, GET `/hotel-visits/{id}`.
- POST `/{id}/check-in`, POST `/{id}/samples`, DELETE `/{id}/samples/{item_id}`.
- PUT `/{id}/devices/{item_id}/result`, PUT `/{id}/report`.
- POST `/{id}/devices/{item_id}/photos?expected_version=N`: body biner gambar,
  Content-Type image/jpeg, image/png atau image/webp; bukan multipart.
- GET `/hotel-visits/photos/{photo_id}`: berkas privat dengan Authorization.
- POST `/{id}/check-out`, `/{id}/resubmit`, `/{id}/review`; GET `/{id}/history`.
  Semua path relatif di atas berawalan `/hotel-visits`.

Pagination koleksi/history memakai offset/limit (default 50, maksimum 100).
Server memeriksa role/kepemilikan pada setiap akses, hubungan hotel/AP serta
status/version pada mutasi. Data kunjungan lama tidak diubah atau diisi otomatis;
0007 hanya menambah tabel dengan FK restriktif. Downgrade destruktif ditolak.

## Verifikasi dan batas tahap ini

33 tes backend lulus, 11 tes integrasi dilewati pada suite default tanpa URL uji.
10 tes PostgreSQL staging lulus, 3 unittest scaffold lulus. Chromium menuntaskan
alur master data → penugasan hotel → GPS → sampling AP → hasil per band → foto →
penolakan foto kurang → pengajuan → revisi → kirim ulang → approval pending.
Foto blob dimuat, empat snapshot ada, tidak ada pageerror, tampilan 390 px tidak
overflow dan sesi hilang saat reload. Browser juga diuji menggunakan image Docker
produksi dengan Python 3.12 dan dependency sebenarnya, pada database sementara.
Tes tambahan memastikan AP mati dilaporkan pending tanpa pengukuran rekaan.

Backup database nyata berhasil dipulihkan dan di-upgrade pada PostgreSQL terpisah;
fingerprint seluruh data lama sama sebelum/sesudah migrasi utama. Data uji hanya
di database/penyimpanan sementara, bukan produksi. Lihat DEPLOYMENT.md untuk
lokasi backup dan container aktif.

Wi-Fi analyzer native, speedtest otomatis, APK/offline, tanda tangan digital dan
PDF sesuai template **belum tersedia**. Nilai pengukuran sekarang merupakan input
manual; aplikasi belum dapat membuktikan HP tersambung ke AP tertentu atau
membaca CCQ radio backbone dari scan Wi-Fi HP. Pengembangan native membutuhkan
pengujian pada HP fisik, dan penggunaan lapangan memerlukan akses backend HTTPS.


## Pembaruan speedtest (0008)

Tombol Jalankan speedtest pada AP sekarang mengukur download/upload/ping/jitter
secara otomatis. Akses tunnel/lokal hanya diagnostik dan tidak mengubah bandwidth
AP. Origin HTTPS langsung yang terverifikasi serta deklarasi Wi-Fi diperlukan
untuk menerapkan hasil. Sinyal/channel tetap manual; native Android/PDF/tanda
tangan masih belum tersedia. SPEEDTEST.md menggantikan pernyataan speedtest belum
tersedia pada catatan tahap 0007 di atas. Hasil pekerjaan/foto tidak berubah.


## Revisi laporan utama (0009)

Form terkini memakai nama pelanggan otomatis dari site, profil bandwidth/ambang
sekali per site dan penilaian download+upload otomatis. TX/RX/CCQ tidak lagi tampil
pada form baru, ditambah hasil link test radio dan lima keterangan LAN/Wireless/
Hotspot yang wajib. Tidak ada ambang default atau data produksi yang diisi rekaan.
REPORT_FORM.md menjadi petunjuk terbaru untuk bagian laporan utama; bagian di
atas yang menggambarkan form lama merupakan riwayat tahap sebelumnya.
