# Hotel Maintenance

Backend FastAPI/PostgreSQL dengan dashboard supervisor dan teknisi. Kunjungan
hotel mencakup router/switch/LAN, sampling AP per lantai/kamar, laporan backbone
FO/wireless dan foto wajib yang disimpan privat. Revisi/approval menyimpan
snapshot. Approval pekerjaan pending tidak dianggap maintenance selesai.

Backend dan web telah diterapkan hingga `0009_site_report_profile` pada 12 November 2026.
Tidak ada akun bawaan atau seed produksi. Speedtest otomatis pada AP tersedia, saat ini mode diagnostik tunnel/lokal.
Hasil lapangan memerlukan origin HTTPS langsung yang diverifikasi. Sinyal/channel
masih manual; Wi-Fi analyzer native, APK/offline, PDF dan tanda tangan belum tersedia. Alur perangkat lama tetap dipertahankan.

[Penggunaan kunjungan hotel dan foto](docs/HOTEL_VISITS.md) ·
[Catatan deployment aktif](docs/DEPLOYMENT.md)

Kontrak API, pengamanan, batas pengujian dan langkah deployment aman tersedia di
[panduan modul](docs/MODULES.md). Rancangan tahapan lanjutan tersedia di
[rencana implementasi](docs/IMPLEMENTATION.md).

Migration `0002_maintenance` menambah users, sesi login dan jadwal tanpa mengubah
atau menghapus tabel hotel/perangkat yang sudah ada. CRUD memakai role dan
validasi; detail endpoint tersedia melalui OpenAPI `/docs`.

## Konfigurasi

Salin `.env.example` ke `.env`, lalu isi `POSTGRES_PASSWORD` dengan secret unik
yang kuat. Jangan commit `.env`. Nilai kosong ditolak Compose dan aplikasi.
Password diteruskan melalui environment container; batasi akses Docker dan file
`.env` pada operator tepercaya. Mengubah password dalam `.env` tidak mengganti
password pada volume PostgreSQL yang sudah diinisialisasi.

Di Compose, host database selalu `db:5432`. Untuk proses lokal di lingkungan
pengembangan yang mempunyai PostgreSQL sendiri, aplikasi juga menerima
`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, dan `POSTGRES_USER`.

## Batas jaringan

PostgreSQL tidak mempunyai published port. Database dan migrasi hanya terhubung
ke network Docker dengan `internal: true`. API terhubung ke network internal dan
bridge `api_network` untuk konektivitas host/akses keluar, dipublikasikan eksplisit
pada **127.0.0.1:8000** di host. Uvicorn mendengarkan `0.0.0.0` **di dalam
container** agar Docker dapat meneruskan koneksi localhost host ke container.
Tidak ada perubahan firewall, SSH, atau jaringan host dalam scaffold ini.
Database tetap terisolasi; API memiliki akses keluar melalui bridge. Integrasi
Google belum dikonfigurasi.

## Scaffold Compose (untuk instalasi baru)

Instalasi yang sedang berjalan memakai compose.sampling.yaml; ikuti docs/DEPLOYMENT.md
agar tidak menjalankan API lama bersamaan. Scaffold berikut memerlukan
Docker Engine dan Compose v2 dengan dukungan
`service_completed_successfully`. Perintah berikut hanya dokumentasi dan
belum dijalankan saat pembuatan scaffold:

```bash
cp .env.example .env
# Edit .env dan isi password terlebih dahulu.
docker compose config --quiet
docker compose up --build -d
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/health/db
docker compose ps
docker compose logs migrate api
```

`/health` mengembalikan HTTP 200 `{"status":"ok"}` tanpa query database.
`/health/db` menjalankan `SELECT 1`: HTTP 200 bila berhasil atau HTTP 503
`{"status":"unavailable"}` bila koneksi/query gagal. Detail koneksi tidak
masuk respons. Pemeriksaan ini tidak membuktikan migrasi terbaru terpasang;
Compose memastikan migrasi sukses sebelum API pertama kali dimulai.
Koneksi dibatasi timeout dan connection pool dibuang saat shutdown.

Data PostgreSQL disimpan pada named volume `postgres_data`. Jangan gunakan
`docker compose down -v` pada lingkungan yang datanya harus dipertahankan.
Lakukan backup dan uji restore sebelum perubahan schema produksi.

## Migrasi

Migrasi awal hanya membuat schema dan metadata versi Alembic, tanpa seed data.
Layanan `migrate` menjalankan `alembic upgrade head`; bila gagal, API tidak
dijalankan. Untuk perubahan berikutnya, buat revision Alembic yang ditinjau dan
uji pada database terpisah sebelum dipakai di produksi. Jangan menjalankan
migrasi dari setiap worker API. Pengguna PostgreSQL pada scaffold ini juga
menjadi pemilik schema; pisahkan role migrasi dan runtime sebelum menambah
endpoint penulisan untuk produksi.

## Pengujian

Gunakan virtualenv, tanpa memasang paket sistem:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/python -m unittest discover -s tests -v
```

