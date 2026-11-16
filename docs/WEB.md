# Antarmuka Hotel Network Maintenance

Antarmuka web berbahasa Indonesia sudah berjalan di `http://127.0.0.1:8000/`
pada server. File HTML/CSS/JavaScript disertakan di image FastAPI, sehingga UI dan
API memakai origin yang sama. Tidak memerlukan Node.js atau proses frontend
terpisah. Tidak ada koneksi ke layanan hosting eksternal.

## Membuka dari komputer melalui PuTTY

API tetap hanya tersedia di localhost server. Pada jendela PuTTY yang sudah
terhubung ke server:

1. Klik ikon PuTTY di pojok kiri atas → **Change Settings**.
2. Buka **Connection → SSH → Tunnels**.
3. Isi **Source port**: `8080`.
4. Isi **Destination**: `127.0.0.1:8000` dan pilih **Local**.
5. Klik **Add**, lalu **Apply**. Pertahankan koneksi PuTTY tetap terbuka.
6. Buka `http://127.0.0.1:8080/` di browser komputer, lalu login dengan akun nyata.

Jika port 8080 komputer sudah digunakan, pilih 8081 untuk Source port dan buka
127.0.0.1:8081. Pengaturan ini membuat tunnel melalui SSH; tidak memerlukan
perubahan firewall/sshd, tidak membuka database, dan tidak mempublikasikan API.
Untuk menyimpan tunnel pada koneksi berikutnya, simpan konfigurasi sesi PuTTY.

## Alur supervisor

- Masuk menggunakan username/password yang dibuat melalui bootstrap.
- Tambahkan hotel, inventaris perangkat dan anggota tim teknisi.
- Buat template checklist (satu baris per item wajib, maksimal 100 item).
  Template immutable: perubahan harus berupa template baru.
- Buat jadwal dengan perangkat, teknisi aktif dan bulan preventive maintenance.
- Pada daftar jadwal, klik **Buat kunjungan** dan pilih template yang sesuai
  jenis perangkat. Kunjungan lama tanpa template dapat diikat sekali.
- Buka kunjungan submitted, periksa checklist, GPS/pengecualian serta riwayat.
  Minta revisi atau setujui dengan alasan keputusan. Approval mengunci laporan
  dan otomatis menyelesaikan jadwal.
- Form ubah/hapus untuk hotel, perangkat, pengguna dan jadwal mengikuti izin
  serta constraint backend. Jadwal yang punya kunjungan tidak bisa diganti;
  perubahan password/role/aktivasi akun mencabut sesi akun tersebut.

## Alur teknisi

- Teknisi hanya melihat jadwal dan kunjungan miliknya pada UI.
- Mulai kunjungan melalui check-in. Browser mencoba GPS; jika tidak tersedia,
  teknisi wajib menjelaskan alasan sebenarnya. Tidak ada koordinat rekaan.
- Isi hasil setiap pemeriksaan. Hasil bermasalah/tidak berlaku wajib disertai
  catatan tindakan/alasan. Klik **Simpan jawaban** sebelum check-out.
- Check-out mengirim laporan setelah seluruh item wajib terjawab. Pada tahap ini
  alasan pengecualian tanda tangan PIC wajib diisi karena fitur tanda tangan
  belum tersedia. Jawaban fail tetap dapat dikirim untuk ditinjau supervisor.
- Jika diminta revisi, perbaiki jawaban, simpan lalu kirim ulang. GPS dan waktu
  check-out asli dipertahankan. Laporan approved tidak dapat diedit.

## Sesi dan batas kemampuan

Token Bearer hanya di memori JavaScript: tidak disimpan di localStorage,
sessionStorage, cookie, URL atau source. Reload/menutup halaman mengharuskan login
ulang. Tombol keluar mencabut sesi server. Setiap izin/status/version tetap
keputusan backend; menyembunyikan tombol bukan pengganti otorisasi server.
Tidak ada mode offline/outbox atau penyimpanan draft lokal. Jangan memuat ulang
atau pindah halaman sebelum menyimpan jawaban. Jika respons terputus/konflik,
muat ulang data untuk memeriksa status sebelum mencoba lagi.

