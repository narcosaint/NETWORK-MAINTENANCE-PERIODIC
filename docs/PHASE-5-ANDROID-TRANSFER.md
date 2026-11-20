# Status setelah persetujuan — backend sudah aktif

18 November 2026: operator menyetujui aktivasi. Migration 0010–0012 sudah dipromosikan
ke chain Alembic dan diterapkan setelah backup/restore salinan terbukti menjaga
seluruh data lama. Source backend/Web serta gate field sampling, observasi dan
speedtest sudah aktif pada https://maintenance.inisaja.id. Tidak ada data dummy
produksi. Lihat [catatan rilis](DEPLOYMENT.md) untuk bukti dan backup. Radio/throughput HP
masih perlu diuji teknisi; completion V2 belum diaktifkan.

Rincian di bawah mencatat implementasi dan status sebelum aktivasi.

# Phase 5B — Android LibreSpeed dan binding Wi-Fi

18 November 2026. Source lokal; tidak menjalankan deployment, migration produksi,
atau perubahan Docker/network server. Melanjutkan [fondasi Phase 5A](PHASE-5-SESSION-SPEEDTESTS.md).

## Alur yang tersedia

Tombol Android menjalankan worker LibreSpeed yang dibundel dari source existing,
meminta tiket per sesi, mengukur download/upload/ping serta jitter jika tersedia,
lalu menyimpan hasil ke sesi titik aktif. Riwayat menampilkan timestamp, server,
status dan angka tersimpan. Setiap lokasi menggunakan run sendiri, termasuk jika
AP sama. Browser biasa tetap tidak dapat memulai pengukuran native.

Teknisi menyetujui penggunaan bandwidth sebelum mulai (kuota server maksimal
512 MiB download + 128 MiB upload). Durasi download/upload masing-masing 8 detik,
5 ping; angka nol dipertahankan dan nilai kosong tidak diubah menjadi nol.
Hasil harus melewati pemeriksaan transfer backend existing.

Plugin `HotelWifi` menyediakan beginSpeedtest/checkSpeedtest/endSpeedtest.
Begin memeriksa jaringan Wi-Fi aktif langsung tanpa VPN, BSSID serta band 2.4/5 GHz,
lalu memanggil bindProcessToNetwork dengan ID binding dan network handle.
Callback memantau kehilangan jaringan dan perubahan BSSID/frekuensi. Pemeriksaan
berkala juga memastikan binding dan jaringan aktif tetap sama. Binding berlaku
sementara untuk proses aplikasi: worker dihentikan sebelum binding dilepas.
Kehilangan jaringan tidak segera melepas binding agar transfer tidak beralih ke
seluler. Pembatalan, background, jaringan berubah atau pelepasan gagal membuang
angka hasil. Snapshot akhir dan ID/handle binding harus cocok saat finish.

Referensi: [Android ConnectivityManager.bindProcessToNetwork](https://developer.android.com/reference/android/net/ConnectivityManager#bindProcessToNetwork(android.net.Network)).
Permission tambahan CHANGE_NETWORK_STATE adalah normal permission untuk operasi
binding lokal aplikasi, tanpa mengubah konfigurasi Wi-Fi atau jaringan server.

## Tiket, retry dan kompatibilitas

Worker hanya memperoleh tiket transfer sementara, tanpa Bearer/login token.
Header tiket dibatasi ke origin yang dipilih dan endpoint ping/download/upload run
tersebut. API kontrol memakai CapacitorHttp existing. Middleware CORS hanya untuk
origin aplikasi `https://localhost`, path transfer dan tiket aktif yang dialokasikan
untuk binding Android. Preflight Authorization, origin lain, run asing, tiket habis,
dan endpoint API umum tidak mendapat izin. Tidak mengaktifkan CORS global.

Outbox IndexedDB terpisah per akun/origin/visit/titik membekukan UUID start sebelum
request dan hasil finish sebelum pengiriman. Tiket transfer tidak dipersist.
Respons start hilang: replay UUID lalu batalkan run lama beralasan, tanpa meneruskan
tiket/binding lama atau membuat pengukuran kedua. Respons finish hilang: kirim hasil
sama atau rekonsiliasi riwayat terminal setelah 409. Start yang ditolak definitif
menghapus antrean agar versi/pemetaan dapat diperbaiki. Gangguan transport tetap
menyimpan antrean. Retry dilakukan lewat tombol, bukan background transfer diam-diam.

Endpoint legacy, field Backbone FO/wireless dan LAN tetap dipertahankan. Metadata
binding berada dalam JSON context existing; tidak memerlukan migration tambahan
selain draft 0010–0012 yang belum diterapkan ke produksi.

## Aktivasi dan batas verifikasi

Butuh schema yang telah direview, SAMPLING_MASTER_ENABLED=true,
SAMPLING_SPEEDTEST_ENABLED=true, API HTTPS yang dapat dijangkau HP, serta
PUBLIC_SPEEDTEST_ORIGIN cocok dengan origin HTTPS pengujian. Gate server tetap
nonaktif secara default. Jangan memasukkan alamat loopback server sebagai origin HP.
APK debug bukan release dan belum dinyatakan siap operasional.

Snapshot/binding adalah laporan klien, bukan attestation radio server. Metadata tetap
radio_verified=false, sampling_eligible=false dan completion_accepted=false.
Kelengkapan sampling/submit V2 masih menunggu dokumentasi/foto dan PIC. Tidak ada
klaim throughput Wi-Fi lapangan dari fixture atau loopback.

Verifikasi lokal: 75 test backend lulus, 21 opt-in dilewati pada perintah default;
20 test PostgreSQL 18.6 terisolasi lulus. 35 test frontend lulus, mencakup worker, pembatalan,
binding hilang, nilai kosong/nol, pembatasan header tiket dan outbox lost response.
Build/typecheck/lint, kompilasi Java serta regresi browser Android
legacy dan Web → FastAPI → SQLite → Android diperiksa. Task unit test Gradle
lulus tetapi hanya berisi contoh bawaan, bukan pengujian binding Android.
Tes fisik HP (permission,
roaming, Wi-Fi putus/seluler aktif, background dan throughput nyata) masih diperlukan
setelah staging siap. Tidak ada database produksi yang dipakai dalam pengujian.

APK: `artifacts/android/hotel-maintenance-phase5-debug.apk` (debug signature
verified; worker/license/source metadata match repository). SHA-256:
`88a61369d4e8a9d5cae5dd339bbe4f1ee857f41c2809e6dcb7db937b728ad383`.
