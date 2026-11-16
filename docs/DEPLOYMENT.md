# Deployment aktif — 13 November 2026

Backend dan UI web terbaru terpasang hingga revision `0009_site_report_profile`. Container
API/web aktif: `hotel-maintenance-web-sampling`; database tetap `hotel-maintenance-db-1` pada
volume yang sama. API lama `hotel-maintenance-api-1` dipertahankan dalam keadaan
stopped dengan restart policy `no`, agar tidak mengambil port setelah reboot.
Container database dan konfigurasi SSH/firewall tidak diubah.

API/web dikelola oleh project Compose `hotel-maintenance-web-sampling`, file
`compose.sampling.yaml`, memakai network internal/API yang sudah ada. PostgreSQL
hanya di network internal, tanpa published port; API bind `127.0.0.1:8000`.
Jangan menjalankan API dari compose.yaml lama bersamaan: port tersebut sudah
digunakan release aktif. Jangan gunakan `down -v` atau reset database.

Pemeriksaan dari direktori proyek:

```bash
docker --host unix:///var/run/docker.sock compose -p hotel-maintenance-web-sampling -f compose.sampling.yaml ps
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/health/db
```

## Backup dan verifikasi

Backup custom-format PostgreSQL tersimpan di:
`/root/backups/hotel-maintenance/20261112T023703Z/database.dump`.
Direktori hanya untuk root; file backup mode 0600. File `deployment.json` di
direktori sama mencatat checksum SHA-256 dan hasil penerapan. Backup berada di
luar source/build context; salinan off-host terkelola belum dibuat.

`previous-api-rootfs.tar` di direktori yang sama menyimpan filesystem API lama
tanpa environment container. Image pemulihan:
`hotel-maintenance-api:before-20261112T023703Z`. Container API lama juga tetap ada.
Image pemulihan merupakan import filesystem dengan CMD/WORKDIR/USER/ENV runtime
dasar yang dipulihkan; belum diuji start sebagai image terpisah.

Backup dipulihkan pada PostgreSQL sementara dengan tmpfs dan jaringan internal
terpisah, kemudian migrasi 0001 → 0005 berhasil dijalankan. Fingerprint seluruh
row hotel/perangkat tetap identik pada database restore dan database utama.
Container/network uji sementara telah dibersihkan. Tidak ada seed data produksi.
Enam tes staging PostgreSQL sebelumnya lulus, mencakup workflow dan konkurensi.

Setelah penerapan, API/database healthy; endpoint baru tersedia di OpenAPI,
akses anonim ditolak dan login salah menghasilkan 401. Akun supervisor pertama kemudian dibuat oleh operator dan sudah terverifikasi aktif.

## Supervisor pertama

Operator menjalankan perintah interaktif berikut dan memasukkan identitas nyata
serta password unik 12–128 karakter. Password tidak ditampilkan saat diketik.
Jangan kirim password melalui chat atau command-line argument.

```bash
docker --host unix:///var/run/docker.sock exec -it hotel-maintenance-web-report-form python -m app.bootstrap
```

Bootstrap ditolak jika sudah ada user. Setelah akun dibuat, periksa login dan
akses supervisor melalui klien lokal; dokumentasi API di
`http://127.0.0.1:8000/docs`. Pengguna berikutnya dibuat melalui API supervisor.

## Pemulihan dan perubahan berikutnya

Tidak ada downgrade otomatis: riwayat/bukti tidak boleh dihapus. Jika API baru
bermasalah, hentikan hanya API release, periksa log dan gunakan perbaikan maju
atau prosedur pemulihan yang ditinjau. Jangan menimpa database utama dari backup
secara otomatis karena perubahan setelah waktu backup dapat hilang. Container
API lama menggunakan schema lama dan bukan rollback yang sudah diverifikasi
untuk schema 0005. Simpan backup, image dan container lama sampai ada kebijakan
retensi serta pemulihan yang disetujui.

Migrasi tetap dijalankan satu kali sebagai job terpisah setelah backup dan
pengujian, bukan dari setiap worker API. Perintah Compose pada dokumen scaffold
lama ditujukan untuk instalasi baru; operasi API aktif memakai release project
pada dokumen ini. Frontend, HTTPS publik, backup off-host dan monitoring lanjutan
belum dikonfigurasi pada tahap ini.


## Release antarmuka web

