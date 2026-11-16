# CODEX TASK — Implementasi Detail Sampling Hotel Maintenance

## 1. Konteks Project

Kita sedang mengembangkan aplikasi **Hotel Network Maintenance** untuk teknisi yang melakukan preventive maintenance internet hotel secara bulanan.

Lokasi project:

`/root/apps/hotel-maintenance`

Stack yang sudah digunakan:
- Backend: FastAPI + PostgreSQL + Alembic
- Infrastruktur: Docker Engine + Docker Compose
- Aplikasi Android: React + Capacitor dengan plugin native Android
- Speedtest: LibreSpeed
- Penyimpanan laporan: Google Sheets dan Google Drive (integrasi bertahap)

**PENTING: Pertahankan semua backend, database, API, Docker Compose, dan fitur yang sudah berjalan.**

Jangan membangun ulang project dari nol.

## 2. Tujuan Implementasi

Buat tampilan Android **Detail Sampling Wi-Fi** yang modern, profesional, responsif, dan nyaman digunakan teknisi di hotel.

Struktur navigasi:

**Dashboard Hotel → Detail Lantai → Detail Titik Sampling**

Setiap lantai memiliki 4 titik sampling default. Jumlah titik harus bisa dikonfigurasi untuk masing-masing lantai.

Contoh:
- Lantai 1
  - Kamar 101
  - Kamar 105
  - Koridor Tengah
  - Area Lift
- Lantai 2 dan seterusnya mengikuti konfigurasi hotel.

Jangan mengisi database produksi dengan data contoh tersebut.

## 3. Desain Antarmuka

Gunakan desain mobile-first dengan:
- Warna utama navy blue, biru dan teal.
- Background terang.
- Kartu informasi dengan sudut membulat.
- Typography jelas, ukuran angka pengukuran cukup besar.
- Navigasi sederhana.
- Indikator loading, error, offline, dan status pemeriksaan.
- Layout responsif untuk Android berbagai ukuran.
- Dark mode opsional, bukan prioritas MVP.

Halaman Detail Sampling menampilkan nama hotel, lantai, lokasi sampling, waktu pemeriksaan, dan status pekerjaan.

Bagian pengujian menggunakan tab **Wi-Fi Analyzer**, **Speedtest**, dan **Foto & Catatan**.

## 4. Connected Network — Seperti WiFiman

Buat kartu informasi jaringan Wi-Fi yang sedang digunakan HP teknisi.

Tampilkan:
- SSID
- BSSID
- Nama AP (jika berhasil dicocokkan)
- Band 2.4 GHz / 5 GHz / 6 GHz jika tersedia
- Frequency (MHz)
- Channel
- RSSI (dBm)
- Link speed jika tersedia
- IP address lokal
- Gateway
- Connection status

Ambil data langsung dari API native Android menggunakan plugin Capacitor/Kotlin.

Gunakan Android WifiManager dan API sistem yang sesuai versi Android.

Implementasikan permission handling yang benar.

**Aturan penting:**
- Jangan mengarang nama AP.
- Nama AP hanya ditampilkan apabila BSSID cocok dengan inventaris atau data controller.
- Jika tidak cocok, tampilkan BSSID dan status "AP belum teridentifikasi".
- Jika izin lokasi/Wi-Fi ditolak, tampilkan penjelasan dan cara mengaktifkannya.
- Jangan memakai dummy network data sebagai data pengukuran sebenarnya.

## 5. Wi-Fi Analyzer

Buat dua pilihan band:

**2.4 GHz | 5 GHz**

Setiap band menampilkan:
- Jumlah network/AP terdeteksi
- Daftar SSID dan BSSID
- RSSI (dBm)
- Channel
- Frequency
- Security type jika tersedia
- Indikasi channel overlap
- Grafik kekuatan sinyal
- Waktu pemindaian terakhir

Gunakan hasil scan dari radio Wi-Fi HP Android.

Grafik harus menggunakan data aktual, bukan grafik statis.

Jika Android membatasi frekuensi scan, jelaskan kondisi tersebut pada UI. Tampilkan waktu scan terakhir agar teknisi tahu apakah data masih baru.

Jangan mengklaim scan lengkap jika OS hanya memberikan hasil cache.

Untuk 2.4 GHz, tampilkan visualisasi channel overlap berdasarkan data scan. Untuk 5 GHz, tampilkan informasi channel dan kepadatan sebagai estimasi, bukan pengukuran interferensi radio yang pasti.

Buat fungsi untuk menyimpan hasil scan ke titik sampling aktif.

## 6. LibreSpeed — Speedtest

Buat halaman speedtest dengan tampilan modern.

Tampilkan:
- Download Mbps
- Upload Mbps
- Ping/latency ms
- Jitter ms jika engine mendukung
- Status pengujian
- Waktu pengujian
- Server pengujian
- Durasi tes

Alur:

1. Teknisi menekan "Mulai Speedtest".
2. Aplikasi menjalankan pengujian nyata menggunakan LibreSpeed.
3. Tampilkan progress secara real-time jika didukung.
4. Setelah selesai, tampilkan hasil.
5. Teknisi dapat menyimpan hasil ke titik sampling.

Gunakan endpoint LibreSpeed yang sudah dikonfigurasi, atau sediakan konfigurasi server jika belum tersedia.

