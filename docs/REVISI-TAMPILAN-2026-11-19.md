# Revisi tampilan pengguna — 19 November 2026

Sumber revisi: artifacts/design/Draf-Tampilan-Nusa-Maintenance-Revisi.docx.
Perubahan diterapkan pada Android 1.2.0 (versionCode 3) dan backend pendukung.

## Diterapkan

- Branding NUSA MAINTENANCE, teks login/footer sesuai revisi, tombol Masuk,
  status Online/Offline, gradasi hijau dan navigasi tahapan bold.
- Label Network Test, Test per lantai, Test Area; titik ditampilkan sebagai area.
- Dua baris area awal, form nama tanpa AP/lokasi/alasan manual. Reason audit tetap
  dicatat otomatis sebagai tindakan penambahan oleh teknisi. Draf/kiriman lama
  dipertahankan, termasuk payload retry yang sudah dibekukan.
- Default API lantai baru 2; default field area 2; fallback UI 2. Existing target
  dan area nyata tidak dihapus. DDL historis/default database tidak dimodifikasi.
- Informasi pelanggan dilipat; field tampilan legacy, feedback dan pengecualian
  PIC dihapus dari form sesuai revisi, tetapi data lama tetap di payload/server.
- Link test radio memakai link_test_download_mbps/link_test_upload_mbps numerik
  nullable dalam JSON laporan. Nilai nol sah; angka negatif ditolak. String lama,
  TX/RX/CCQ dan LAN legacy tidak dibuang. Tidak memerlukan migration baru.
- Lokasi pada Foto & Catatan menjadi pilihan area yang menavigasi ke sesi yang
  benar; label menyertakan lantai untuk membedakan nama area yang sama. Input
  tinggal Temuan dan Tindakan, tombol simpan terletak paling bawah setelah foto.
  Data notes/recommendation/condition historis dipertahankan. Perubahan temuan
  memperbarui kondisi attention/untested tanpa membuat klaim pemeriksaan selesai.
- Checkbox kapasitas speedtest dihapus; tombol Mulai menjadi aksi eksplisit.
  Binding/cancel/kuota dan validasi hasil tetap ada, hasil disimpan per area.
- Karena pilihan AP pada form dihapus, area tanpa mapping mengidentifikasi AP
  dari BSSID aktual dan MAC inventaris hotel secara case-insensitive. Harus tepat
  satu AP cocok. Tidak membuat AP palsu atau menebak jika tidak dikenal/ambigu.
  Identitas AP disimpan di context run, snapshot historis tidak ditulis ulang.

Logo gambar baru belum diganti karena operator menyatakan akan mengirim terpisah.
Ikon existing dipertahankan sebagai placeholder. Radio/throughput HP tetap perlu
uji fisik. Foto per sesi/PIC/submit V2 tidak diklaim selesai.

## Verifikasi dan rilis

40 test frontend, 84 backend pada image Python 3.12, 24 PostgreSQL terisolasi,
regresi browser legacy/responsive serta Web→API→SQLite→Android lulus. Tes browser
mencakup field tersembunyi tetap utuh dalam payload, numerik link radio, dropdown
antar-area yang tidak memindahkan catatan, tombol simpan di bawah foto, retry UUID,
serta target area baru 2. APK build/lint/typecheck lulus.

Backend aktif: hotel-maintenance-api:ui-revisi-20261119T034713Z. Backup database/foto konsisten pada:
/root/backups/hotel-maintenance/ui-revisi-20261119T034713Z/.
Restore dan uji image pada salinan berhasil, seluruh fingerprint data produksi
identik sebelum update aplikasi. Schema tetap 0012; tidak ada migration produksi
baru atau data QA dimasukkan ke produksi. Health/API publik HTTPS lulus.

APK: artifacts/android/nusa-maintenance-1.2.0-debug.apk.

APK signature/versi/label dan seluruh aset dist terverifikasi. SHA-256:
`8ce7139988ab734769036840c24a8c779364f03f1237e36173fa19301e2b5c61`.

## Revisi lanjutan: koneksi Wi-Fi HP (APK 1.3.0)

Instruksi operator terbaru membatalkan kebutuhan identifikasi AP inventaris di
atas. Wi-Fi Analyzer membaca data Android, dan speedtest area memakai jaringan
Wi-Fi yang sedang tersambung pada HP. SSID, BSSID, band, RSSI, serta binding
awal/akhir tetap direkam; pergantian AP/band saat tes membuat hasil gagal.
Tidak memerlukan pengisian MAC, pemetaan AP, atau pembuatan perangkat otomatis.
Alur tambah area memeriksa kapabilitas server tanpa mengambil inventaris.

Run area baru mengacu langsung ke sampling_sessions melalui migration 0013.
Run lama, API perangkat dan data Backbone/LAN tetap dipertahankan. Review SQL
dan dampak pemulihan ada di docs/reviews/PHONE-NETWORK-0013.md.

Verifikasi: 86 backend lulus (26 pengujian PostgreSQL dilewati pada suite
biasa); suite PostgreSQL terisolasi 25 lulus. Frontend 40 lulus; build, lint,
regresi browser dan signature/versi/aset APK lulus. Kasus tanpa inventaris AP
menguji transfer dan penyimpanan hasil per area. Uji radio/throughput fisik
pada HP tetap harus dilakukan, bukan disimpulkan dari fixture.

APK 1.3.0 versionCode 4: artifacts/android/nusa-maintenance-1.3.0-debug.apk.
SHA-256: `651baba8c6bc1046fec96aacd220ffbd470a29c75dd871ee45fbc28092380959`.

## Pengukuran koneksi HP — APK 1.3.0

Backend aktif: `hotel-maintenance-api:phone-network-20261119T042217Z`; schema `0013_phone_network_runs`.
Backup database/foto privat: `/root/backups/hotel-maintenance/phone-network-20261119T042217Z`. Restore terisolasi, upgrade,
alur API tanpa AP inventaris, dan transfer byte sungguhan pada salinan lulus.
Seluruh baris produksi dengan kolom semula memiliki fingerprint identik
sebelum/sesudah migration. Tidak ada data QA di produksi. Health/API HTTPS
domain dan IP publik lulus. APK 1.3.0/code4 sudah diverifikasi signature/aset.
Lihat docs/reviews/PHONE-NETWORK-0013.md untuk batas rollback.
