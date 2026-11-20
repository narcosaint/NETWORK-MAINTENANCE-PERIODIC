RILIS REVIEW DAN HASIL MAINTENANCE — 19 NOVEMBER 2026:
APK 1.7.0/backend/Web aktif: pemulihan antrean catatan lama, perbandingan konflik,
pesan tombol PIC/check-out/PDF terlihat, menu hasil supervisor dan grafik interaktif.
Schema tetap 0014; data lama utuh. Rincian: docs/REVIEW-RECOVERY-1.7.md.

RILIS UI DAN PROFIL — 19 NOVEMBER 2026:
APK 1.6.1 dan backend/Web telah diaktifkan atas persetujuan operator.
Revisi form/foto/PIC/check-out/PDF ditambah kontak profil teknisi tersimpan di server.
Migration 0014 direview dan diuji sebelum diterapkan; data lama/cakupan tetap utuh.
Rincian: docs/PROFILE-RELEASE-1.6.1.md dan docs/reviews/USER-PROFILE-0014.md.

PENYESUAIAN OPERATOR — AREA LAPANGAN BEBAS:
Jumlah lantai dan area mengikuti pemeriksaan teknisi, tanpa minimum per lantai.
Pengujian satu halaman; foto area opsional dan foto terkirim tetap dimuat di PDF.
Menu perangkat dan kartu cakupan sampling dihilangkan dari UI; histori tetap utuh.

IMPLEMENTASI ALUR LAPORAN — 19 NOVEMBER 2026:
Dokumentasi area, review PIC, submit dan PDF diintegrasikan dalam rilis 1.4.0.
Lihat docs/COMPLETION-RELEASE.md untuk rancangan, alur dan batas verifikasi.

PENYESUAIAN OPERATOR — PENGUKURAN DARI HP:
Wi-Fi Analyzer dan speedtest area menggunakan koneksi Wi-Fi aktual HP.
Inventaris AP, pemetaan perangkat, dan pencocokan MAC bukan syarat pengukuran.
Riwayat/API inventaris lama tetap dipertahankan untuk kompatibilitas.

PENYESUAIAN OPERATOR — DOKUMEN REVISI 19 NOVEMBER 2026:
Nama aplikasi NUSA MAINTENANCE; UI menggunakan istilah area; target awal baru
2 area, menggantikan default 4 untuk pembuatan baru. Target/data lama tetap utuh.
Revisi dokumen pengguna mengambil prioritas atas angka 4 pada riwayat roadmap.
Lihat docs/REVISI-TAMPILAN-2026-11-19.md.

# PROJECT: HOTEL NETWORK MAINTENANCE V2
# MASTER ROADMAP & DEVELOPMENT INSTRUCTIONS

PENYESUAIAN DISETUJUI OPERATOR — 18 NOVEMBER 2026:
Teknisi yang ditugaskan boleh menambah lantai/area dan titik sampling aktual
langsung dari Android saat kunjungan dapat diedit setelah check-in. Perubahan
lapangan harus memiliki alasan, actor, UUID retry, dan audit pada kunjungan.
Cakupan boleh bertambah tanpa menghapus/mengubah bukti yang sudah ada. Default
4 titik tetap target; jangan membuat lokasi/pengukuran dummy. Histori kunjungan
lain tetap utuh. Ini menggantikan pembatasan penambahan lokasi hanya supervisor;
pengelolaan master administratif existing tetap tersedia untuk supervisor.
Lihat docs/FIELD-SAMPLING.md. Deployment/migration tetap memerlukan persetujuan.


KONTEKS:
Kita sedang mengembangkan aplikasi Hotel Network Maintenance
untuk teknisi Nusanet yang melakukan preventive maintenance
internet hotel setiap bulan.

Project sudah berjalan di Ubuntu Server dengan:
- FastAPI
- PostgreSQL
- Alembic
- Docker Compose
- Frontend Web
- React + Capacitor untuk Android (target)
- LibreSpeed (target/integrasi sesuai kondisi existing)

Lokasi project:
~/apps/hotel-maintenance

PENTING:
Ini adalah kelanjutan project existing.
JANGAN membuat project baru.
JANGAN menghapus database, migration, API, atau data lama.
JANGAN mengubah konfigurasi Docker, firewall, SSH, dan port.
Audit kondisi kode existing sebelum implementasi.

==================================================
1. KONSEP APLIKASI FINAL
==================================================

