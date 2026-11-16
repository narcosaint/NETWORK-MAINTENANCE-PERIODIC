# Speedtest otomatis pada AP sampling

Engine browser LibreSpeed telah diintegrasikan dengan endpoint transfer FastAPI.
Tombol **Jalankan speedtest** muncul pada kartu AP sampling untuk teknisi pemilik
kunjungan yang sedang in_progress/revision_requested. Download, upload, ping dan
jitter dihitung oleh worker dari transfer HTTP nyata; bukan angka dari server
atau isian manual. Ini estimasi jalur perangkat ke server aplikasi, bukan jaminan
kapasitas radio AP atau seluruh koneksi internet. Sinyal/channel tetap terpisah.

## Cara memakai

1. Buka Kunjungan hotel sebagai teknisi → buka AP sampling → Jalankan speedtest.
2. Pilih band yang benar-benar dipakai dan jenis koneksi: Wi-Fi hotel, seluler,
   Ethernet atau tidak diketahui. Untuk Wi-Fi hotel, konfirmasi bahwa perangkat
   sudah tersambung ke AP/band tersebut. SSID/BSSID deklarasi boleh dicatat.
3. Mulai pengukuran dan tunggu hasil. Pengukuran sekitar 20–30 detik dan dapat
   dibatalkan. Batas volume: 512 MiB alokasi download + 128 MiB upload diterima.
   Pengujian menggunakan kapasitas jaringan selama berjalan; lakukan pada waktu
   yang sesuai operasional hotel. Melebihi batas membuat hasil gagal, bukan angka
   yang dianggap valid. Fast connection dapat mencapai batas sebelum waktu habis.
4. Hasil akhir dan konteks tersimpan pada AP/kunjungan/band yang dipilih. Transfer
   gagal, tidak lengkap, kedaluwarsa, berubah koneksi terdeteksi atau dibatalkan
   tidak menghasilkan nilai pengukuran tersimpan. UI tidak mengubahnya menjadi 0.
5. Hasil yang memenuhi syarat otomatis memasukkan **download Mbps** ke field
   bandwidth AP; upload/ping/jitter tetap tersimpan di record lengkap. Sinyal dan
   channel yang sudah dicatat tidak ditimpa. Konflik version tidak menimpa data:
   hasil tetap ada dalam riwayat, dapat diterapkan setelah memuat ulang jika izin
   dan status kunjungan masih sesuai.

## Dua konteks akses

**Diagnostik tunnel/lokal (yang aktif saat ini):** aplikasi masih diakses melalui
localhost/PuTTY dan belum mempunyai origin HTTPS publik yang dikonfigurasi.
Speedtest tetap berjalan otomatis, tetapi ikut mengukur jalur tunnel/lokal.
Angkanya disimpan dengan label diagnostik dan **ditolak server untuk diterapkan
sebagai bandwidth AP lapangan**. Menutup modal tidak mengubah keputusan tersebut.

**HTTPS langsung:** setelah domain/TLS/reverse proxy telah disiapkan dan diuji,
operator dapat mengatur `PUBLIC_SPEEDTEST_ORIGIN=https://<domain>` tanpa path.
Server hanya menandai origin terkonfigurasi sebagai direct_https jika Origin,
Host dan scheme HTTPS request cocok. Proxy perlu meneruskan Host dan protokol
asli dengan konfigurasi trusted proxy yang terbatas. Matikan kompresi/buffering
pada rute transfer; beri waktu/ukuran unggahan yang cukup untuk pengujian.
Jangan hanya mengisi env untuk menganggap deployment HTTPS sudah benar.

Penerapan hasil juga mensyaratkan test completed, jaringan dinyatakan hotel_wifi
serta konfirmasi teknisi. Hasil seluler/Ethernet/unknown/diagnostik tidak dapat
diterapkan sebagai bandwidth AP. Origin HTTPS bukan attestation jalur jaringan:
VPN/tunnel lanjutan tidak selalu dapat dideteksi browser. Pengujian lapangan harus
memakai jalur langsung yang sudah diverifikasi operator.

Browser biasanya tidak menyediakan SSID/BSSID, band atau jenis koneksi yang
terpercaya. Network Information API dipakai hanya bila type aktual tersedia;
effectiveType seperti "4g" **tidak** dianggap bukti jaringan seluler. Kontradiksi
jenis koneksi yang teramati dengan klaim Wi-Fi ditolak; identitas AP/band tetap
berdasarkan konfirmasi teknisi dan ditandai `radio_verified: false`.
Pembacaan radio otomatis dan verifikasi koneksi lebih baik memerlukan modul
Android dan uji HP fisik. APK/analyzer native belum dibuat pada tahap ini.