UI diterapkan 12 November 2026 setelah alur browser pada PostgreSQL terpisah lulus.
Schema tetap 0005_reviews; tidak ada migrasi atau seed saat pembaruan UI. Container
backend sebelumnya `hotel-maintenance-api-current` dipertahankan stopped dengan
restart policy no, begitu juga container scaffold lama. Jangan memulai container
API lama bersamaan dengan release web karena port 8000 dipakai release aktif.

Backup sebelum pembaruan UI:
`/root/backups/hotel-maintenance/20261112T043020Z-web/database.dump`; record serta
checksum di deployment.json pada direktori sama. Image sebelum UI:
`hotel-maintenance-api:before-web-20261112`. Database/volume dan akun supervisor
tetap dipertahankan. Health/root/static assets pada container web telah diperiksa.
Pembaruan ini tidak mengubah firewall/SSH atau membuka port publik.

Akses browser melalui tunnel PuTTY dan petunjuk penggunaan ada di [WEB.md](WEB.md).
Dokumen backup pada bagian sebelumnya merujuk penerapan backend pertama;
compose.release.yaml adalah konfigurasi release backend sebelumnya yang sekarang
stopped. Operasi aktif memakai compose.web.yaml dan project hotel-maintenance-web.


## Release detail inventaris

Pada 12 November 2026, revision 0006_device_details menambah kolom opsional merek,
model, lokasi, IPv4/IPv6, MAC dan catatan. Backup sebelum migrasi:
`/root/backups/hotel-maintenance/20261112T044740Z-inventory/database.dump`;
checksum dan hasil penerapan di deployment.json pada direktori sama.
Backup berhasil di-restore pada PostgreSQL 17 terpisah; upgrade 0005 → 0006 dan
fingerprint semua tabel data lama diverifikasi sebelum migrasi utama. Kolom baru
pada data lama tetap NULL; akun, sesi, inventaris, tugas dan riwayat tetap utuh.

Container aktif sekarang hotel-maintenance-web-inventory, project Compose
hotel-maintenance-web-inventory dengan compose.web.yaml. Container sebelumnya
hotel-maintenance-web-current dipertahankan stopped, restart policy no; image
sebelumnya hotel-maintenance-api:before-inventory-20261112. Bagian release web
di atas merupakan riwayat penerapan sebelumnya. URL/port tunnel tidak berubah.

Verifikasi: 27 tes backend lokal lulus, 8 dilewati pada suite default; 7 tes
PostgreSQL staging lulus, 3 tes scaffold lulus, alur browser lengkap termasuk
create/edit detail perangkat, revisi dan approval lulus. OpenAPI/asset terbaru,
revision database dan health telah diperiksa setelah penerapan. Tidak ada data
contoh/akun baru yang ditambahkan ke database utama.


## Release kunjungan hotel / foto wajib (0007)

Container aktif: hotel-maintenance-web-hotel-visits-v2, project Compose dengan nama
sama dan compose.web.yaml. Container API sebelumnya tetap stopped dengan restart
policy no. Database tetap hotel-maintenance-db-1 pada volume semula; port API tetap
127.0.0.1:8000. Volume tambahan hotel-maintenance_photos dipasang pada
/app/storage/photos. Jangan hapus volume tersebut; sertakan dalam backup.

Backup sebelum migrasi 0006 → 0007:
/root/backups/hotel-maintenance/20261112T065131Z-hotel-visits/database.dump
beserta photos.tar.gz dan deployment.json pada direktori sama. Restore ke
PostgreSQL terpisah dan migrasi berhasil; fingerprint semua tabel lama identik.
0007 hanya membuat tabel baru, tanpa seed atau perubahan laporan lama.

Backup berpasangan terakhir sebelum perbaikan penanganan AP gagal diukur:
/root/backups/hotel-maintenance/20261112T065552Z-hotel-visits-v2/database.dump
beserta photos.tar.gz dan checksum pada deployment.json. Schema tetap 0007.
Backup disimpan dengan permission root-only; tar foto saat penerapan masih kosong
karena belum ada foto produksi. Volume telah diuji lintas container memakai
probe sementara yang dibersihkan. Restore database aktual juga diverifikasi
sebelum release final. Backup off-host terjadwal belum tersedia.