Foto, tanda tangan digital, PDF, Wi-Fi analyzer native, speedtest, sinkronisasi
Google dan aplikasi Android belum tersedia. UI ini merupakan web online yang
responsif. GPS tergantung izin browser/perangkat dan belum diverifikasi radius.

## Pengujian

- Backend: 25 passed, 7 skipped pada suite default; 3 unittest scaffold passed.
  Enam tes PostgreSQL staging juga telah lulus pada tahap sebelumnya.
- Browser Chromium dengan PostgreSQL 17 terpisah: pembuatan master data,
  penugasan, login dua peran, check-in GPS, checklist, check-out, review revisi,
  kirim ulang, approval, jadwal completed dan empat snapshot riwayat terverifikasi.
- Viewport 1440×1000 dan 390×844 diperiksa; tidak ada overflow halaman pada ponsel.
  Sesi hanya di memori dan reload kembali ke login, tanpa pageerror browser.
- Halaman login produksi, static assets, CSP, health dan database diperiksa.
  Login positif produksi dilakukan pengguna sendiri; pengujian otomasi tidak
  memakai atau membaca password pengguna. Tabel users utama tetap satu; tidak
  ada hotel/perangkat contoh yang ditambahkan.

Script: `scripts/run_web_staging.py`, alur browser di
`tests/browser/workflow.py`. Script membuat database container sementara,
menjalankan server hanya di localhost dan membersihkan sumber daya miliknya.
Dependencies pengujian browser terpisah: `backend/requirements-browser.txt`.
Chromium dan library browser perlu tersedia pada runner; jangan menambah library
ke image produksi. Pada sesi ini library browser diekstrak hanya ke /tmp,
bukan dipasang sebagai paket sistem host. Screenshot/log pengujian tersedia di
`artifacts/web/` dan diabaikan Git/build context.


## Detail inventaris tambahan (revision 0006)

Form Perangkat kini memuat merek, model, lokasi pemasangan, IPv4/IPv6, MAC dan
catatan opsional. Daftar menampilkan lokasi/IP dan serial/MAC; detail kunjungan
memperlihatkan identitas perangkat tersebut. Field kosong tidak diberi nilai
rekaan. Alamat IP/MAC divalidasi di server; MAC dinormalisasi menjadi huruf kecil
berpemisah titik dua. Perubahan data master tidak mengubah snapshot laporan lama.
Refresh halaman dan login kembali untuk memuat form terbaru. Akses tetap melalui
alamat tunnel yang sama. Hasil verifikasi terbaru ada di DEPLOYMENT.md.


## Alur hotel terbaru

Gunakan menu Kunjungan hotel untuk penugasan baru; kunjungan/jadwal perangkat
lama tetap tersedia pada menu terpisah. Form baru mencakup backbone, LAN, laporan
utama dan AP sampling, dengan unggah foto privat per perangkat. Refresh halaman
dan login kembali untuk memuat menu terbaru. Akses tunnel tidak berubah.
Lihat HOTEL_VISITS.md untuk langkah supervisor/teknisi dan batas tahap manual.


## Pengukuran otomatis terbaru

Pada kartu AP sampling kunjungan hotel, teknisi mendapat tombol Jalankan speedtest.
Pilih band/jaringan yang benar, konfirmasi Wi-Fi bila digunakan, lalu mulai uji.
Download/upload/ping/jitter ditampilkan dan disimpan otomatis. Pada akses PuTTY,
hasil diberi label diagnostik dan tidak menimpa bandwidth AP. Gunakan domain HTTPS
langsung yang diverifikasi operator untuk mode lapangan; lihat SPEEDTEST.md.
Tidak ada pembacaan sinyal/channel otomatis di web. Refresh lalu login kembali
untuk memuat skrip/widget terbaru. URL tunnel tetap sama.


## Revisi laporan utama (0009)

Form terkini memakai nama pelanggan otomatis dari site, profil bandwidth/ambang
sekali per site dan penilaian download+upload otomatis. TX/RX/CCQ tidak lagi tampil
pada form baru, ditambah hasil link test radio dan lima keterangan LAN/Wireless/
Hotspot yang wajib. Tidak ada ambang default atau data produksi yang diisi rekaan.
REPORT_FORM.md menjadi petunjuk terbaru untuk bagian laporan utama; bagian di
atas yang menggambarkan form lama merupakan riwayat tahap sebelumnya.
