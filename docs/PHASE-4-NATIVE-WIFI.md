# Phase 4 — Wi-Fi native Android

16 November 2026. Implementasi source lokal; tidak mengaktifkan gate produksi,
migration, deployment, Docker atau perubahan jaringan server.

## Implementasi

`HotelWifiPlugin.java` terdaftar di MainActivity dan diakses melalui Capacitor
`HotelWifi`. Izin lokasi presisi diminta hanya saat teknisi menekan tombol baca
atau scan. Manifest menambah ACCESS_WIFI_STATE dan CHANGE_WIFI_STATE untuk scan;
tidak ada perintah mengaktifkan/mematikan Wi-Fi, VPN, atau mengikat trafik aplikasi.

Connected Network memakai callback jaringan default. Android 12+ memakai flag
INCLUDE_LOCATION_INFO; versi lama memakai API kompatibel dengan minSdk 24.
Transport selain Wi-Fi langsung/VPN ditolak. SSID/BSSID, frekuensi, RSSI, link speed,
IP dan gateway berasal dari Android, terkait jaringan default yang sama. Placeholder
BSSID/SSID dan nilai sentinel menjadi null, bukan angka/identitas buatan.
Nama AP hanya muncul jika BSSID cocok persis dengan MAC AP snapshot titik. Belum
ada tabel BSSID multi-radio; AP lain tetap “AP Belum Teridentifikasi”.

Scanner menunggu SCAN_RESULTS_AVAILABLE_ACTION, memeriksa hasil startScan dan
EXTRA_RESULTS_UPDATED. Timeout/kegagalan memakai cache OS hanya jika tersedia,
dengan alasan serta label cached. Timestamp tiap jaringan dihitung dari timestamp
monotonik ScanResult, bukan dianggap waktu scan baru. Receiver/callback/timeout
dibersihkan saat selesai atau activity ditutup. Tidak ada polling background.

UI mempunyai band 2.4/5 GHz, jumlah jaringan, daftar RSSI/channel/frequency/BSSID,
waktu hasil, grafik dan estimasi kedekatan pusat kanal. Kurva memakai ilustrasi
20 MHz dari frekuensi/RSSI aktual; lebar kanal dan interferensi tidak diklaim terukur.
Perizinan ditolak, lokasi mati, scan dibatasi, radio tidak tersedia dan jalur
seluler/VPN ditampilkan sebagai unavailable. Browser tidak menghasilkan hasil radio.

## Persistence dan kompatibilitas

Capture hanya tersedia pada sesi titik V2 yang dapat diedit. Draf radio disimpan
di IndexedDB akun/server/visit/sesi yang sama dengan catatan. Tombol simpan
mengirim wifi_connection/wifi_scan melalui outbox UUID existing. Capture baru
tidak dihapus ketika acknowledgment hanya mencakup kiriman lama. Riwayat server
tetap ditampilkan dengan waktu pengukuran; pembacaan ulang harus eksplisit.

Schema JSON observasi menambah metadata band, alasan cache dan timestamp/cached
per jaringan secara opsional; klien lama tetap diterima. Batch tidak boleh mengaku
fresh bila ada network cached, dan frekuensi harus cocok dengan band yang dideklarasikan.
Tidak ada migration baru di tahap ini. Draft 0010/0011 tetap di luar head aktif.

Source android_native tetap deklarasi klien. Backend tetap mengembalikan
radio_verified=false dan completion_accepted=false. Native reading belum membuktikan
binding trafik LibreSpeed, dan tidak membuat sampling selesai. Backbone FO,
Wireless Backbone dan Local Area Network dipertahankan.

## Lingkungan pengujian

Runtime PostgreSQL 18.6 portabel dipasang hanya di /tmp, wheel diverifikasi SHA256.
`tests/run_isolated_postgres.py` membuat database `_test` baru sebagai nobody,
Unix socket privat tanpa listener TCP. Suite memakai schema acak, bukan produksi;
server dihentikan dan direktori sementara dibersihkan setelah pengujian.
Head aktif tetap 0009; draft diterapkan hanya dalam schema uji.

