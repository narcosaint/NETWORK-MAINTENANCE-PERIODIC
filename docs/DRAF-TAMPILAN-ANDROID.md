# Draf Tampilan Nusa Maintenance — Android

Versi review 1 · 18 November 2026
Acuan: APK 1.1.0 yang sekarang. Ini dokumen susunan layar, bukan kode aplikasi.

## Cara edit

Hapus baris/blok yang tidak ingin ditampilkan. Ganti langsung teks atau nama tombol.
Pindahkan blok untuk mengganti urutan. Tambahkan komentar dengan awalan CATATAN:.
Kalau ingin menyembunyikan bagian panjang dalam panel buka/tutup, tulis LIPAT:.
Kirim kembali dokumen yang sudah diedit atau salin bagian revisinya ke chat.

Contoh:
HAPUS: kartu Progress pekerjaan di Beranda.
UBAH: tombol "Buka maintenance" menjadi "Mulai pemeriksaan".
PINDAH: Connected Network ke dalam tab Wi-Fi Analyzer.

Menghapus bagian pada draf berarti usulan perubahan tampilan. Data dan histori
laporan yang sudah tersimpan tidak otomatis dihapus. Backbone FO, Wireless
Backbone dan LAN tetap dicantumkan sebagai acuan template laporan utama.

## 1. Masuk

Judul: HOTEL NETWORK
Teks kecil: PREVENTIVE MAINTENANCE
Kalimat pembuka: Siap merawat jaringan hotel.
Subjudul: Workspace teknisi Nusanet

Form:
- Username
- Password

Tombol: Masuk ke workspace
Informasi koneksi: tersedia / offline
Pesan saat login gagal
Keterangan: password/token tidak disimpan untuk login berikutnya
Footer: MAINTENANCE + WIFI DIAGNOSTICS

Alamat server sudah otomatis; tidak ada kolom origin API.

CATATAN:

## 2. Navigasi utama

Menu bawah:
- Beranda
- Jadwal
- Review
- Profil

Ketika membuka kunjungan:
- Hotel
- Laporan
- Sampling
- Review

CATATAN:

## 3. Beranda dan Jadwal

Sapaan: Halo, [nama teknisi].
Kalimat pembuka: Pilih hotel dan lanjutkan pemeriksaan jaringan.

Kartu ringkasan:
- Jumlah penugasan
- Jumlah PM selesai
- Progress pekerjaan: dalam proses / perlu review

Daftar penugasan:
- Nama hotel
- Periode / tanggal
- Status pekerjaan
- Tombol: Buka maintenance

Kontrol tambahan:
- Muat ulang jadwal
- Informasi offline / data tersimpan
- Pesan bila belum ada penugasan

CATATAN:

## 4. Detail kunjungan dan Check-in

Informasi hotel:
- Nama hotel
- Alamat
- Tanggal / periode maintenance
- Status kunjungan

Check-in:
- Tombol: Check-in dengan GPS
- Pilihan pengecualian GPS dengan alasan bila diperlukan

Tahapan pekerjaan:
- Laporan Utama
- Sampling Wi-Fi
- Review Laporan

Kontrol:
- Kembali
- Muat ulang kunjungan
- Informasi koneksi / penyimpanan draf

CATATAN:

## 5. Laporan Utama

### 5A. Informasi pelanggan

- Nama pelanggan / hotel
- Nama PIC
- Kontak PIC
- Jenis koneksi backbone: FO / wireless / keduanya / failover / bonding

### 5B. Backbone Fiber Optic

- SLA download dan upload
- Hasil download dan upload
- Status kesesuaian
- Keterangan
- Bagian data laporan lama bila tersedia

### 5C. Wireless Backbone

- SLA download dan upload
- Hasil download dan upload
- Signal strength
- Hasil link test radio
- Status kesesuaian
- Keterangan
- Data laporan lama jika ada: TX, RX, CCQ dan isian terkait

### 5D. Local Area Network

Setiap item berisi Status dan Keterangan:
- a. Koneksi LAN Router
- b. Koneksi LAN Switch
- c. Signal Test
- d. Blank Spot Area
- e. Hotspot

Catatan LAN lama ditampilkan bila masih tersimpan.

### 5E. Hasil pekerjaan

- Ringkasan / hasil pemeriksaan
- Hasil pekerjaan: selesai / pending
- Alasan pending
- Feedback pelanggan
- Solusi / tindak lanjut
- Alasan pengecualian tanda tangan PIC