## Penyimpanan dan pembatasan

- Tabel `network_speedtests` (migration 0008) menyimpan pemilik, AP/band, konteks,
  status/waktu, metrik akhir atau alasan gagal. Tidak ada seed/backfill. Alur dan
  foto lama tetap dipertahankan. Hasil akhir tidak memiliki endpoint edit/delete.
- Angka speedtest berasal dari browser, disimpan sebagai browser_reported, bukan
  attestation hardware. Server memeriksa sesi transfer dan aktivitas download,
  upload serta minimal tiga ping sebelum menerima status completed. Counter
  download server adalah budget yang direservasi untuk response 4 MiB, bukan
  bukti byte yang benar-benar diterima browser. Counter upload adalah byte
  diterima; semuanya disimpan sebagai konteks dengan nama yang sesuai.
- Hanya teknisi yang ditugaskan dapat memulai/mengakhiri/menerapkan hasil.
  Supervisor dapat meninjau. Pengukuran dimulai hanya pada kunjungan editable,
  AP yang benar, expected_version yang sesuai. Saat approved hasil tidak dapat
  diterapkan lagi. Snapshot pengajuan/review membawa konteks dan metrik terkait.
- Bukti otomatis dipertahankan saat hasil RF disimpan jika nilai bandwidth tidak
  berubah. Penggantian bandwidth secara manual melepas label otomatis untuk band
  itu, tetapi record test asli tetap tersimpan. Klien tidak dapat menyuntikkan
  metadata automatic_speedtests melalui endpoint hasil manual.
- Tiket transfer acak hanya 180 detik, dikirim lewat header X-Speedtest-Token pada
  origin/run path yang tepat. Bukan token login; tidak masuk URL, DB, riwayat,
  localStorage atau sessionStorage. Run ID di URL bukan credential. Pengakhiran
  menghapus tiket, transfer selanjutnya ditolak. Telemetry/lookup IP/ISP eksternal
  LibreSpeed dimatikan.
- Maksimal dua test aktif per proses dan satu per teknisi. Payload upload per
  request maksimal 16 MiB, waktu satu upload 30 detik; server memberlakukan budget.
  Download respons 4 MiB, data acak tanpa cache/kompresi. API utama tidak menerima
  proxy URL/file arbitrary untuk pengukuran.
- Worker/API saat ini satu proses. Tiket/progress berada di memori; restart
  memutus test aktif, bukan mengarang hasil. Scaling multi-worker/replica perlu
  shared state atau routing yang sesuai sebelum diaktifkan.

## Kontrak

- POST /hotel-visits/{id}/devices/{item}/speedtests: expected_version, band,
  network, wifi_confirmed, observed_type, SSID/BSSID deklarasi opsional.
- GET /network-speedtests/transfer/{run}/ping dan /download serta POST /upload:
  hanya tiket khusus pada header, tanpa akses umum anonim.
- POST /network-speedtests/{run}/finish: status completed/failed/aborted dan metrik
  lengkap hanya untuk completed. Pengakhiran bersamaan hanya satu yang sukses.
- GET /network-speedtests/{run}: akses reviewer/pemilik tugas.
- POST /hotel-visits/{id}/devices/{item}/speedtests/{run}/apply: expected_version;
  server memeriksa konteks, hubungan run/AP, status dan pemilik.

## Verifikasi

37 tes backend lulus; 13 integrasi dilewati pada suite default tanpa URL staging.
12 tes PostgreSQL staging lulus, termasuk dua finish bersamaan yang menghasilkan
200/409. Tiga tes scaffold lulus. Chromium melakukan transfer sungguhan melalui
worker, dengan shaping koneksi hanya pada browser uji terpisah; angka yang
muncul bukan angka produksi/hotel. Alur diuji dari data master, sampling dan
speedtest hingga foto/revisi/approval. Diagnostik tidak menimpa bandwidth manual,
pembatalan tidak menyimpan metrik, dan token sesi tidak dipersistenkan browser.
Jalur penerapan origin HTTPS diuji melalui request integrasi dan PostgreSQL,
bukan pengujian domain/TLS publik yang sudah live. Domain masih dibutuhkan.

Vendor source: upstream https://github.com/librespeed/speedtest,
commit 06524abd22e4581fb38a32393b80f37beec05f34. Worker LGPL-3.0 disertakan dengan
LICENSE dan SOURCE.json di assets/librespeed. Modifikasi: whitelist setting tiket,
header hanya untuk origin/run yang tepat, dan error HTTP download menghentikan
stream. Source asli dan checksum upstream dicatat; tidak memakai UI WiFiman.
