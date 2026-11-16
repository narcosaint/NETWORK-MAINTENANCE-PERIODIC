Kita akan membangun aplikasi Hotel Network Maintenance dari nol.

Lingkungan:
- Ubuntu Server fisik dengan akses IP publik
- Semua source code berada di direktori project saat ini
- Backend FastAPI + PostgreSQL + Docker Compose
- Android menggunakan React + Capacitor + plugin native Kotlin
- Google Sheets untuk rekap, Google Drive untuk arsip
- LibreSpeed untuk pengujian koneksi
- Offline-first untuk teknisi

Fitur aplikasi:
1. Login teknisi dan supervisor
2. Master hotel dan inventaris router/switch/AP
3. Jadwal preventive maintenance bulanan
4. Checklist maintenance per perangkat
5. Foto dokumentasi
6. Wi-Fi analyzer otomatis dari radio HP Android: SSID, BSSID, RSSI, frekuensi, channel
7. Speedtest download/upload/latency
8. GPS check-in/check-out
9. Tanda tangan PIC hotel
10. PDF laporan maintenance
11. Sinkronisasi Google Sheets dan Google Drive
12. Penyimpanan offline dan sinkronisasi ketika internet kembali

Tugas pertama:
- Audit OS, disk, RAM, Docker, firewall, port, dan tool yang tersedia secara read-only.
- Buat rancangan arsitektur, ERD, struktur project, dan rencana implementasi bertahap.
- Setelah audit, buat scaffold backend FastAPI, PostgreSQL dan Docker Compose di folder project ini.
- Jangan mengekspos PostgreSQL atau FastAPI langsung ke IP publik.
- PostgreSQL hanya lewat internal Docker; FastAPI hanya bind ke 127.0.0.1.
- Jangan mengubah konfigurasi SSH/firewall tanpa persetujuan.
- Jangan menggunakan data dummy di database produksi.
- Jangan menghapus file atau container yang sudah ada.
- Jangan menjalankan perintah destruktif.
- Jangan menyimpan password, API key, atau secret ke source code atau Git.
- Minta persetujuan sebelum install paket sistem, menjalankan sudo, mengubah firewall, atau melakukan deployment.
- Buat tes kesehatan API dan koneksi database.
- Laporkan apa yang berhasil, gagal, dan langkah berikutnya.

Kerjakan bertahap, mulai dari audit dan arsitektur. Jelaskan rencana sebelum melakukan perubahan besar.Kita akan membangun aplikasi Hotel Network Maintenance dari nol.

Lingkungan:
- Ubuntu Server fisik dengan akses IP publik
- Semua source code berada di direktori project saat ini
- Backend FastAPI + PostgreSQL + Docker Compose
- Android menggunakan React + Capacitor + plugin native Kotlin
- Google Sheets untuk rekap, Google Drive untuk arsip
- LibreSpeed untuk pengujian koneksi
- Offline-first untuk teknisi

Fitur aplikasi:
1. Login teknisi dan supervisor
2. Master hotel dan inventaris router/switch/AP
3. Jadwal preventive maintenance bulanan
4. Checklist maintenance per perangkat
5. Foto dokumentasi
6. Wi-Fi analyzer otomatis dari radio HP Android: SSID, BSSID, RSSI, frekuensi, channel
7. Speedtest download/upload/latency
8. GPS check-in/check-out
9. Tanda tangan PIC hotel
10. PDF laporan maintenance
11. Sinkronisasi Google Sheets dan Google Drive
12. Penyimpanan offline dan sinkronisasi ketika internet kembali

Tugas pertama:
- Audit OS, disk, RAM, Docker, firewall, port, dan tool yang tersedia secara read-only.
- Buat rancangan arsitektur, ERD, struktur project, dan rencana implementasi bertahap.
- Setelah audit, buat scaffold backend FastAPI, PostgreSQL dan Docker Compose di folder project ini.
- Jangan mengekspos PostgreSQL atau FastAPI langsung ke IP publik.
- PostgreSQL hanya lewat internal Docker; FastAPI hanya bind ke 127.0.0.1.
- Jangan mengubah konfigurasi SSH/firewall tanpa persetujuan.
- Jangan menggunakan data dummy di database produksi.
- Jangan menghapus file atau container yang sudah ada.
- Jangan menjalankan perintah destruktif.
- Jangan menyimpan password, API key, atau secret ke source code atau Git.
- Minta persetujuan sebelum install paket sistem, menjalankan sudo, mengubah firewall, atau melakukan deployment.
- Buat tes kesehatan API dan koneksi database.
- Laporkan apa yang berhasil, gagal, dan langkah berikutnya.

Kerjakan bertahap, mulai dari audit dan arsitektur. Jelaskan rencana sebelum melakukan perubahan besar.
