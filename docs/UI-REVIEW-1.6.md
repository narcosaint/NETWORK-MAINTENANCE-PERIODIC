> Revisi ini sudah dirilis bersama profil teknisi pada **1.6.1**.
> Backend/Web aktif; lihat [catatan rilis final](PROFILE-RELEASE-1.6.1.md).
> Bagian kandidat 1.6.0 di bawah adalah catatan sebelum persetujuan deployment.

# Revisi Laporan, Network Test, Review dan PDF — 1.6.0

Status: kandidat APK dan image selesai dibuat, belum deployment. Backend aktif
masih `hotel-maintenance-api:field-simple-20261119T100010Z`. Alias APK aktif
`hotel-maintenance-https-debug.apk` tetap 1.5.0 sampai pembaruan server disetujui.
Tidak ada migration, perubahan Compose/network atau perubahan data produksi.

APK: `artifacts/android/nusa-maintenance-1.6.0-debug.apk`, versionCode 8.
SHA-256: `3713acb6751fcfadab718b1a39ae7f9ff760b6c819a6016ba94f7acd39604192`.
Sertifikat sama dengan APK 1.5.0; seluruh 12 berkas dist di APK identik dengan
build teruji. Image kandidat: `hotel-maintenance-api:ui-review-20261119T151723Z`.
Semua 43 berkas backend/Web kandidat diverifikasi terhadap source teruji.

## Tampilan dan perilaku

- Laporan: tulisan template dihapus, judul Informasi Pelanggan disamakan dengan
  accordion lain. Backbone FO dan wireless tanpa input keterangan. Wireless:
  Signal Strength, Link Test Radio Download/Upload, Bandwidth Test Download/Upload.
  Hasil pekerjaan hanya ringkasan pemeriksaan, status, dan alasan saat pending.
- Network Test: tanpa penjelasan statis di bawah tombol Mulai; riwayat dilipat;
  Catat Gagal Uji dihapus dari UI. Wi-Fi Scanner selalu terbuka. Temuan dan Tindakan
  satu kolom dalam accordion tertutup, kondisi area dipilih terpisah sehingga
  kalimat positif tidak otomatis menjadikan area Perlu Perhatian. Status produksi
  historis tidak diubah otomatis. Catatan server lama tetap tersedia sebagai isi
  kolom gabungan. Foto memakai label Keterangan dan pemilih multi foto bertema.
  Simpan Hasil menyimpan catatan dan foto area ke server; kegagalan tetap menyisakan
  foto/draf yang belum terkonfirmasi di perangkat.
- Review: menampilkan isi laporan dan catatan area, kategori dokumentasi kapital,
  pemilih multi foto bertema, checkbox persetujuan kecil. Tidak ada tombol reload
  untuk review ulang atau kolom alasan GPS check-out. Tanda tangan menyinkronkan
  draf/foto lebih dahulu dan memvalidasi ulang kelengkapan serta digest laporan.
  Identitas/jabatan, goresan dan persetujuan PIC tetap wajib. Retry tanda tangan
  memakai UUID semula saat respons hilang; perubahan laporan membatalkan tanda
  tangan yang tidak lagi cocok. Check-out memvalidasi tanda tangan terbaru dan
  mengirim laporan; kegagalan GPS dicatat sebagai pengecualian otomatis yang jujur,
  tanpa koordinat buatan. Review read-only memakai laporan server yang disahkan.
- Semua textarea Android dan Web tidak dapat ditarik ukurannya.
- Profil memuat identitas akun, status, jumlah penugasan/lokasi, koneksi, versi dan
  informasi sinkronisasi. Saran tambahan untuk pengisian berikutnya: nomor WA,
  email kantor, divisi dan wilayah kerja; belum ditambahkan ke schema pengguna.
- Logout Web dan Android memakai dialog bertema, fokus awal pada batal, mendukung
  Escape; draf akun tetap tersimpan.
- PDF: `Nusa Maintenance-<nama lokasi>-<YYYY-MM>.pdf`; draf diberi penanda DRAF.
  Header logo+ikon, watermark transparan, wireless urut seperti form. Daftar
  Wi-Fi Scanner tidak dicetak; informasi jaringan yang terhubung, speedtest,
  foto yang dikirim dan persetujuan PIC tetap dicetak. Blok backbone tidak dipotong
  antarhalaman. Snapshot tanda tangan dan data lama tetap dipertahankan.

## Perbaikan penyimpanan

Observasi teks tidak menghapus pembacaan Wi-Fi yang tidak dikirim dalam request.
Null eksplisit tetap diperlakukan sebagai pengosongan, dan berbeda dari omission
untuk pemeriksaan UUID retry. Observasi baru menyimpan request asal sebagai
metadata internal; API lama tetap diterima, data historis tidak ditulis ulang.
Perubahan area lain tidak menyebabkan konflik palsu jika versi sesi area tujuan
masih sama. Transaksi tetap mengunci kunjungan, menaikkan versi dan menolak
perubahan bersamaan pada sesi yang sama. Draf dengan baseline catatan yang masih
sama boleh memakai versi sesi terbaru; UUID belum terkonfirmasi tidak diganti.
Konflik isi yang nyata tetap memerlukan review; tidak ditimpa otomatis.

## Verifikasi

- Lint, typecheck, build Web/Capacitor dan Gradle assembleDebug lulus.
- 44 test frontend lulus.
- 94 test backend Python 3.12 lulus; 30 test opt-in dilewati pada suite biasa.
- 29 test PostgreSQL terisolasi lulus; perubahan terakhir retry/omission diuji
  ulang khusus pada PostgreSQL, tanpa menyentuh database produksi.
- Browser: regresi Android legacy/read-only/offline/XSS/logout pada lebar
  360/390/430/768, navigasi/logout Web, Web→API→Android sampling, dan alur nyata
  multi foto→catatan→PDF draf→PIC→PDF final→check-out lulus. Hilangnya respons
  tanda tangan diuji tanpa duplikasi. Backend, DB dan radio fixture hanya QA.
- PDF diperiksa melalui ekstraksi teks, keberadaan gambar dan render visual.
  Contoh QA: `artifacts/completion/qa-signed-report.pdf`.
- Regresi worker LibreSpeed melalui HTTPS/CORS lintas origin lulus: upload
  sungguhan berhenti tepat pada budget QA 16 MiB dan hasil completed tersimpan.
  Radio/binding memakai fixture; tidak menggantikan uji HP.
- Tetap perlu uji radio, pemilih beberapa foto dan share PDF pada HP fisik.
  Hasil browser bukan klaim pengukuran Wi-Fi fisik.

Backend baru perlu diaktifkan bersama pembaruan APK untuk validasi kolom catatan
  gabungan. Sesuai AGENTS.md, persetujuan deployment dibutuhkan sebelum aktivasi;
  jangan mengganti alias APK aktif lebih dahulu. Saat disetujui, buat backup
  konsisten DB/foto privat, uji restore pada salinan, ganti image API saja, periksa
  health/HTTPS dan fingerprint data. Schema tetap 0013.
