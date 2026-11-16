# Hotel Maintenance — Android UI (Phase 3)

Aplikasi React + TypeScript + Capacitor terpisah dari web existing. Source native
Android tersedia di `android/`. Tidak mengubah backend, PostgreSQL, migration,
Docker, jaringan atau deployment. Referensi lengkap: `../docs/PHASE-3-ANDROID-UI.md`.

## Menjalankan source

Gunakan Node 22.13+ (diverifikasi pada 22.23.5) dan npm. Dari direktori ini:

```sh
npm ci
npm run typecheck
npm run lint
npm test
npm run build
```

Tidak ada akun demo atau API produksi bawaan. Login memakai username/password akun
teknisi existing. Password dan token hanya di memori; reload/cold start memerlukan
login ulang. Draf tetap tersimpan per server/akun/kunjungan di IndexedDB.

Untuk development browser, salin `.env.example` menjadi `.env.local`, isi
`DEV_API_TARGET` dengan origin backend development yang disetujui, lalu:

```sh
npm run dev
```

Vite hanya bind ke `127.0.0.1`. Browser memakai `/api` melalui proxy development;
backend tidak perlu mengubah CORS. Tanpa target, data tidak tersedia. `npm run build`
menghasilkan asset statis; `DEV_API_TARGET` hanya berlaku saat development,
bukan konfigurasi API untuk APK. Uji otomatis memakai intercept fixture, tanpa
menulis ke backend nyata.

## Build APK debug

Host Android sudah dibuat; jangan menjalankan `cap add android` lagi.
Persiapkan JDK 21, Android SDK 36, platform-tools dan Android Studio kompatibel
Capacitor 8. Gradle wrapper disertakan (8.14.3); konfigurasi SDK berasal dari
`android/variables.gradle`. Detail resmi:
[Environment](https://capacitorjs.com/docs/getting-started/environment-setup),
[Android](https://capacitorjs.com/docs/android),
[workflow](https://capacitorjs.com/docs/basics/workflow).

1. Isi `VITE_API_URL` di `.env.local` dengan origin HTTPS backend existing, misalnya
   format `https://<server-resmi>`. Ini konfigurasi publik, bukan secret. Alternatif:
   isi Alamat server di halaman login APK. Tidak boleh menyertakan username,
   password, path, query atau token di URL. Host memakai asset lokal, bukan remote
   `server.url`. Cleartext/mixed-content dinonaktifkan.
2. Atur `JAVA_HOME`, `ANDROID_HOME`, dan `android/local.properties` sesuai mesin
   build lokal (jangan commit path SDK atau keystore).
3. Jalankan:

```sh
npm ci
npm run android:sync
cd android
./gradlew assembleDebug
```

Hasil: `android/app/build/outputs/apk/debug/app-debug.apk`.
Buka project native dengan `npm run android:open` jika memakai Android Studio.
Instal secara manual pada emulator/perangkat yang disetujui:

```sh
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

Perintah `adb` di atas dijalankan dari direktori `android-app`, setelah kembali
keluar dari `android/`. Build release/signing/Play Store tidak dikerjakan. Keystore,
password signing dan konfigurasi perangkat bukan bagian source.

**Status verifikasi environment saat ini:** build frontend dan `cap sync android`
lulus. JDK/Android SDK/emulator tidak tersedia di server pengembangan ini; APK belum
dibangun atau diuji pada Android fisik. Panduan di atas belum dianggap bukti native
build lulus.

## Integrasi dan batas Phase 3

- API client terstruktur: login/me/logout, semua halaman daftar hotel/penugasan,
  detail kunjungan, check-in GPS dan PUT laporan menggunakan `expected_version`.
  Request Android memakai CapacitorHttp native dengan timeout dan tanpa redirect;
  browser memakai fetch/proxy. Tidak mengganti konfigurasi backend/CORS/TLS.
- GPS plugin disiapkan dan dipanggil saat pengguna memilih check-in. Tidak ada
  koordinat default. Penolakan izin tampil sebagai error; pengecualian GPS wajib
  alasan dan memakai kontrak backend existing.
- Kamera plugin dan file picker disiapkan. Blob, kategori, caption, timestamp dan
  point ID disimpan lokal. Maksimum 10 foto/titik, 10 MiB/foto JPEG/PNG/WebP.
  Foto lokal belum memenuhi kewajiban foto server. Native kamera/GPS masih perlu
  uji perangkat setelah APK tersedia.
- Laporan Nusanet dapat disimpan ke server secara manual. Semua field report
  existing, termasuk format lama, dipertahankan. SLA/conformity ditentukan backend.
  HTTP 409 mempertahankan draf dan versi asal; tidak ada rebase atau overwrite
  otomatis. Konflik ditinjau melalui Web Dashboard, salinan draf Android tetap ada.
- Catatan/foto dan cache kunjungan dapat dipakai offline dalam sesi aktif. Tidak
  ada auto-sync, background sync atau cold-start login offline. Tidak memodifikasi
  IndexedDB web; konfigurasi lantai lokal web tidak otomatis masuk aplikasi ini.
- Default empat target per lantai dari AP kunjungan; placeholder bukan AP/record
  server dan tidak dapat memperoleh hasil pengukuran. Master lantai/titik backend
  belum tersedia. Lokasi AP existing tetap dibaca sebagai histori.
- `WifiService` adalah kontrak typed untuk connection/scan native. Implementasi
  Phase 4 belum dibuat; UI menampilkan “Belum tersedia”, tanpa SSID/RSSI/grafik palsu.
- `LibreSpeedService` adalah interface Phase 5; start dinonaktifkan. Riwayat run AP
  server dapat dibaca, dipisahkan dari pengukuran aktif. Tidak ada tes jaringan
  dijalankan atau satu run dibagikan untuk empat target.
- Review merangkum hasil server dan temuan lokal dengan label terpisah. Native
  submit V2, dokumentasi server, persetujuan/signature PIC dan PDF belum tersedia;
  gunakan workflow existing di Web untuk operasi yang sudah didukung.

## Struktur

- `src/services/api.ts`: API, pagination, timeout, 401/409 dan origin validation.
- `src/services/storage.ts`: IndexedDB akun/server/visit, antrean persistence.
- `src/services/native.ts`: GPS/kamera dan interface Wi-Fi native.
- `src/services/librespeed.ts`: boundary pengujian Android, tanpa simulasi.
- `src/components/`: header, bottom navigation, field, card, progress dan sync status.
- `src/pages/`: login, form Nusanet, workspace hotel/lantai/review, detail sampling.
- `src/domain.ts`: aturan evidence sampling dan kompatibilitas payload.
- `tests/domain.test.ts`: unit test kontrak dan aturan evidence.
- `../tests/browser/android_phase3_ui.py`: integrasi UI dengan fixture lokal.

## UI refinement Phase 3.1

Panel sinkronisasi terpadu, tiga section Foto & Catatan, bottom navigation tanpa
overlay, dan empat ringkasan Review tersedia di source terbaru.
Lihat [hasil pengujian dan screenshot Phase 3.1](../docs/PHASE-3-1-UI-REFINEMENT.md).
Jalankan `npm run android:sync` sebelum build APK untuk menyalin bundle UI terbaru.
