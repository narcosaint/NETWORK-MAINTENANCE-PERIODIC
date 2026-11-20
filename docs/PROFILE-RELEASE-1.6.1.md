# Rilis 1.6.1 — revisi UI dan profil teknisi

Diaktifkan 19 November 2026 atas persetujuan operator. Seluruh revisi Laporan,
Network Test, Review/PIC/check-out, logout dan PDF pada docs/UI-REVIEW-1.6.md ikut
rilis ini. Backend/Web aktif: `hotel-maintenance-api:profile-ui-20261119T152738Z`.
Schema: `0014_user_contact_profile`. Tidak ada perubahan jaringan/port; Compose
hanya mengganti tag image aplikasi.

## Profil

Menu Profil memiliki Nomor WhatsApp, Email kantor, Divisi, Wilayah kerja dan
Simpan Profil. Identitas/peran/status akun tetap dikelola supervisor melalui
mekanisme existing. Pengguna hanya dapat mengisi kontak untuk akunnya sendiri.
Data tersimpan di server sehingga tersedia saat berganti perangkat. Tidak ada
isian produksi yang ditebak atau diisi otomatis.

Draf profil disimpan per akun/server di perangkat ketika diisi, tetap tersedia
saat offline/logout, dan dikirim hanya saat Simpan Profil. Sinkronisasi memakai
versi: konflik menampilkan data server untuk dibandingkan; pengguna dapat
mempertahankan draf setelah review atau memakai isian server. Endpoint profil
tidak dapat mengubah username/nama/peran/password/status akun atau memilih ID
akun lain. Nomor WA dan email divalidasi; profil tidak membuka data kontak ke
akun lain melalui daftar pengguna atau /auth/me.

Migration hanya menambah users.contact_profile JSON nullable tanpa DEFAULT atau
backfill. SQL direview dan diverifikasi offline sebelum uji PostgreSQL dan
penerapan. Lihat docs/reviews/USER-PROFILE-0014.md. Kolom tambahan dapat diabaikan
binary sebelumnya; rollback aplikasi tidak boleh menghapus kolom/data profil.

## Verifikasi dan data produksi

- 44 test frontend; lint/typecheck/build/Gradle lulus.
- 96 test backend Python 3.12 lulus; 32 opt-in dilewati pada suite biasa.
- 31 test PostgreSQL terisolasi lulus, termasuk upgrade dari 0013 dengan data akun
  lama tetap identik, profil akun sendiri dan konflik versi.
- Browser API/DB nyata: profil offline → buka ulang → simpan → roundtrip server,
  isolasi akun dan konflik dua sesi dengan review eksplisit; lalu multi foto,
  catatan, tanda tangan PIC/retry tanpa duplikasi, PDF dan check-out lulus.
- Regresi Android legacy/offline/XSS/read-only/logout/responsive lulus. Regresi
  Web logout dan HTTPS LibreSpeed budget sebelumnya tetap berlaku; worker tidak
  diubah pada penambahan profil.
- Image rilis cocok dengan 60 berkas source backend/Web/migration teruji.
- Backup DB/foto privat:
  `/root/backups/hotel-maintenance/profile-ui-20261119T152738Z/`.
  Restore, migration dan alur API aktual image diuji di salinan terisolasi sebelum
  migration produksi. QA profil/foto/speedtest/PIC hanya ditulis ke salinan.
- Fingerprint seluruh kolom lama setiap tabel produksi identik setelah migration;
  seluruh 22 lokasi, kunjungan, hasil pengukuran dan foto dipertahankan. Kolom baru
  dikecualikan hanya dari perbandingan kolom lama users, tanpa mengabaikan isian
  akun/password/peran/status semula. Tidak ada data produksi yang dihapus.
- Health aplikasi/DB, TLS publik, asset Web versi baru dan endpoint profil yang
  wajib autentikasi diverifikasi setelah aktivasi.

## APK final

`artifacts/android/nusa-maintenance-1.6.1-debug.apk`, versionCode 9.
Alias `artifacts/android/hotel-maintenance-https-debug.apk` identik.
SHA-256: `73313e76d5a8819c7f8055ddb3ac03804cbb399ceafdef1c40e9accc901e2522`.
Sertifikat sama dengan 1.5.0; seluruh 12 berkas dist di paket cocok. Pasang sebagai
update tanpa uninstall untuk mempertahankan draf. Kandidat 1.6.0 bukan APK final.

Pembacaan radio Wi-Fi, pilihan beberapa foto pada Android dan share PDF tetap
memerlukan uji pada HP fisik. Pengujian browser memakai radio/binding fixture;
tidak mengklaim telah melakukan pengukuran Wi-Fi fisik dari perangkat operator.
