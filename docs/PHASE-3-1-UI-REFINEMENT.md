# Phase 3.1 — Android UI refinement

Implementasi lokal 13 November 2026, mengikuti review screenshot Phase 3 dan
ROADMAP-V2. Perubahan terbatas pada presentasi React/CSS, pengujian dan dokumentasi.

## Perubahan

- Status kunjungan, cache, penyimpanan draf dan kegagalan ditampilkan dalam satu
  `SyncPanel` ringkas. Detail persistence dapat dibuka melalui disclosure native
  (juga mendukung keyboard). Error server/storage dan perbedaan versi draf tampil
  di luar konten disclosure, sehingga tetap terlihat saat panel ditutup. Draf dan
  versi asalnya dipertahankan; tidak ada perubahan API atau cara sinkronisasi.
- Foto & Catatan dibagi menjadi tiga card: **Kondisi & Temuan** (lokasi, status,
  catatan, temuan), **Tindakan & Rekomendasi**, dan **Dokumentasi Foto** (kategori,
  caption, kamera/file picker, thumbnail). Field, permission edit, handler dan
  penyimpanan lokal existing dipertahankan. Banner sinkronisasi duplikat di form
  dihapus; status berada pada panel kunjungan.
- Layout shell memakai tiga baris: header, area konten yang bisa di-scroll, dan
  bottom navigation. Menu tidak lagi menjadi overlay fixed di atas form. Konten
  memiliki scroll padding, safe area dan pengembalian posisi scroll ketika pindah
  halaman. Area konten tetap berada di atas menu, termasuk pada viewport pendek.
- Review memiliki empat ringkasan: **Backbone Fiber Optic**, **Wireless Backbone**,
  **Local Area Network**, **Sampling Wi-Fi**. Data berasal dari laporan/evidence
  server; draf lokal tidak menaikkan progress. Nilai nol tetap ditampilkan, hasil
  format lama ditandai, missing tetap “Belum diperiksa”. LAN memakai seluruh lima
  item termasuk boolean false; sampling memakai aturan completion existing.
- Tema hijau/putih, border radius, touch target dan struktur navigasi dipertahankan.
  Tidak menambahkan pengukuran/grafik simulasi.

## Pengujian

Lulus:

- `npm run build --prefix android-app` — TypeScript strict dan build Vite.
- `npm run typecheck --prefix android-app`.
- `npm run lint --prefix android-app`.
- `npm test --prefix android-app` — 13 unit test existing.
- Browser suite `tests/browser/android_phase3_ui.py`, dengan semua fixture keamanan
  dan regresi Phase 3 tetap dipertahankan. Pemeriksaan tambahan mencakup satu panel
  sinkronisasi, expand/collapse, konflik server tetap terlihat saat collapsed,
  konflik versi aktual, tiga section form, empat ringkasan Review dan hasil aktual
  bernilai nol/negatif serta boolean false. Input XSS tetap dirender sebagai teks.
- Responsivitas 360/390/430/768px. Untuk setiap input/select/textarea/tombol foto,
  tes melakukan scroll dan focus lalu membandingkan bounding box dengan posisi
  bottom navigation. Tidak ada overlap atau horizontal overflow di area konten.
  Viewport 390×500 juga diuji sebagai simulasi ruang layar berkurang; ini bukan
  pengujian keyboard pada perangkat Android fisik.

Perintah browser dengan lokasi artifact baru:

```sh
ANDROID_UI_ARTIFACTS=artifacts/phase3-1 \
LD_LIBRARY_PATH=/tmp/hotel-browser-libs/root/usr/lib/x86_64-linux-gnu \
FONTCONFIG_FILE=/tmp/hotel-fonts.conf \
.venv/bin/python tests/browser/android_phase3_ui.py
```

Pengujian menggunakan build statis di localhost sementara, API intercept dan
fixture QA, tanpa koneksi database produksi atau server aplikasi existing.
Pustaka Chromium di `/tmp` mengikuti lingkungan pengujian yang sudah tersedia.
Tidak mengubah konfigurasi jaringan atau membuka port publik.

## Screenshot 390px

Semua screenshot 390×844, memakai fixture lokal. Bagian form yang panjang diambil
pada posisi scroll berbeda agar pengaturan section dan posisi menu terlihat:

- `artifacts/phase3-1/dashboard-390.png`
- `artifacts/phase3-1/sync-conflict-390.png`
- `artifacts/phase3-1/sampling-notes-390.png`
- `artifacts/phase3-1/sampling-actions-390.png`
- `artifacts/phase3-1/sampling-photos-390.png`
- `artifacts/phase3-1/review-390.png`
- `artifacts/phase3-1/review-pic-390.png`

Payload XSS terlihat sebagai teks di fixture; gambar foto adalah aset QA lokal.
Tidak ada fixture dimasukkan ke produksi. Screenshot Phase 3 sebelumnya tetap ada.

## Batas

Tidak mengubah backend, database, API client/kontrak, service native/storage,
Docker Compose, jaringan, deployment atau autentikasi. Tidak menerapkan migration.
Wi-Fi native, start LibreSpeed Android, PIC/signature dan fitur belum terintegrasi
Phase 3 tetap berstatus belum tersedia. Phase 4 tidak dikerjakan.

Build APK/perangkat fisik belum diverifikasi karena JDK/Android SDK tidak tersedia.
Sebelum build APK pada workstation Android, jalankan `npm run android:sync` seperti
panduan `android-app/README.md` untuk menyalin bundle UI terbaru ke host Capacitor.
