# Sampling: audit Phase A dan implementasi Phase B

## Hasil audit (12 November 2026)

Frontend aktif adalah HTML/CSS/JavaScript biasa di `backend/app/web`, dilayani FastAPI pada origin yang sama. Tidak ada package.json, React, Capacitor, Gradle atau plugin Kotlin; folder `mobile/` kosong. UI Android native dalam spesifikasi merupakan target berikutnya, bukan stack yang sudah terpasang. Tidak ada integrasi Google Sheets/Drive yang ditemukan.

PostgreSQL/Alembic memiliki migration sampai `0009_site_report_profile`. Audit ini membaca source; tidak membaca data pelanggan atau credential dan tidak menjalankan migration.

| Kebutuhan | Existing | Gap / keputusan fase ini |
| --- | --- | --- |
| Hotel dan sesi kunjungan | hotels, hotel_visits; GET /hotel-visits/{id} | Dipakai sebagai konteks sampling |
| Lantai dan titik | hotel_visit_devices.floor/point; POST samples | Lantai belum entitas terpisah; konfigurasi target per hotel disimpan lokal |
| Hasil per AP | PUT devices/{item}/result; band_24/band_5 | Hasil existing ditampilkan dengan label sumber manual; tidak diubah otomatis |
| Speedtest | network_speedtests, worker LibreSpeed, start/finish/apply | Gunakan alur existing, termasuk batas diagnostik tunnel dan konfirmasi jaringan |
| Foto | device_photos, GET authenticated, POST foto | Foto existing ditampilkan; kategori/caption/offline queue belum didukung API |
| Connected network | Belum ada | Kartu unavailable, tidak menyimpulkan koneksi aktif dari hasil historis |
| Scan radio/channel overlap | Belum ada | Interface unavailable; tidak mengarang daftar/grafik/scan |
| Catatan terstruktur | notes satu teks | Catatan, temuan, tindakan, rekomendasi dan status disimpan sebagai draf lokal |
| Android permission/kamera | Belum ada native host | Browser file/camera capture sebagai fallback; Kotlin/Capacitor fase berikutnya |
| Sinkronisasi Sheets/Drive | Belum ada | Tidak dibuat dalam Phase B |

## Batas perubahan

Phase A–B saja. Tidak mengubah backend, schema, API, Docker/port/network, validasi atau fungsi simpan laporan existing. Tidak menjalankan deployment, migration, atau menghapus container/volume. Isi Laporan Utama, Backbone dan LAN dipertahankan. Tombol “Dashboard sampling” ditambahkan ke kunjungan sebagai pintu masuk modul baru.

Tidak dibuat migration. Kandidat additive fase berikut: hotel_floors, sampling_points, sampling_sessions, connection_measurements, scan_results, sampling_photos metadata, technician_notes. Hubungkan ke hotel/visit/device/user existing; simpan waktu/sumber/izin/transport pengukuran dan status sinkronisasi. Rancang FK, ownership, version checks, retention/kuota dan kontrak offline-idempotency sebelum membuat migration. Tidak mengubah constraint band speedtest existing untuk mengklaim dukungan 6 GHz.

## Penyimpanan Phase B

IndexedDB `hotel-sampling-drafts-v1` menyimpan konfigurasi lantai per user+hotel dan draf per user+visit+point. Foto disimpan sebagai Blob bersama metadata kategori, timestamp, point ID dan caption. Token/password tidak disimpan. Status lokal bukan status resmi laporan; draf tidak ikut checkout/review dan belum diunggah otomatis. Kesalahan storage/kuota ditampilkan; tidak memberi klaim tersimpan bila transaksi gagal. Data lokal tetap ada setelah logout, hanya dapat ditampilkan UI pada akun dan kunjungan yang sesuai. Perangkat bersama perlu kebijakan keamanan/retensi pada fase native. Ini cache draf aplikasi, bukan mode PWA offline penuh: membuka ulang aplikasi saat server tidak dapat diakses belum didukung.

Lantai baru mempunyai target 4 titik placeholder, dapat diatur 1–100. Tidak membuat AP atau titik produksi. Titik yang tersimpan di server diutamakan; target tidak membatasi jumlah AP existing. Label placeholder meminta teknisi menentukan lokasi, bukan nama kamar contoh. Konfigurasi lokal tidak disinkronkan antarperangkat. Pengurangan target tidak boleh menyembunyikan titik yang sudah memiliki draf.

## Pengukuran dan integrasi berikutnya

`SamplingServices.connection()` / `scan()` adalah batas service native yang mengembalikan unavailable pada fase ini. Tidak meminta izin lokasi browser seolah-olah dapat melakukan Wi-Fi scan. Kartu menjelaskan kebutuhan aplikasi Android dan izin Nearby Wi-Fi/lokasi sesuai versi; status denied harus ditangani oleh adapter native fase C.

Speedtest tetap memakai dialog/worker/API nyata existing. Riwayat menampilkan konteks, download/upload/ping/jitter, server, waktu dan durasi bila ada. “Belum diuji” untuk data kosong. Data manual band tidak digunakan untuk menyimpulkan jaringan aktif. Foto server dimuat dengan Authorization di memory; URL Blob dibersihkan saat meninggalkan halaman/logout. Foto lokal dapat dilihat penuh dan dihapus setelah konfirmasi; tidak ada delete foto server baru.

## APK

