# Rilis 1.7.0 — Review/PIC/check-out dan hasil maintenance supervisor

Aktif 19 November 2026, melanjutkan persetujuan deployment operator dan permintaan
perbaikan aplikasi. Image: `hotel-maintenance-api:review-recovery-20261119T161501Z`.
Schema tetap `0014_user_contact_profile`: tanpa migration, perubahan jaringan atau
penghapusan data. Compose hanya mengganti image aplikasi.

## Perbaikan Review Android

Antrean observasi dari sesi lama dapat berisi versi area lama, sementara server
sudah memiliki catatan atau hasil speedtest baru. Pesan error CompletionPanel
sebelumnya berada di bagian atas kartu, sehingga setelah menekan tombol bawah
pengguna dapat tidak melihat alasan gagal.

- Tombol preview bernama **Review Hasil PDF**.
- Server memeriksa baseline observasi historis pada versi yang dimiliki draf.
  Perubahan independen pada kolom berbeda digabungkan di dalam transaksi yang
  mengunci kunjungan. Snapshot Wi-Fi yang lebih baru tidak ditimpa draf radio lama.
  Perubahan kolom yang sama dengan nilai berbeda tetap ditolak, dengan detail
  isian server/perangkat dan versi aktual. Versi dari masa depan tetap ditolak.
- Saat kolom benar-benar bentrok, aplikasi menampilkan perbandingan area dan dua
  pilihan eksplisit: gunakan isian perangkat setelah review atau isian server.
  Kiriman yang sudah pasti ditolak dan draf asal disimpan untuk recovery lokal
  sebelum diganti. Tidak ada overwrite otomatis untuk konflik isi nyata.
- UUID request dengan respons hilang tetap digunakan. Jika request lama diterima
  sementara teknisi sudah mengedit lagi, perubahan terbaru ikut dikirim sebelum
  draf dibersihkan. Kolom server yang digabungkan secara independen tidak ikut
  dikosongkan oleh request lanjutan. Prepare Review juga menyelesaikan outbox yang
  masih menunggu walaupun isi tampilan terlihat sama.
- Pesan proses/validasi/gagal difokuskan dan digulirkan ke layar, termasuk konflik
  serta nama/jabatan/goresan/persetujuan PIC yang belum lengkap. Check-out tetap
  memerlukan tanda tangan yang sesuai isi laporan terbaru.
- Unduh/bagikan PDF bisa ditekan untuk mendapat penjelasan bila belum ada tanda
  tangan. PDF final tetap hanya tersedia setelah PIC tersimpan. Preview tidak
  digunakan untuk mengakali persyaratan tanda tangan.

Histori kunjungan/observasi/speedtest/foto lama tidak ditulis ulang. Agen tidak
mengubah isian produksi PGFC, membuat tanda tangan, atau melakukan check-out atas
nama pengguna; pemilihan isi konflik dan persetujuan PIC dilakukan pengguna.

## Web supervisor

- Menu **Hasil Maintenance**: semua laporan tersimpan termasuk draf yang belum
  dikirim, status pemeriksaan/pending dan alasan, ringkasan, teknisi serta akses
  detail foto/PIC/PDF. Filter periode/hotel/teknisi/status dan pencarian tersedia.
- Kartu Ringkasan menjadi tombol ke data terkait. Hasil selesai dihitung hanya
  ketika laporan approved dan work_status completed; approved tetapi pending
  tidak masuk sebagai maintenance selesai.
- Grafik distribusi status dan penugasan enam bulan menggunakan record tersimpan,
  tanpa data buatan. Klik status/bulan membuka hasil terkait. Grafik halaman
  Hasil Maintenance mengikuti filter hotel/teknisi/pencarian; pilihan status tetap
  dapat dipindah melalui grafik. Data belum ada ditampilkan nol/daftar kosong.
- Detail area supervisor membaca satu kolom gabungan Temuan dan Tindakan beserta
  format lama; kondisi good dengan catatan positif tidak dihitung temuan masalah.
- Navigasi hasil/detail/kembali, keyboard dan lebar layar kecil diuji. Halaman
  hasil supervisor tidak ditampilkan di navigasi teknisi.

## Verifikasi

- Frontend: 45 test, lint/typecheck/build dan APK Gradle lulus.
- Backend Python 3.12: 97 lulus, 33 test opt-in dilewati pada suite biasa.
- PostgreSQL terisolasi: 32 lulus, termasuk merge catatan lama, konflik nyata,
  radio terbaru, transaksi/versi dan replay UUID.
- Browser API/DB nyata: antrean offline lama, perubahan lokal lebih baru,
  perubahan server independen dan konflik teks nyata; pengguna memilih hasil
  perbandingan, lalu preview PDF, multi foto, PIC/retry respons hilang, PDF final
  dan check-out berhasil. Rekomendasi server independen tetap tersimpan.
- Browser memverifikasi pesan tombol tanda tangan/check-out/PDF yang belum
  memenuhi persyaratan benar-benar tampak di viewport; tidak sekadar muncul jauh
  di atas posisi scroll. Regresi profil, offline, XSS dan read-only lulus.
- Browser Web: kartu ringkasan, grafik status/bulan, filter, pencarian, perbedaan
  draft/pending/approved, detail/kembali serta responsive 360/390/768/1440 lulus.
- Image cocok dengan 45 file backend/Web yang diuji.
- Backup privat DB/foto:
  `/root/backups/hotel-maintenance/review-recovery-20261119T161501Z/`.
  Backup berhasil direstore; image diuji pada salinan dengan observasi lama,
  merge, replay, penolakan konflik, transfer, foto, PIC, check-out dan PDF.
- Seluruh fingerprint tabel produksi sebelum/sesudah identik, termasuk kolom
  profil akun. Tidak ada penulisan QA pada produksi. Health/DB/HTTPS dan asset Web
  baru diverifikasi setelah aktivasi.

## APK final

`artifacts/android/nusa-maintenance-1.7.0-debug.apk`, versionCode 10.
Alias `artifacts/android/hotel-maintenance-https-debug.apk` identik.
SHA-256: `8fc6e0949ba4e75fd4f232662c70411661dc7229d36b58fe90a23248066a7a4f`.
Sertifikat upgrade sama dengan 1.6.1, 12 file dist di APK cocok dengan build teruji.
Pasang sebagai update, jangan uninstall atau menghapus data perangkat agar draf
lapangan tetap tersedia. Uji fisik radio, pemilih foto dan share PDF pada HP tetap
perlu dilakukan; hasil browser tidak diklaim sebagai uji perangkat fisik.