Gunakan konsep HYBRID MAINTENANCE + WIFIMAN.

Aplikasi memiliki dua interface:

A. WEB ADMIN / SUPERVISOR
Untuk pengelolaan hotel, jadwal, teknisi,
template checklist, monitoring dan laporan.

B. ANDROID TEKNISI
Untuk maintenance lapangan, pengukuran Wi-Fi,
speedtest, dokumentasi, dan tanda tangan PIC.

Kedua platform menggunakan backend dan database
yang sama.

==================================================
2. STRUKTUR MENU WEB
==================================================

Sidebar utama:

1. Ringkasan
2. Maintenance Hotel
3. Data Hotel
4. Tim Teknisi
5. Template Checklist

Hilangkan dari navigasi utama:
- Kunjungan Perangkat
- Perangkat
- Jadwal Perangkat

JANGAN menghapus database maupun endpoint lama.

Inventaris perangkat dipindahkan ke:
Data Hotel > Detail Hotel > Perangkat.

Detail Hotel mempunyai tab:
- Informasi Hotel
- Lantai
- Titik Sampling
- Perangkat
- Riwayat Maintenance

Pertahankan tema desain existing:
- Sidebar hijau tua
- Background putih/terang
- Card modern
- Layout responsif
- Bahasa Indonesia

==================================================
3. DASHBOARD WEB
==================================================

Dashboard menampilkan:

- Total hotel
- Maintenance bulan berjalan
- Maintenance selesai
- Maintenance tertunda
- Total temuan
- Progress pekerjaan teknisi

Detail maintenance per hotel:

- Nama hotel
- Periode
- Teknisi
- Jumlah lantai
- Jumlah titik sampling
- Progress tiap lantai
- Status laporan utama
- Status dokumentasi
- Status persetujuan PIC

Gunakan status:
- Belum Dikerjakan
- Dalam Proses
- Selesai
- Selesai dengan Temuan
- Perlu Review

==================================================
4. ALUR ANDROID TEKNISI
==================================================

Pilih Jadwal Maintenance
        |
Pilih Hotel
        |
Check-in GPS
        |
LAPORAN UTAMA
        |
SAMPLING WI-FI
        |
DOKUMENTASI
        |
REVIEW & SUBMIT
        |
TANDA TANGAN PIC
        |
GENERATE PDF

Tampilkan progress setiap tahap.

Data form harus dapat disimpan sementara
dan dilanjutkan ketika koneksi terputus.

==================================================
5. LAPORAN UTAMA - TEMPLATE NUSANET
==================================================

PERTAHANKAN semua field pemeriksaan existing
yang berasal dari template PDF Nusanet.

Jangan menghapus field existing.

Bagian utama:

A. INFORMASI PELANGGAN
- Nama hotel
- Alamat
- PIC
- Kontak PIC
- Tanggal maintenance
- Teknisi

B. BACKBONE FIBER OPTIC
- Service Agreement (Mbps)
- Hasil Speedtest (Mbps)
- Sesuai / Tidak Sesuai
- Keterangan

C. WIRELESS BACKBONE
- Signal Strength (dBm)
- TX Rate (Mbps)
- RX Rate (Mbps)
- CCQ / Link Test (%)
- Hasil Speedtest (Mbps)
- Kualitas link
- Keterangan

D. LOCAL AREA NETWORK
- Koneksi LAN Router
- Koneksi LAN Switch
- Signal Test
- Blank Spot Area
- Hotspot
- Keterangan setiap pemeriksaan

Tampilan checklist:
- Judul item menggunakan a, b, c otomatis.
- Status berupa dropdown.
- Label textarea hanya "Keterangan".
- Jangan menampilkan "Keterangan a", "Keterangan b",
  atau pengulangan nama pemeriksaan.
- Pisahkan item menggunakan spacing dan separator.
- UI harus nyaman dipakai di HP.

==================================================
6. SAMPLING WI-FI PER LANTAI
==================================================

Struktur:

HOTEL
  > LANTAI
    > TITIK SAMPLING

Default 4 titik sampling per lantai.

Contoh:
Lantai 1:
- Kamar 101
- Kamar 105
- Koridor Tengah
- Area Lift

Contoh tersebut hanya untuk UI development.
Jangan insert data dummy ke database produksi.

Supervisor dapat:
- Menambah lantai
- Mengubah nama lantai
- Menambah titik sampling
- Mengubah lokasi titik sampling
- Mengatur urutan sampling