Belum ada APK atau konfigurasi build Android pada Phase B. Belum ada perintah build APK yang valid untuk repo ini. Fase C perlu scaffold mobile React/Capacitor, Android SDK/JDK/Gradle, adapter auth/API, plugin WifiManager + permission/runtime network binding, kamera/filesystem, sinkronisasi, lalu `npx cap sync android` dan build Gradle setelah project Android tersedia. WebView wrapper saja tidak menyediakan pembacaan radio Wi-Fi. Uji perangkat nyata wajib untuk scan throttling, permission ditolak, pergantian Wi-Fi/seluler dan kamera.

## File Phase A–B

Baru:
- `backend/app/web/sampling-service.js`: service boundary native dan IndexedDB; formatter hasil existing serta pengelompokan lantai/titik.
- `backend/app/web/sampling.js`: dashboard, lantai, detail titik, tab, draf, foto dan navigasi.
- `backend/app/web/sampling.css`: gaya navy/blue/teal yang dibatasi ke modul sampling.
- `tests/browser/sampling_ui.py`: pengujian UI dan storage pada server statis lokal dengan fixture eksplisit; tidak memakai database.
- `docs/SAMPLING_AUDIT.md`: laporan audit, gap, penggunaan, batasan dan rencana APK.

Diubah:
- `backend/app/web/index.html`: memuat asset sampling.
- `backend/app/web/app.js`: membersihkan state/URL sampling ketika logout atau navigasi utama.
- `backend/app/web/hotel.js`: satu tombol Dashboard sampling; fungsi form utama/perangkat/Backbone/LAN identik dengan source sebelum tugas (diverifikasi SHA256).
- `backend/tests/test_web.py`: pemeriksaan asset baru dan header keamanan existing.

## Cara mencoba setelah source ini disetujui untuk rilis

Buka kunjungan hotel → Dashboard sampling → pilih lantai → Detail titik sampling. Teknisi yang memiliki kunjungan in-progress/revision dapat menambah lantai, mengatur target dan menyimpan draf. Supervisor/akun lain/kunjungan terkunci hanya dapat membaca. AP dan hasil resmi tetap dikelola alur existing. Titik lokal belum mempunyai AP; gunakan Pilih AP sampling pada laporan untuk menambahkan AP inventaris sebelum melakukan speedtest.

## Verifikasi

- ` .venv/bin/pytest -q`: 47 passed, 15 skipped (tes integrasi PostgreSQL opsional tidak diaktifkan).
- ` .venv/bin/pytest -q backend/tests/test_web.py`: 1 passed setelah asset baru ditambahkan ke pemeriksaan.
- ` .venv/bin/python -m unittest discover -s tests -v`: 3 passed.
- ` .venv/bin/python tests/browser/sampling_ui.py`: Chromium/Playwright; formatter data kosong/nol, native unavailable, layout 360/390/768/1440px, tab, draf lintas tab/reload, offline, Blob foto, caption/kategori, preview, konfirmasi hapus, kegagalan storage, target lantai, isolasi akun, error/retry, dan form utama. Browser memakai runtime library/font lokal di /tmp pada server ini. Screenshot: `artifacts/sampling/` (diabaikan Git).
- Tidak ada package.json, TypeScript, linter atau bundler frontend; asset buildless diparse/dijalankan Chromium dan diuji melalui ASGI asset tests. Tidak mengklaim lint/typecheck/npm build atau build APK telah dilakukan.
- Tes UI memakai fixture khusus pengujian, tidak memasukkan data contoh ke produksi. Tidak ada API write pada tes sampling; tidak menjalankan migration (termasuk database sementara), tidak membuat/menghapus container atau volume.
- Permission Wi-Fi ditolak, scan throttling, binding Wi-Fi/seluler, kamera native dan sinkronisasi harus diuji pada perangkat Android setelah Phase C. Fase ini hanya menguji UI unavailable, bukan plugin yang belum ada.
- Asset produksi belum diganti; GET /health existing tetap ok. Tidak ada deployment atau perubahan image Docker.


## Release Phase B — 13 November 2026

Sudah dipasang pada container `hotel-maintenance-web-sampling`, image
`hotel-maintenance-api:sampling-20261113`, project Compose dengan nama container
yang sama dan file `compose.sampling.yaml`. Catatan “belum deployment” di atas
merupakan hasil audit sebelum rilis. Container sebelumnya
`hotel-maintenance-web-report-form` disimpan stopped dengan restart policy no.

Backup terbaru: `/root/backups/hotel-maintenance/20261113T025256Z-sampling-release/`.
Berisi database.dump, photos.tar.gz, salinan aplikasi sebelumnya dan deployment.json
beserta checksum arsip. Backup dilakukan saat API lama berhenti agar database dan
foto konsisten. Tidak ada migration; fingerprint seluruh tabel database sebelum dan
sesudah deployment identik. Backend source identik dengan aplikasi sebelumnya;
perubahan hanya asset frontend. Network, port, database dan volume foto dipertahankan.

Verifikasi rilis: 47 passed, 15 skipped; browser sampling lulus terhadap server
statis dan terhadap asset aplikasi aktif di localhost:8000. Browser menggunakan
fixture API yang dicegat, tanpa menulis data produksi. Asset aktif cocok byte per
byte dengan source; health API/database ok dan container healthy. Pengujian browser
mencakup 360/390/768/1440px, navigasi/tab, catatan/foto IndexedDB, offline, isolasi
akun dan form utama. Batas Phase B/native/sinkronisasi tetap berlaku.

Pemulihan aplikasi (tanpa restore database): stop container sampling,
aktifkan restart unless-stopped dan start container report-form sebelumnya.
Jangan menjalankan kedua API bersamaan karena port sama. Tidak perlu downgrade
schema karena rilis ini tidak mengubah database.