Image sebelum perubahan hotel: hotel-maintenance-api:before-hotel-visits-20261112.
Image penerapan awal hotel: hotel-maintenance-api:hotel-visits-initial-20261112.
Tidak ada downgrade database otomatis. Untuk pemulihan bukti, database dan file
foto harus dari backup konsisten; jangan menimpa data aktif atau menjalankan down -v.

33 tes backend, 10 tes PostgreSQL staging, 3 scaffold dan browser end-to-end pada
image produksi lulus. Health, OpenAPI/foto endpoint, mount volume dan root/assets
release diperiksa. User/record produksi tidak dibuat sebagai data uji. Petunjuk
penggunaan dan batas fitur saat ini ada di HOTEL_VISITS.md. Bagian deployment lama
di atas merupakan riwayat; gunakan project/container aktif pada bagian awal.


## Release speedtest otomatis (0008)

Aktif: hotel-maintenance-web-speedtest, project hotel-maintenance-web-speedtest,
file compose.web.yaml. URL tetap localhost:8000 dan volume foto sama. Container
API sebelumnya dipertahankan stopped dengan restart policy no. Image sebelum
perubahan: hotel-maintenance-api:before-speedtest-20261112.

Backup berpasangan sebelum migrasi:
/root/backups/hotel-maintenance/20261112T081616Z-speedtest/database.dump,
photos.tar.gz dan deployment.json (checksum/hasil penerapan) pada direktori sama.
Restore ke PostgreSQL terpisah, migrasi 0007 → 0008 dan fingerprint seluruh data
lama diverifikasi sebelum penerapan utama. Tidak ada seed atau data pengukuran
contoh yang dibuat ke produksi. 0008 hanya menambah tabel network_speedtests.

PUBLIC_SPEEDTEST_ORIGIN tetap kosong. Speedtest tersedia sebagai diagnostik
localhost/tunnel; hasil tidak diterapkan sebagai bandwidth AP. Belum ada domain
HTTPS/reverse proxy publik, SSH/firewall dan port publik tidak diubah. Endpoint
transfer bukan endpoint umum: memakai tiket khusus singkat di header. Satu
proses API, paling banyak dua pengukuran bersamaan dan satu per teknisi.

37 tes backend, 12 PostgreSQL staging, 3 scaffold lulus. Chromium mengukur data
nyata dalam jaringan uji yang dibatasi di browser; mode diagnostik/cancel dan
seluruh alur foto/revisi/approval lulus pada image produksi. Jalur pengaitan hasil
HTTPS diuji lewat request integrasi, bukan lewat domain publik yang sudah live.
Catatan engine, kredensial transfer dan syarat aktivasi lapangan: SPEEDTEST.md.


## Release revisi laporan utama / profil site (0009)

Aktif: hotel-maintenance-web-report-form, project dengan nama sama, compose.web.yaml.
Backup: /root/backups/hotel-maintenance/20261112T093230Z-report-form/database.dump
beserta photos.tar.gz dan deployment.json pada direktori sama. Restore pada
PostgreSQL terpisah dan upgrade 0008 → 0009 berhasil; fingerprint seluruh data
lama (termasuk field hotel sebelum tambahan nullable) identik sebelum/sesudah.
Foto tetap pada volume yang sama. Tidak ada seed nama pelanggan/SLA/persen dan
laporan historis tidak ditulis ulang. Container API lama tetap stopped/restart no;
image pemulihan hotel-maintenance-api:before-report-form-20261112.

47 backend, 14 PostgreSQL staging, 3 scaffold dan browser pada image Docker lulus.
API/database sehat; port tetap localhost8000, PUBLIC_SPEEDTEST_ORIGIN tetap kosong.
Konfigurasi sekali di menu Hotel, alur form baru, hasil otomatis dan kompatibilitas
laporan lama dijelaskan di REPORT_FORM.md. Catatan release sebelumnya di atas
adalah riwayat, bukan project/container yang aktif sekarang.


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


## Navigasi berbasis hotel — 13 November 2026

Frontend diperbarui tanpa restart API atau perubahan Compose. Sidebar, Detail Hotel
dan PM bulanan dijelaskan di [NAVIGATION.md](NAVIGATION.md). Backup asset:
`/root/backups/hotel-maintenance/20261113T031213Z-hotel-navigation/`.
Image pemulihan: `hotel-maintenance-api:before-navigation-20261113`. Tag image
sampling existing dibangun ulang; container aktif tetap sama, asset live cocok source.
Tidak ada migration atau perubahan API/backend. Health API/database ok.
