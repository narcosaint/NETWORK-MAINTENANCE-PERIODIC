# Penyelesaian laporan area, PIC dan PDF — APK 1.4.0

Instruksi operator: selesaikan satu alur utuh sebelum meminta pemasangan APK lagi.
Cakupan rilis ini: dokumentasi area/infrastruktur, review bukti, persetujuan PIC,
check-out/submit, revisi supervisor, PDF dan riwayat laporan. Tidak mengubah
koneksi Wi-Fi HP menjadi inventaris AP. Backbone FO, wireless dan LAN tetap ada.

## Penyimpanan dan kompatibilitas

Tidak membutuhkan migration. Bukti memakai event log HotelVisitEvent existing:
`evidence_added` menyimpan metadata foto dan hash berkas pada volume foto privat;
`pic_signed` menyimpan snapshot isi laporan, SHA-256, nama/jabatan PIC, waktu server,
persetujuan dan goresan ternormalisasi. UUID event adalah kunci retry. Tidak ada
base64 foto atau token transfer tersimpan di event. Foto dinormalisasi dan disimpan
secara eksklusif, fsync sebelum commit; gagal commit membersihkan berkas baru.

Event hanya ditambah. Foto/snapshot terdahulu tidak ditulis ulang. Tanda tangan
terikat tepat pada snapshot, bukan hanya nama PIC. Perubahan isi, cakupan, hasil,
foto, atau permintaan revisi supervisor memerlukan persetujuan PIC baru. Replay
signature mempertahankan request asli; kiriman berbeda dengan UUID sama ditolak.
Foto dari draf APK lama dipetakan dari label Indonesia ke kategori API, termasuk
retry ketika respons hilang. Berkas diakses dengan otorisasi kunjungan.

Endpoint legacy tetap ada. Submit V2 mengalihkan validator ke pemeriksaan area;
submit legacy tetap memakai aturan lama. Setiap area memerlukan observasi dan
speedtest sendiri: pengukuran sukses harus memiliki transfer teramati, koneksi
awal/akhir dan binding sama melalui HTTPS; gagal uji harus beralasan dan memiliki
tindakan. Validasi ini tidak mengklaim attestation radio dari server. Kebijakan
foto dan target area snapshot wajib dipenuhi. Foto lokal belum dihitung lengkap.

## Alur pengguna

1. Check-in; simpan laporan utama dan hasil tiap area.
2. Ambil foto AP/area melalui halaman area; tambah dokumentasi utama di Review.
3. Kirim setiap foto lokal ke server. Draf tetap ada sampai penerimaan server.
4. Review menampilkan daftar kekurangan; draf lokal memblokir tanda tangan.
5. Buka draf PDF bersama PIC, isi nama/jabatan, goreskan tanda tangan dan centang
   persetujuan. Saat offline draf PIC tetap tersimpan, submit memerlukan server.
6. Check-out memakai GPS atau alasan pengecualian; laporan menjadi Perlu Review.
7. Supervisor meninjau hasil/foto/PIC di Web lalu menyetujui atau meminta revisi.
8. Unduh/bagikan PDF dari Android atau Web. PDF menyatakan status supervisor
   terpisah dari tanda tangan PIC. Salinan PDF terakhir dapat dibuka offline
   dengan penanda bahwa perubahan server belum diperiksa.

PDF memakai struktur formulir Nusanet: pelanggan, backbone FO, wireless, LAN,
ringkasan, tiap lantai/area, SSID/BSSID/RSSI/frekuensi/channel, scan tersimpan,
seluruh percobaan speedtest, download/upload/ping/jitter, server/waktu/alasan
kegagalan, foto, temuan/tindakan serta PIC. Angka kosong tidak diganti dummy.
Foto asli dipertahankan; salinan untuk PDF diperkecil agar laporan tidak berat.
Goresan PIC adalah persetujuan laporan, bukan sertifikat elektronik.

## Pengujian

API integration menguji transfer aktual pada fixture terisolasi, foto/replay,
ACL lintas teknisi, blank signature, perubahan isi yang membatalkan signature,
file bukti hilang, submit/approval, revisi/resign, serta ekstraksi teks PDF untuk
FO/wireless/LAN/area/PIC. PostgreSQL menguji alur yang sama pada schema disposable.
Browser memakai FastAPI dan SQLite nyata: foto area dengan label APK lama,
dokumentasi utama, draf PDF, canvas PIC, kehilangan respons/retry tanpa duplikasi,
PDF final, offline cache, check-out, dan layar 360/390/768. Tes radio/throughput
fisik dan intent bagikan pada perangkat Android tidak disimpulkan dari fixture.

Aktivasi server hanya setelah semua pengujian lolos, backup database/foto,
restore terisolasi dan QA image selesai. Semua data uji hanya pada salinan.

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