JUMLAH SAMPLING DEFAULT = 4 PER LANTAI.

SPEEDTEST WAJIB DI SETIAP TITIK SAMPLING.

Tidak boleh menggunakan satu speedtest untuk
mewakili empat titik.

==================================================
7. DETAIL TITIK SAMPLING
==================================================

Setiap titik mempunyai halaman detail.

HEADER:
- Nama hotel
- Nama lantai
- Nama titik sampling
- Waktu pemeriksaan
- Status

TAB 1: WIFI ANALYZER
TAB 2: SPEEDTEST
TAB 3: FOTO & CATATAN

--------------------------------------------------
TAB 1 - WIFI ANALYZER
--------------------------------------------------

CONNECTED NETWORK:

Ambil informasi koneksi HP teknisi:

- SSID
- BSSID
- Nama AP jika cocok dengan inventaris
- Frequency
- Channel
- Band
- RSSI (dBm)
- Link Speed
- IP Address
- Gateway

Gunakan Android native API:
WifiManager dan API Android terkait.

Untuk plugin Capacitor gunakan Kotlin/Java.

Jangan menggunakan data simulasi untuk
hasil pengukuran produksi.

Jika AP belum dikenali berdasarkan BSSID,
tampilkan "AP Belum Teridentifikasi".

WIFI SCANNER:

Buat dua tab:
[2.4 GHz] [5 GHz]

Tampilkan:
- SSID
- BSSID
- RSSI
- Channel
- Frequency
- Grafik sinyal
- Jumlah network terdeteksi
- Channel overlap (estimasi)
- Waktu scan terakhir

Grafik terinspirasi aplikasi WiFiman.

Perhatikan permission Android dan
pembatasan Wi-Fi scanning.

Simpan hasil scan pada titik sampling aktif.

--------------------------------------------------
TAB 2 - SPEEDTEST
--------------------------------------------------

Gunakan LibreSpeed.

Tampilkan:
- Download Mbps
- Upload Mbps
- Ping ms
- Jitter ms jika tersedia
- Test server
- Timestamp
- Status pengujian

Buat tombol:
[MULAI SPEEDTEST]

Hasil speedtest langsung masuk ke
titik sampling yang sedang diperiksa.

WAJIB:
Setiap titik sampling mempunyai hasil speedtest
sendiri.

Jika gagal:
- Status: Gagal Diuji
- Alasan wajib diisi
- Tandai sebagai temuan

Jangan mengarang hasil pengujian.

Validasi bahwa pengujian memakai koneksi Wi-Fi
yang dimaksud, bukan data seluler.

--------------------------------------------------
TAB 3 - FOTO & CATATAN
--------------------------------------------------

Fitur:
- Foto Access Point
- Foto perangkat
- Foto area sampling
- Foto temuan

Gunakan kamera Android.

Tampilkan thumbnail dua kolom.

Setiap foto menyimpan:
- Sampling ID
- Kategori
- Timestamp
- Catatan
- Status sinkronisasi

Tambahkan Catatan Teknisi:
- Kondisi jaringan
- Temuan
- Tindakan
- Rekomendasi

Status sampling:
- Baik
- Perlu Perhatian
- Bermasalah
- Belum Diperiksa

==================================================
8. DOKUMENTASI UTAMA
==================================================

Selain foto pada tiap titik sampling,
buat dokumentasi untuk infrastruktur hotel.

Kategori:
- Router
- Switch
- Rack
- Backbone
- Access Point
- Kabel
- Temuan lainnya

Foto harus terhubung dengan Visit ID
dan hotel yang diperiksa.

==================================================
9. REVIEW DAN SUBMIT
==================================================

Sebelum submit lakukan validasi:

1. Laporan Utama sudah diisi.
2. Seluruh lantai sudah diperiksa.
3. Seluruh titik sampling telah diperiksa.
4. Setiap titik punya hasil speedtest
   atau status gagal dengan alasan.
5. Foto wajib sesuai konfigurasi tersedia.
6. Temuan telah diberi keterangan.
7. PIC hotel telah meninjau hasil.

Tambahkan tanda tangan digital PIC.

Data tanda tangan:
- Nama PIC
- Jabatan
- Timestamp
- Signature image