Jangan membuat hasil speedtest simulasi di production mode.

Tangani timeout, jaringan terputus, serta perubahan koneksi Wi-Fi ke data seluler saat pengujian.

Jangan menyimpan hasil pengujian sebagai hasil Wi-Fi jika ternyata trafik menggunakan data seluler.

## 7. Foto Dokumentasi

Buat tab **Foto & Catatan**.

Kategori dokumentasi:
- Foto Access Point
- Foto perangkat jaringan
- Foto area sampling
- Foto temuan/kerusakan

Gunakan kamera Android melalui Capacitor.

Setiap foto mempunyai:
- ID titik sampling
- Kategori
- Timestamp
- Keterangan opsional
- Status sinkronisasi

Tampilkan foto dalam thumbnail grid dua kolom.

Teknisi bisa melihat foto ukuran penuh dan menghapus foto yang belum disubmit setelah konfirmasi.

Simpan file lokal terlebih dahulu apabila perangkat sedang offline.

## 8. Catatan Teknisi

Buat textarea dengan label **Catatan Teknisi**.

Tambahkan:
- Status titik: Baik / Perlu Perhatian / Bermasalah / Belum Diperiksa
- Deskripsi temuan
- Tindakan teknisi
- Rekomendasi tindak lanjut

Catatan dan data pemeriksaan harus tersimpan otomatis secara lokal supaya tidak hilang ketika berpindah tab atau koneksi internet terputus.

## 9. Dashboard dan Detail Lantai

Dashboard hotel menampilkan:
- Nama hotel
- Periode maintenance
- Jumlah lantai
- Total titik sampling
- Jumlah selesai
- Jumlah temuan
- Progress keseluruhan

Setiap lantai memiliki kartu ringkasan dengan progress 4 titik sampling default.

Halaman Detail Lantai menampilkan kartu masing-masing titik dengan:
- Nama lokasi
- Status pengujian
- RSSI terakhir
- Download Mbps terakhir
- Band koneksi terakhir
- Waktu pemeriksaan

Angka hasil pengukuran hanya boleh muncul jika ada data aktual. Jika belum dites, tampilkan "Belum diuji".

## 10. Database dan API

Pertama, audit schema PostgreSQL, migration Alembic, endpoint FastAPI dan modul frontend yang sudah ada.

Gunakan struktur yang sudah tersedia.

Jika data sampling belum didukung, rancang penambahan secara additive untuk:
- Hotel floor
- Sampling point
- Sampling session
- Wi-Fi connection measurement
- Wi-Fi scan result
- Speedtest result
- Sampling photo
- Technician note

Sebelum membuat migration, jelaskan perubahan schema dan dampaknya.

**Jangan menjalankan migration otomatis, drop table, reset database, atau menghapus data.**

Untuk fase pertama, boleh mengimplementasikan frontend dan service interface terlebih dahulu. Jika endpoint belum tersedia, tampilkan status "Belum tersedia", bukan menggunakan hasil pengukuran palsu.

## 11. Aturan Keamanan

- Jangan mengubah konfigurasi server atau firewall.
- Jangan mengubah port PostgreSQL maupun FastAPI.
- Jangan mengubah Docker network.
- Jangan menghapus container atau volume.
- Jangan menampilkan credential dalam log.
- Jangan memasukkan API key ke frontend.
- Jangan membuka API langsung ke IP publik.
- Jangan menggunakan mode Codex yang melewati approval/sandbox.
- Gunakan source code dan konfigurasi existing.
- Minta approval sebelum operasi yang memerlukan sudo atau deployment.
- Utamakan perubahan kecil dan mudah diuji.

## 12. Urutan Pengerjaan

**Phase A — Audit**
1. Baca struktur project saat ini.
2. Identifikasi framework frontend.
3. Periksa plugin native Android yang sudah ada.
4. Periksa endpoint backend dan struktur database.
5. Buat laporan gap analysis.

**Phase B — UI**
1. Implementasikan Dashboard Hotel.
2. Implementasikan Detail Lantai.
3. Implementasikan Detail Sampling.
4. Buat komponen Connected Network.
5. Buat tab Wi-Fi Analyzer, Speedtest, Foto & Catatan.
6. Tambahkan loading, empty state, error state, dan offline state.

**Phase C — Native Integration**
1. Implementasikan Wi-Fi connection info.
2. Implementasikan Wi-Fi scan Android.
3. Integrasikan LibreSpeed.
4. Integrasikan kamera.
5. Hubungkan data ke sampling aktif.

**Phase D — Testing**
1. Jalankan lint/typecheck/build.
2. Tambahkan unit tests pada fungsi pengukuran dan penyimpanan.
3. Uji alur tanpa izin lokasi.
4. Uji jaringan offline.
5. Pastikan backend existing tidak terganggu.

## 13. Hasil yang Diharapkan

Setelah selesai, laporkan:
- File yang dibuat atau diubah.
- Halaman UI yang sudah berfungsi.
- Fitur yang sudah memakai data nyata.
- Fitur yang masih membutuhkan backend/API.
- Hasil pengujian.
- Langkah untuk build APK.
- Kendala teknis yang belum terselesaikan.

**Mulai dari Phase A, kemudian implementasikan Phase B. Jangan langsung menjalankan deployment atau migration database.**
