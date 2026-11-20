# Network Test lapangan sederhana — 1.5.0

Instruksi operator menggantikan kuota 2/4: jumlah lantai dan area bebas sesuai
lokasi aktual. Setiap area tetap punya Wi-Fi dan speedtest sendiri. Tidak perlu
inventaris untuk menjadwalkan maintenance. Backend lama dan data produksi tetap
kompatibel; tidak ada migration atau pengubahan Docker/network.

## Akar kegagalan upload

Empat percobaan native terbaru pada produksi gagal dengan error batas volume;
server mencatat masing-masing upload tepat 134217728 byte (128 MiB), dengan
5 ping dan download yang telah diterima. Worker lama terus mengirim sampai
batas waktu sehingga melampaui kuota. Batas server tetap dipertahankan.

Worker baru mereservasi byte per request sebelum transfer. Saat budget habis,
tidak membuka stream lagi dan menyelesaikan fase setelah request aktif selesai.
Semua byte terukur dipertahankan (tidak dibuang sebagai warm-up setelah budget
terpakai). Delayed stream tidak boleh mulai setelah cleanup fase, termasuk jeda
antar-tes. APK memilih budget maksimal 64 MiB download / 32 MiB upload; server
hard cap tetap 512/128 MiB. Throughput tetap hasil LibreSpeed, bukan angka dummy.

Tes browser menggunakan worker vendored asli, origin https://localhost dan
FastAPI HTTPS dengan sertifikat lokal pada port disposable. Upload mencapai
tepat hard cap yang dikecilkan menjadi 16 MiB untuk QA, berhenti tanpa HTTP
quota error, lalu menyimpan hasil lengkap dan snapshot Wi-Fi. Radio dan binding
adalah fixture, bukan bukti pengukuran HP fisik. Tidak menyentuh produksi.

## Alur pengguna dan bukti

Satu halaman area: koneksi HP, pengujian, riwayat, scanner opsional, temuan dan
foto. Saat finish, snapshot koneksi asli dari start disimpan atomik bersama run
sebagai observasi area. Catatan lama dipertahankan; status gagal tetap memerlukan
alasan/tindakan. Foto opsional per area. Foto yang sudah dikirim tetap disertakan
di PDF, dengan kompresi untuk PDF; lokal yang belum dikirim tetap harus dikirim
atau dihapus dari draf sebelum tanda tangan.

Target snapshot lama tidak ditulis ulang, tetapi tidak memblokir submit atau
menambah denominator progress. Daftar hanya menampilkan lokasi nyata. Tidak ada
record sampling kosong otomatis. Area kosong dapat dibatalkan melalui event
append-only; baris, master dan audit tetap disimpan. Area yang sudah punya
observasi/percobaan/foto tidak dapat dibatalkan. Penambahan ulang nama area kosong
mengaktifkan kembali sesi yang sama. Floor tanpa area aktif disembunyikan.

Kartu Cakupan Sampling Kunjungan dihapus. Informasi pelanggan, FO, wireless dan
LAN dilipat. Tab Perangkat di detail hotel Web dihapus; data dan histori tetap
utuh. Logout Web/Android memerlukan konfirmasi; batal tidak memanggil logout.

PDF tetap mencantumkan backbone FO/wireless, LAN, setiap area, hasil/failed reason,
foto terkirim dan tanda tangan PIC. Tidak ada kuota atau kewajiban foto per area.

## Verifikasi dan aktivasi

92 backend pada image Python 3.12 lulus (29 opt-in dilewati pada suite biasa),
28 PostgreSQL terisolasi dan 42 frontend lulus. Pengujian tambahan setelah
optimasi pembacaan event juga lulus. Browser nyata: worker lintas-origin HTTPS,
alur PDF/PIC, logout batal/konfirmasi Web/Android, area/offline, kartu cakupan
yang dihapus, accordion laporan dan navigasi tanpa Perangkat lulus.

Backend aktif: `hotel-maintenance-api:field-simple-20261119T100010Z`. Backup konsisten database/foto:
`/root/backups/hotel-maintenance/field-simple-20261119T100010Z`. Restore dan QA alur API/PIC/PDF pada salinan
PostgreSQL lulus. Seluruh fingerprint data produksi identik. Tidak ada migration
atau data QA di produksi. Schema tetap 0013. Aset publik HTTPS cocok dengan
source rilis dan endpoint pembatalan area ada di OpenAPI.

APK: `artifacts/android/nusa-maintenance-1.5.0-debug.apk`, code7, signature upgrade tetap sama.
SHA-256: `4dd709dccc19f4e5ddef85c50e5f5ab557e3ded2d26c54a756479c2cdfd0e9a1`. Aset worker/brand/bundle telah diverifikasi di APK.
Alias https-debug diperbarui. Radio, binding Android dan jaringan HP fisik tetap
perlu uji lapangan; fixture browser tidak membuktikan pengukuran perangkat.
