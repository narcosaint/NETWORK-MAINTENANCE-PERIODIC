# Branding Android — Nusa Maintenance 1.4.1

Artwork dari operator: `artifacts/design/ikon aplikasi.jfif`. Gambar berisi
logo utama di kiri dan ikon di kanan. Masing-masing dipotong dari artwork asli,
tanpa label presentasi; desain/warna asli dipertahankan. Provenance dan batas
crop dicatat pada `android-app/public/brand/SOURCE.json`.

- Logo utama: layar login, pada panel putih agar tulisan hijau tetap jelas.
- Ikon: header aplikasi dan favicon pratinjau web Android.
- Android: launcher legacy/round dan adaptive foreground untuk mdpi sampai
  xxxhdpi. Foreground diberi ruang aman untuk bentuk mask launcher.
- Splash: artwork ikon untuk orientasi portrait/landscape dan konfigurasi
  SplashScreen Android modern.
- Teks login memakai hijau gelap pada latar hijau muda agar tetap terbaca.

APK 1.4.1 versionCode 6 memakai applicationId dan sertifikat debug existing.
Perubahan khusus branding Android; tidak memerlukan update backend atau database.
Berkas logo/icon canonical berada di `android-app/public/brand/` dan ikut APK.

Verifikasi: build/typecheck, lint dan regresi browser 360/390/430/768 lulus.
Layar login dan logo diperiksa dari screenshot. Dimensi launcher di lima density,
padding foreground adaptive, 15 bitmap launcher dalam APK, signature upgrade,
versi dan seluruh aset web terverifikasi.

APK: `artifacts/android/nusa-maintenance-1.4.1-debug.apk`.
SHA-256: `0768d74d44d66d50e7be15ebefefca461f9f28ce5aa0981ff6885a7c61b6e4d7`.
Alias `hotel-maintenance-https-debug.apk` menunjuk rilis yang sama.
