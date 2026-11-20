# Phase 5A — API speedtest per sesi dan pencatatan gagal uji

18 November 2026. Implementasi source lokal. Tidak ada migration produksi,
deployment, perubahan Docker/network atau APK baru yang dinyatakan siap lapangan.

## Implementasi

Mesin transfer LibreSpeed existing digunakan kembali melalui helper alokasi dan
commit run. Endpoint legacy, tabel network_speedtests dan hasil AP dipertahankan.
Tambahan tabel sampling_speedtest_attempts menghubungkan tepat satu run ke satu
sesi fisik; UNIQUE(run_id) melarang run dibagi ke beberapa titik. Dua lokasi pada
AP sama tetap menghasilkan dua percobaan/run berbeda. Percobaan hanya menyimpan
referensi dan request replay, bukan sumber metrik kedua.

- GET/POST `/hotel-visits/{visit}/sampling-sessions/{session}/speedtests`.
- POST `.../speedtests/failures`: UUID, versi visit/sesi, alasan nonblank wajib.
  Tanpa run atau metrik; alasan tersimpan sebagai temuan gagal uji per percobaan.
- POST `.../speedtests/{attempt}/finish`: result dan snapshot koneksi akhir.
  Completed membutuhkan metrik aktual serta transfer server yang benar-benar
  teramati. Jitter boleh null khusus kontrak sesi; endpoint legacy tetap kompatibel.
- Start memerlukan snapshot Wi-Fi Android dengan BSSID/frekuensi. AP harus satu
  hotel, jenis AP dan cocok dengan MAC snapshot jika tersedia. AP belum dikenali
  tidak dibuat fiktif: start ditolak dengan arahan pencatatan gagal beralasan.
- AP visit dibuat dari inventaris aktual jika belum ada, dalam transaksi yang sama
  dengan pembuatan run dan relasi sesi; hasil pemeriksaan legacy tidak diisi otomatis.
- BSSID/frekuensi akhir berbeda atau snapshot akhir hilang menghasilkan failed
  tanpa angka, sekalipun client meminta completed. Transfer tidak lengkap,
  quota, timeout atau live ticket hilang juga gagal melalui validator mesin existing.
- Run sesi tidak bisa di-apply ke hasil AP legacy atau di-finish lewat endpoint
  legacy yang tidak memerlukan snapshot akhir. Ownership dan scope visit/session
  diperiksa server; hanya teknisi pemilik yang bisa mutasi, supervisor bisa membaca.
- Mutasi start/failure/finish mengunci visit dan menaikkan versi visit/sesi. Start
  dan failure memakai UUID idempotent; payload berbeda pada UUID sama memberi 409.
  Replay start tidak mengeluarkan kembali transfer token. Jika respons start hilang,
  baca riwayat, batalkan run lama dengan alasan atau tunggu expiry sebelum start baru.
- Transfer token hanya ada dalam respons start, tidak disimpan di DB/history.
  Public API list berpaginasi (maksimal 100). Riwayat masuk ke detail cakupan dan
  snapshot audit existing. Gate mati tidak menyembunyikan histori tersimpan.

Android menampilkan riwayat tiap sesi dan form alasan gagal uji. Alasan dan versi
dasar draf disimpan lokal; outbox membekukan UUID/payload sebelum request. Retry
setelah kehilangan respons tidak membuat percobaan ganda. Setelah 409 pengguna
memuat ulang serta meninjau riwayat sebelum mengirim pengganti dengan UUID baru.
Foto/catatan lain tetap dipertahankan.

## Batas pada tahap 5A (historis)

Integrasi berikutnya tersedia pada [Phase 5B](PHASE-5-ANDROID-TRANSFER.md).
Paragraf berikut mencatat kondisi sebelum tahap tersebut.

Tombol Mulai Speedtest Android masih nonaktif. Integrasi worker/native transport
dan binding/validasi trafik Wi-Fi belum dibuat, sehingga tidak ada klaim aplikasi
bisa melakukan speedtest lapangan dari APK. Tidak menambah CORS atau membuka origin
server secara diam-diam. HTTPS staging tetap perlu disiapkan terpisah sebelum uji HP.

Snapshot native adalah laporan klien, bukan attestation. Walaupun satu run selesai
mengukur transfer, sampling_eligible=false, radio_verified=false dan
completion_accepted=false. Completion visit tetap diblokir oleh guard V2 sampai
bukti per sesi, foto dan PIC terintegrasi. API ini tidak memenuhi seluruh Phase 5.
Temuan gagal uji tersimpan pada attempt; lifecycle maintenance_findings terstruktur
masih bagian dokumentasi berikutnya.

## Draft schema dan aktivasi

Draft `docs/migrations/0012_sampling_speedtest_attempts.py` berada di luar head aktif
0009, parent draft 0011. Satu tabel baru: UUID PK, session/run/actor FK RESTRICT,
timestamp server, request JSONB, alasan gagal nullable. CHECK memastikan ada run
atau alasan gagal, tidak keduanya; UNIQUE run_id serta indeks FK session/actor.
Tidak mengubah tabel lama, backfill atau seed. Downgrade penghapus histori ditolak.
Review SQL/lock, backup/restore dan staging tetap diperlukan sebelum penerapan.

Default nonaktif: memerlukan SAMPLING_MASTER_ENABLED=true dan
SAMPLING_SPEEDTEST_ENABLED=true sesudah schema terpasang. Metadata gate tersedia
dalam capabilities dan cakupan. Tidak ada environment server yang diubah.

## Verifikasi

Test backend mencakup dua titik satu AP, run tidak dibagi, scope/role, replay UUID,
versi stale, gagal beralasan, perubahan BSSID, transfer tidak lengkap, nullable jitter,
blok apply/finish legacy, serta kompatibilitas speedtest existing. SQL draft
dikompilasi offline tanpa mengubah head. PostgreSQL opt-in menjalankan alur yang
sama pada database sementara Unix socket, bukan produksi.

Test Android memeriksa antrean gagal uji/retry UUID, tanpa metrik palsu. Browser
melakukan simpan alasan melalui FastAPI dan SQLite terisolasi serta memastikan
riwayat muncul pada sesi yang benar. Ini tidak membuktikan speedtest HP nyata.

Hasil lokal: 73 test backend lulus (21 opt-in dilewati pada perintah default),
20 test PostgreSQL 18.6 terisolasi lulus, 24 test frontend serta build/lint lulus.
Tidak ada test radio HP atau throughput lapangan yang diklaim dari fixture API.