Tes default memakai mock koneksi untuk memeriksa respons API saat database
tersedia, gagal terhubung, atau query gagal. SQL migrasi diperiksa offline,
sehingga tes ini tidak membuktikan penerapan DDL pada PostgreSQL nyata.
Tes integrasi koneksi diaktifkan hanya bila `TEST_DATABASE_URL` diisi dengan
URL SQLAlchemy `postgresql+psycopg://...` milik **database pengujian terpisah**.
Tes integrasi hanya menjalankan `SELECT 1` dan tidak memasukkan data.

Pemeriksaan statis tanpa dependensi aplikasi (memerlukan PyYAML):

```bash
python3 -m unittest discover -s tests -v
```

Validasi penerapan migrasi dan startup lengkap tetap harus dilakukan pada
PostgreSQL pengujian ketika Docker tersedia dan eksekusinya diizinkan.

Tes migrasi dan workflow PostgreSQL terisolasi tersedia melalui
`HOTEL_STAGING_DATABASE_URL` pada database khusus `_test`/`_staging`.
Lihat [petunjuk staging](docs/MODULES.md#pengujian-postgresql-staging-terisolasi).
Suite ini menulis dan membersihkan schema uji acak. Pada 12 November 2026,
6 tes staging lulus pada PostgreSQL 17.6 dalam container sementara terpisah.
Ini tidak menerapkan source terbaru ke container aplikasi yang sudah berjalan.


## Antarmuka web

Dashboard supervisor dan teknisi sudah terpasang pada localhost server di port
8000. Buka melalui SSH tunnel PuTTY lalu login dengan akun yang sudah dibuat.
[Petunjuk akses dan penggunaan](docs/WEB.md). Container aktif:
`hotel-maintenance-web-sampling`, dikelola dengan compose.sampling.yaml. Sesi browser
hanya di memori; mode offline/tanda tangan belum tersedia.


Inventaris kini mendukung merek/model, lokasi pemasangan, IPv4/IPv6, MAC dan
catatan opsional. [Bahan diskusi data pemeriksaan](docs/DATA_REQUIREMENTS.md).


## Speedtest otomatis

Pada AP sampling, teknisi dapat menjalankan download/upload/ping/jitter otomatis.
Hasil tunnel PuTTY/lokal tersimpan sebagai diagnostik dan tidak dimasukkan ke
bandwidth AP. Mode lapangan membutuhkan HTTPS langsung serta konfirmasi Wi-Fi;
SSID/BSSID/sinyal/channel belum dapat dibaca otomatis oleh browser.
[Petunjuk speedtest dan batas pengukuran](docs/SPEEDTEST.md).


## Laporan utama terbaru

Nama pelanggan otomatis dari master site; profil bandwidth FO/wireless dan batas
persentase diatur sekali oleh supervisor. Form Backbone memisahkan download dan
upload dengan penilaian otomatis, menambah link test radio dan menghapus input
TX/RX/CCQ. Bagian LAN serta Wireless/Hotspot mempunyai lima keterangan terpisah.
[Pengaturan profil dan aturan penilaian](docs/REPORT_FORM.md).


## Dashboard sampling

Desain sampling Phase B sudah terpasang pada 13 November 2026. Buka kunjungan hotel → Dashboard sampling → lantai → detail titik. Draf catatan/foto tersimpan lokal pada browser; Wi-Fi analyzer native dan sinkronisasi draf belum tersedia. Lihat [audit dan batas fitur](docs/SAMPLING_AUDIT.md).

## Android UI — Phase 3

Source React + Capacitor tersedia di [`android-app/`](android-app/README.md).
Lihat [hasil dan batas integrasi Phase 3](docs/PHASE-3-ANDROID-UI.md) untuk build APK,
verifikasi frontend, draf lokal, serta fitur native/sinkronisasi yang belum tersedia.
Belum ada APK release atau deployment Android.

## Fondasi sampling server — source lokal

Master lantai/titik dan snapshot cakupan kunjungan sudah mempunyai model/API serta
integrasi Web/Android. Snapshot mempertahankan lokasi historis dan sesi berbeda
untuk tiap titik. Pengukuran per sesi dan submit V2 belum tersedia; alur kunjungan
legacy serta Backbone FO/wireless dan LAN tetap dipertahankan.
Fitur default nonaktif dan migration 0010 masih draft di luar head Alembic.
Belum diterapkan ke database/deployment. Lihat
[cakupan implementasi dan pengujian](docs/SAMPLING-MASTER-IMPLEMENTATION.md).

Catatan/temuan/tindakan per sesi sekarang dapat dikirim Web/Android dengan
antrean lokal dan retry UUID yang sama. Kontrak penyimpanan observasi Wi-Fi
tersedia; pengumpulan native dan verifikasi radio belum diimplementasikan.
Draft 0011 dan gate write masih nonaktif; lihat
[batas dan verifikasi observasi](docs/SAMPLING-OBSERVATIONS.md).

Source [Phase 4 Wi-Fi native](docs/PHASE-4-NATIVE-WIFI.md) menambah plugin Android,
scanner 2.4/5 GHz, grafik serta draf capture per sesi. Kompilasi Java dan frontend
lulus; pengujian radio HP fisik masih wajib. Fondasi juga diuji pada PostgreSQL
18.6 sementara melalui Unix socket privat, tanpa Docker atau database produksi.
