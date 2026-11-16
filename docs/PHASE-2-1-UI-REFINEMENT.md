# Phase 2.1 — UI/UX Refinement

Implementasi lokal: 13 November 2026. Acuan: ROADMAP-V2, hasil Phase 2,
permintaan refinement dan `docs/design/hotel-maintenance-ui-reference.png.png`.

## Perubahan

- Dashboard mempertahankan empat statistik dan kartu lantai expandable. Penjelasan
  teknis progress dipindah ke disclosure “Detail progress & sumber data”.
- Badge “Perubahan belum disinkronkan” untuk konfigurasi/draf/foto lokal, dengan
  detail penyimpanan lokal yang dapat dibuka. Ketika belum ada perubahan lokal,
  labelnya “Penyimpanan lokal”. Error penyimpanan tampil di luar disclosure dengan
  role alert dan label “Gagal menyimpan perubahan”, termasuk setelah render ulang.
  Sinkronisasi server belum tersedia; online bukan bukti draf sudah terkirim.
- Navigasi mobile memakai hamburger dan drawer dengan backdrop, Escape, penutupan
  saat memilih menu, pengembalian fokus dan pembatasan fokus keyboard di drawer.
  Sidebar tertutup inert; aturan peran existing tetap digunakan.
- Form tambah lantai/target hanya tampil di Data Hotel > Detail Hotel > Lantai,
  dengan label lokal/belum tersinkronisasi. Detail lantai maintenance menyediakan
  tombol ke pengaturan tersebut. Key, format dan fungsi persistence IndexedDB
  existing dipertahankan; tidak ada migrasi, penghapusan atau konversi data lokal.
- Empat kartu pemeriksaan: Backbone Fiber Optic, Wireless Backbone, Local Area
  Network, Sampling Wi-Fi. Status berasal dari report/result/run server. Missing
  menampilkan “Belum diperiksa”. Catatan atau SLA saja bukan bukti pengukuran.
  Nol pengukuran tetap sah. Conformity tersimpan menentukan sesuai/tidak sesuai;
  tanpa conformity, pengukuran hanya berlabel tersimpan. LAN memperlihatkan hasil
  parsial/tersimpan/perlu perhatian berdasarkan field aktual, termasuk boolean.
  Sampling tetap memakai aturan evidence Phase 2, bukan status draf lokal.
- Grid statistik dan pemeriksaan dua kolom pada mobile, spacing header diringkas,
  badge membungkus teks, tombol minimum 44 px dan tema hijau tua/putih dipertahankan.
- Nama hotel/lantai/titik dan catatan di-escape sebelum masuk template HTML;
  feedback dinamis memakai textContent. Fixture keamanan lama tetap ada.

## Verifikasi

47 test backend lulus:

```
.venv/bin/python -m pytest -q --ignore=backend/tests/test_staging.py --ignore=backend/tests/test_postgres.py
```

Test PostgreSQL/staging opt-in tidak dijalankan. Test backend memakai fixture
terisolasi. Test migration existing hanya menghasilkan SQL offline; tidak ada
migration diterapkan ke database.

Tiga suite browser lulus dengan server statis localhost sementara dan API
intercept/fixture, tanpa akses database produksi:

- `tests/browser/dashboard_v2_ui.py`: evidence dan missing/zero values, status
  backbone, exclusion draf lokal, disclosure, form Nusanet/validasi/save payload
  ke fixture, screenshot, serta 360/390/430/768/1440 px tanpa horizontal overflow.
  XSS hotel/lantai/titik dengan img onerror dan script, serta catatan dengan
  penutup textarea, tampil sebagai teks tanpa eksekusi atau node injeksi.
- `tests/browser/hotel_navigation_ui.py`: semua menu supervisor dapat dipilih lewat
  drawer pada 360/390/430 px, drawer menutup setelah pilihan, Escape/focus trap,
  pembatasan peran teknisi, histori legacy, inventaris, tab/keyboard, filter periode,
  konfigurasi lantai/default empat dan perubahan target lokal.
- `tests/browser/sampling_ui.py`: navigasi sampling, catatan/foto offline, reload,
  isolasi akun, target dikurangi tetap mempertahankan titik berdraf, storage failure
  terlihat tanpa membuka disclosure dan setelah render ulang, recovery, native
  unavailable, serta lebar 360/390/768/1440 px.

Browser memakai pustaka Chromium/font existing di `/tmp`; tidak ada instalasi
sistem atau perubahan Docker/network. Pengujian perlu izin menjalankan browser
serta server fixture localhost di luar sandbox. Server ditutup setelah tes.

Screenshot terbaru (fixture QA, termasuk teks keamanan yang sengaja dipertahankan):

- `artifacts/phase2-1/dashboard-1440.png`
- `artifacts/phase2-1/dashboard-390.png`

Kedua ukuran diperiksa secara visual: warna, statistik, status, whitespace,
expandable floor, pembungkusan badge dan layout mobile. Tidak ada grafik atau
hasil pengukuran simulasi di fitur aplikasi.

## Batas perubahan

Tidak mengubah backend, API, autentikasi, form Laporan Utama Nusanet, database,
file migration, Docker Compose, konfigurasi jaringan atau deployment. Tidak
melanjutkan Phase 3. Status kartu merupakan ringkasan bukti tersimpan, bukan
validasi kelengkapan submit atau approval/PIC baru. Master dan draf tetap lokal;
Phase 2.1 tidak menambahkan sinkronisasi atau pengukuran native.