JDK 21 dan Android SDK 36 disiapkan di /tmp dengan checksum unduhan. Cache Gradle
serta user directory Android juga memakai /tmp. Build tidak membutuhkan perubahan
Docker atau instalasi paket sistem. Emulator dan perangkat fisik belum tersedia.

Test frontend memeriksa unavailable di luar Android, penolakan placeholder/seluler,
nilai nol, SSID tersembunyi, frekuensi/channel, provenance cache dan draf radio yang
lebih baru dari acknowledgment. Backend memeriksa metadata scan pada schema nyata
dan SQLite. Browser menguji regresi Web/Android dan persistence; fixture bukan
bukti hasil radio perangkat.

## Uji HP yang masih wajib

1. Instal APK debug pada perangkat uji, login ke origin HTTPS staging yang disetujui.
2. Pada titik V2, coba izin lokasi ditolak/approximate/presisi, lokasi mati dan Wi-Fi mati.
3. Baca jaringan aktif; cocokkan SSID/BSSID, RSSI, frekuensi/IP/gateway dengan perangkat.
4. Pindai kedua band; ulang cepat untuk menguji pembatasan OS dan penanda cache.
5. Beralih ke seluler/VPN dan ganti jaringan saat membaca: jangan menerima hasil lama
   sebagai koneksi baru. Capture bukan bukti jalur trafik speedtest.
6. Simpan capture saat offline, pindah halaman/restart sesuai sesi login, lalu kirim
   kembali dan pastikan UUID tidak menggandakan histori serta tiap titik terpisah.
7. Periksa lifecycle activity, timeout, OEM berbeda dan Android 24/29/31/33/36.

Native behavior belum dinyatakan lulus sebelum uji perangkat. Tahap berikutnya
adalah LibreSpeed per sesi beserta validasi/binding koneksi, lalu foto dan PIC.

## Hasil verifikasi lokal

- Backend default: 69 passed, 20 skipped (suite PostgreSQL opt-in tidak aktif pada
  perintah default; dijalankan terpisah di bawah).
- PostgreSQL 18.6 nyata terisolasi: 19 passed, termasuk DDL draft, compatibility,
  aktivasi coverage bersamaan, observasi/replay dan metadata radio JSONB.
- Frontend: 23 test passed, TypeScript/build/lint passed.
- Java plugin: compileDebugJavaWithJavac passed. testDebugUnitTest passed untuk
  satu test baseline existing; ini bukan pengujian radio atau callback Android.
- Browser: regresi Phase 3 dan alur Web → FastAPI → SQLite → Android passed,
  termasuk arsip grafik/cache Wi-Fi dengan fixture QA serta retry respons hilang.
- cap sync dan assembleDebug passed. APK debug lokal:
  `artifacts/android/hotel-maintenance-phase4-debug.apk` (8,836,187 bytes).
  SHA256: `1cd68d5b5c8e10242825754c934b9253548a3deb97db07990bfe491fe159b8b6`.
- Artifact diperiksa: plugin HotelWifi terpaket, frontend terbaru, tidak ada
  server.url, backup/cleartext mati dan scheme WebView HTTPS. Bukan APK release.

Build pertama gagal karena cap sync dijalankan bersamaan dengan Gradle sehingga
direktori plugin generated dibuat ulang. Build diulang secara berurutan dan lulus.
SDK/Gradle memberi warning metadata/flatDir dan API scan deprecated yang masih
dipakai sesuai API Android; tidak mengubah versi dependency/config server.

Referensi primer:
[Android Wi-Fi scanning](https://developer.android.com/develop/connectivity/wifi/wifi-scan),
[NetworkCallback](https://developer.android.com/reference/android/net/ConnectivityManager.NetworkCallback),
[ScanResult timestamp](https://developer.android.com/reference/android/net/wifi/ScanResult#timestamp),
[Capacitor Android plugins](https://capacitorjs.com/docs/plugins/android),
[custom plugin registration](https://capacitorjs.com/docs/android/custom-code).