Tombol: Simpan laporan ke server
Informasi: Draf lokal / Data server / konflik penyimpanan

CATATAN:

## 6. Sampling per lantai / area

Judul: Sampling per lantai
Ringkasan: jumlah lantai dan progress titik

Daftar lantai / area:
- Nama lantai / area
- Jumlah titik
- Target titik; awalnya 4, dapat bertambah
- Daftar titik sampling
- Nama AP jika sudah dihubungkan
- Status masing-masing titik

Tombol: Tambah lantai / titik sampling

Form penambahan lokasi oleh teknisi:
- Pilih lantai / area tujuan, atau buat lantai / area baru
- Nama lantai / area baru
- Empat baris awal titik; baris kosong tidak dibuat sebagai titik nyata
- Pada setiap baris: nama titik, lokasi, pilihan AP inventaris
- Tombol: Tambah baris titik
- Alasan penambahan lokasi
- Tombol: Simpan lokasi ke kunjungan
- Tombol kirim ulang bila respons sebelumnya terputus

Informasi draf offline dan status pengiriman

CATATAN:

## 7. Detail titik sampling

Header:
- Nama titik
- Nama AP / AP belum dikenali
- Status pemeriksaan

### 7A. Connected Network

- SSID
- BSSID
- Frequency
- Channel
- Band
- RSSI
- Link speed
- IP address
- Gateway
- Waktu pembacaan

Tombol: Baca koneksi Wi-Fi
Informasi izin lokasi bila diperlukan

### 7B. Tab Wi-Fi Analyzer

- Pilihan band: 2.4 GHz / 5 GHz
- Tombol scan Wi-Fi
- Grafik sinyal
- Jumlah jaringan terdeteksi
- Daftar SSID / BSSID / RSSI / kanal
- Waktu scan dan penanda cache bila hasil dari cache Android
- Keterangan estimasi kanal berdekatan
- Kartu pengukuran manual lama jika ada

### 7C. Tab Speedtest

- Persetujuan penggunaan bandwidth sebelum mulai
- Tombol: Mulai / kirim ulang speedtest
- Download Mbps
- Upload Mbps
- Ping ms
- Jitter ms jika tersedia
- Tahap / progress pengujian
- Tombol: Batalkan pengujian
- Riwayat hasil, waktu, server uji, dan alasan gagal

Jika tidak dapat diuji:
- Alasan gagal uji
- Tombol: Simpan alasan gagal uji

### 7D. Tab Foto & Catatan

- Lokasi sampling
- Kondisi: belum diperiksa / baik / perlu perhatian / bermasalah
- Catatan teknisi
- Temuan
- Tindakan
- Rekomendasi
- Tombol simpan catatan ke server
- Pilihan kirim ulang setelah review bila terjadi konflik

Foto:
- Kategori foto
- Keterangan foto
- Ambil foto / pilih foto perangkat
- Thumbnail foto dan status penyimpanan

Catatan status: catatan/radio per sesi sudah tersedia. Foto per sesi belum
tersinkronisasi penuh; jangan menuliskannya sebagai fitur yang sudah selesai.

CATATAN:

## 8. Review kunjungan

- Ringkasan laporan utama
- Ringkasan Backbone FO, Wireless Backbone dan LAN
- Tombol: Tinjau laporan utama
- Daftar lantai / titik dan status kelengkapannya
- Daftar temuan
- Penanda temuan lokal yang belum dikirim
- Informasi PIC
- Tombol kembali ke sampling

Bagian yang sekarang masih berupa informasi fitur belum tersedia:
- Tanda tangan PIC
- Submit V2
- PDF Android

Bagian ini boleh dihapus dari rancangan tampilan atau dipindah ke bagian rencana.
Mengubah drafnya tidak membuat fitur tersebut otomatis tersedia.

CATATAN:

## 9. Profil

- Nama teknisi
- Username
- Peran akun
- Status sinkronisasi / draf lokal
- Keterangan penyimpanan
- Alamat server sebagai informasi saja
- Tombol keluar akun

CATATAN:

## 10. Keputusan tampilan keseluruhan

Nama aplikasi yang diinginkan:

Warna utama:

Gaya tampilan (sederhana / banyak informasi / lainnya):

Menu yang ingin dihapus:

Bagian yang ingin dilipat agar lebih ringkas:

Nama tombol yang ingin diganti:

Urutan menu / tahapan yang diinginkan:

Bagian yang harus selalu terlihat:

Catatan tambahan:
