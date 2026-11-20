# Revisi NUSA MAINTENANCE 1.2.0 — 19 November 2026

Rilis backend hotel-maintenance-api:ui-revisi-20261119T034713Z aktif setelah backup konsisten dan uji restore.
Schema tetap 0012, semua row lama terjaga identik, tidak ada migration atau seed baru.
Default area baru 2, link test radio numerik JSON dan auto-identifikasi AP melalui
BSSID sudah aktif. Android 1.2.0 memakai revisi dokumen pengguna. Detail lengkap:
[REVISI-TAMPILAN-2026-11-19.md](REVISI-TAMPILAN-2026-11-19.md).

# Sampling teknisi aktif — 18 November 2026

Operator menyetujui backup, uji restore, deployment dan migration 0010–0012.
Rilis aktif: `hotel-maintenance-api:sampling-field-20261118T101650Z`, container `hotel-maintenance-web-sampling`.
Schema produksi sekarang **0012_sampling_speedtest_attempts**. Keempat gate master,
field locations, observasi dan session speedtests aktif. PUBLIC_SPEEDTEST_ORIGIN
adalah https://maintenance.inisaja.id. Backend tetap bind 10.100.23.103:8000,
proxy TLS tetap 10.100.23.103:443; database/foto memakai volume semula.

Backup konsisten database.dump + photos.tar.gz dibuat dengan API berhenti sementara:
`/root/backups/hotel-maintenance/sampling-field-20261118T101650Z`. File backup/record deployment mode 0600, direktori 0700.
Restore ke PostgreSQL 17.6 `--network none` berhasil, lalu upgrade 0009→0012 dan
fingerprint semua tabel lama identik. Baru setelah itu upgrade produksi dilakukan;
fingerprint seluruh data lama tetap sama dan tujuh tabel baru kosong saat migrasi
selesai. Tidak ada seed atau data pengukuran QA dimasukkan ke produksi.

Image yang sama diuji pada salinan restore: QA login teknisi, check-in, penambahan
lokasi/replay UUID, observasi native client-reported, tiket/CORS transfer, transfer
byte download/upload serta finish per sesi. Akun/lokasi/radio/metrik QA hanya ada
di database salinan terisolasi yang dibersihkan. Uji tersebut bukan bukti radio
atau throughput HP fisik.

Verifikasi rilis: 82 test backend lulus pada Python 3.12 image produksi (25 opt-in
skipped), 24 test PostgreSQL terisolasi lulus melalui chain aktif sampai 0012.
Pengulangan suite pada Python 3.14 development sempat crash; suite produksi 3.12
lulus. Test dependencies dipasang hanya ke layer container QA sementara, tidak
mengubah dependency image rilis. Health/API kontrak HTTPS privat dan publik lulus,
route lapangan/observasi/speedtest tersedia. Proxy HTTPS dipercaya hanya dari
alamat host/gateway yang ditentukan. Tidak memakai forwarded-allow-ips='*'.

Semua asset Web source disalin ke image baru; image lama tetap tersedia untuk
recovery. Tidak ada downgrade schema atau pemulihan dump di atas data baru.
Jika perlu mematikan write baru, gunakan gate di backend baru agar guard bukti
sampling tetap berlaku. Jangan kembali ke backend lama setelah bukti V2 tercatat.

APK teknisi terbaru: versi 1.1.0 (versionCode 2),
artifacts/android/hotel-maintenance-https-debug.apk. Login tanpa kolom origin.
Setelah check-in: Sampling → Tambah lantai / titik sampling → masukkan lokasi
aktual dan AP inventaris jika dikenali. Hasil AP lama tidak disalin ke sesi baru.
AP tidak dikenal belum dapat start speedtest; dapat dicatat gagal uji beralasan.
Dokumentasi per sesi/PIC dan completion V2 masih tahap berikutnya; jangan mengklaim
seluruh maintenance selesai hanya dari pengukuran.

Catatan sebelumnya di bawah adalah riwayat sebelum aktivasi.

# HTTPS Let’s Encrypt — 18 November 2026

Caddy systemd service hotel-maintenance-https.service sudah aktif/enabled pada
10.100.23.103:443, reverse proxy ke API privat 10.100.23.103:8000. Sertifikat
maintenance.inisaja.id diterbitkan Let’s Encrypt YE2; berakhir 16 Februari 2027.
Bootstrap menggunakan jalur HTTP yang sudah diteruskan NOC; API dihentikan
sementara lalu dipulihkan dan health/database diverifikasi. Tidak ada migration.

Health/kontrak login HTTPS privat lulus dengan sertifikat publik terverifikasi.
Jalur publik 110.232.70.162:443 masih ditolak, sehingga login HP belum dinyatakan
siap. NOC perlu forward TCP443 ke 10.100.23.103:443. Renewal otomatis TLS-ALPN-01
bergantung jalur ini. Private key hanya di state root-private Caddy di luar repo.
Detail operasi dan batas verifikasi: deploy/https/README.md.

# Binding IP privat — 18 November 2026

Atas instruksi operator, published port API di compose.sampling.yaml berubah dari
127.0.0.1:8000 menjadi **10.100.23.103:8000**. Container tetap
hotel-maintenance-web-sampling; image kini hotel-maintenance-api:private-bind-20261118.
Backend code memakai image deployed sebelumnya; hanya aset web aktif disalin ke
image turunan supaya perubahan UI dalam writable layer tidak hilang saat recreate.
Tidak menyertakan source Phase 4/5 yang belum dideploy. Database dan volume foto,
network Docker, environment aplikasi serta migration tidak diubah.

Validasi: /health dan /health/db lewat IP privat berstatus ok; binding Docker tepat
10.100.23.103:8000 dan checksum semua file web identik sebelum/sesudah. Healthcheck
127.0.0.1 di dalam container tetap benar karena backend listen 0.0.0.0 di container.
Salinan Compose sebelumnya, aset/checksum web dan Compose rollback tersedia pada
artifacts/private-bind/. Rollback mengembalikan binding localhost dengan image yang
mempertahankan aset aktif; gunakan project-directory repo untuk pemuatan .env.

Upstream NOC: http://10.100.23.103:8000. HTTPS maintenance.inisaja.id belum aktif;
reverse proxy/firewall/NAT publik tidak dipasang atau diubah pada langkah ini.
Bagian di bawah merupakan riwayat, termasuk referensi binding localhost lama.

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

## Pengukuran koneksi HP — APK 1.3.0

Backend aktif: `hotel-maintenance-api:phone-network-20261119T042217Z`; schema `0013_phone_network_runs`.
Backup database/foto privat: `/root/backups/hotel-maintenance/phone-network-20261119T042217Z`. Restore terisolasi, upgrade,
alur API tanpa AP inventaris, dan transfer byte sungguhan pada salinan lulus.
Seluruh baris produksi dengan kolom semula memiliki fingerprint identik
sebelum/sesudah migration. Tidak ada data QA di produksi. Health/API HTTPS
domain dan IP publik lulus. APK 1.3.0/code4 sudah diverifikasi signature/aset.
Lihat docs/reviews/PHONE-NETWORK-0013.md untuk batas rollback.

## Aktivasi rilis 1.4.0

Backend: `hotel-maintenance-api:completion-20261119T044137Z`. Schema tetap `0013_phone_network_runs`;
tidak ada perubahan tabel/network pada rilis ini. Backup privat database/foto:
`/root/backups/hotel-maintenance/completion-20261119T044137Z`. Restore, pengujian image pada salinan PostgreSQL,
foto/replay, PIC/replay, submit dan PDF lulus. Semua fingerprint data produksi
identik sebelum/sesudah update. Tidak ada data QA di produksi.

89 test backend runtime Python 3.12 lulus; 29 opt-in dilewati dalam suite biasa.
28 test PostgreSQL terisolasi dan 42 frontend lulus. Build, lint, signature,
versi dan kecocokan aset APK lulus. Browser alur penuh pada API asli dan
regresi tampilan/offline lulus. Layout PDF ditinjau dari hasil render.

APK: `artifacts/android/nusa-maintenance-1.4.0-debug.apk`; versionCode 5. Sertifikat penandatangan
sama dengan 1.3.0 sehingga mendukung upgrade. SHA-256: `d4272a67af4345549ee677fbfb3b82ee1724cedb3a6dd6edb73e71fafb4db3db`.
Alias `hotel-maintenance-https-debug.apk` diperbarui ke berkas yang sama.
Batas verifikasi: native radio/speedtest dan intent berbagi PDF masih memerlukan
uji perangkat fisik; tidak diklaim dari fixture browser atau build.

Aktif di https://maintenance.inisaja.id. Image: `hotel-maintenance-api:web-branding-20261119T063733Z`.
Backup database/foto: `/root/backups/hotel-maintenance/web-branding-20261119T063733Z`. Restore dan QA pada
salinan lulus; fingerprint seluruh data produksi tidak berubah. Schema tetap
0013. Pengecekan HTTPS publik memastikan title/logo/login baru, PNG identik
dengan Android, sidebar tanpa menu template, dan layout 390/1440 tanpa overflow.

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

## Rilis 1.6.1: UI dan profil teknisi

Operator menyetujui deployment dan penambahan profil. Image aktif
`hotel-maintenance-api:profile-ui-20261119T152738Z`, schema
`0014_user_contact_profile`. Backup privat, uji restore/image, perbandingan data
lama dan HTTPS lulus. APK `artifacts/android/nusa-maintenance-1.6.1-debug.apk`
(code9) beserta alias memiliki sertifikat upgrade yang sama dengan 1.5.0.
Rincian: docs/PROFILE-RELEASE-1.6.1.md.

## Rilis Review Recovery 1.7.0

Image `hotel-maintenance-api:review-recovery-20261119T161501Z`, schema tetap0014.
Backup, restore dan image QA lulus; seluruh fingerprint produksi identik.
APK code10/1.7.0 dan alias terverifikasi sertifikat/aset.
Detail: docs/REVIEW-RECOVERY-1.7.md.