Generate laporan PDF yang mencakup:
- Data hotel dan teknisi
- Backbone Fiber Optic
- Wireless Backbone
- Local Area Network
- Hasil sampling per lantai
- Wi-Fi RSSI
- Speedtest per titik
- Foto dokumentasi
- Temuan
- Tanda tangan PIC

PDF menggunakan data aktual.

==================================================
10. DATABASE
==================================================

Audit database yang sudah ada.

Gunakan tabel existing bila memungkinkan.

Jika diperlukan, rancang tabel tambahan:

- hotel_floors
- sampling_points
- sampling_sessions
- wifi_connection_results
- wifi_scan_results
- speedtest_results
- sampling_photos
- maintenance_findings
- maintenance_signatures
- maintenance_reports

Semua data sampling harus terhubung dengan:
- Hotel
- Visit
- Floor
- Sampling Point
- Periode maintenance

Simpan histori bulanan.

Jangan menjalankan migration tanpa review.
Gunakan migration additive dan non-destructive.

==================================================
11. OFFLINE FIRST
==================================================

Android harus mendukung:

- Checklist offline
- Foto offline
- Catatan offline
- Hasil scan Wi-Fi offline
- Penyimpanan sementara hasil speedtest
- Sinkronisasi ketika internet tersedia

Gunakan UUID untuk menghindari duplikasi data.

Jika speedtest gagal karena offline,
jangan membuat angka hasil palsu.

==================================================
12. ATURAN DEVELOPMENT
==================================================

- Pertahankan backend existing.
- Jangan membuat ulang Docker Compose.
- Jangan menghapus database.
- Jangan reset PostgreSQL.
- Jangan mengubah firewall.
- Jangan mengubah SSH.
- Jangan membuka port publik.
- Jangan menghapus fitur lama tanpa analisis.
- Jangan menaruh credential dalam source code.
- Jangan insert dummy ke database produksi.
- Jangan menjalankan deployment otomatis.
- Jangan menjalankan migration tanpa persetujuan.

==================================================
13. ROADMAP IMPLEMENTASI
==================================================

PHASE 1 - AUDIT & ALIGNMENT

Audit:
- Backend existing
- Database schema
- Frontend existing
- Route dan navigasi
- Template checklist
- API existing
- Android project
- LibreSpeed integration

Buat dokumen:
docs/ROADMAP-V2.md
docs/ARCHITECTURE-V2.md
docs/DATABASE-GAP-V2.md

PHASE 2 - WEB UI

Implementasikan:
- Sidebar final
- Dashboard maintenance
- Detail hotel
- Detail lantai
- Titik sampling
- Progress maintenance

PHASE 3 - ANDROID UI

Implementasikan:
- Dashboard teknisi
- Detail kunjungan
- Laporan Utama
- Sampling per lantai
- Detail titik sampling
- Review laporan

PHASE 4 - NATIVE WIFI

Implementasikan:
- Connected network
- Wi-Fi scanner
- RSSI 2.4/5 GHz
- Grafik sinyal
- AP identification

PHASE 5 - LIBRESPEED

Implementasikan:
- Speedtest tiap titik
- Simpan hasil
- Validasi koneksi
- Status gagal uji

PHASE 6 - DOKUMENTASI

Implementasikan:
- Foto perangkat
- Catatan teknisi
- Temuan
- Signature

PHASE 7 - REPORTING

Implementasikan:
- PDF
- Riwayat maintenance
- Google Sheets sync
- Google Drive archive

PHASE 8 - TESTING

Uji:
- Android build
- Backend tests
- API integration
- Offline sync
- GPS
- Wi-Fi permission
- Speedtest nyata
- Generate PDF

==================================================
14. INSTRUKSI EKSEKUSI SEKARANG
==================================================

MULAI DARI PHASE 1.

Lakukan audit project existing secara read-only.

Bandingkan kondisi source code sekarang dengan
master roadmap ini.

Buat tiga dokumen:
1. ROADMAP-V2.md
2. ARCHITECTURE-V2.md
3. DATABASE-GAP-V2.md

Identifikasi:
- Fitur yang sudah tersedia
- Fitur yang perlu diperbaiki
- Fitur yang belum dibuat
- Database yang perlu ditambah
- API yang perlu ditambah
- Prioritas implementasi

JANGAN langsung implementasi seluruh phase.
JANGAN deploy.
JANGAN menjalankan migration.
JANGAN mengubah konfigurasi server.

Setelah audit selesai, laporkan hasilnya
dan rekomendasikan pekerjaan Phase 2.
