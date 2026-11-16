# Hotel Network Maintenance

Project ini adalah aplikasi preventive maintenance
internet hotel berbasis Web dan Android.

## Referensi utama

Baca docs/ROADMAP-V2.md sebelum melakukan
perubahan fitur atau arsitektur.

## Arsitektur

- Backend: FastAPI
- Database: PostgreSQL
- Migration: Alembic
- Web: Gunakan framework existing
- Android: React + Capacitor
- Speedtest: LibreSpeed

## Prinsip

1. Jangan menghapus data produksi.
2. Jangan mengubah Docker/network tanpa izin.
3. Pertahankan kompatibilitas backend existing.
4. Gunakan template maintenance Nusanet.
5. Default 4 sampling per lantai.
6. Speedtest wajib pada setiap titik sampling.
7. Wi-Fi Analyzer menggunakan data Android asli.
8. Jangan menggunakan dummy pada database produksi.
9. Migration harus direview terlebih dahulu.
10. Setiap perubahan wajib diuji.

## Development Workflow

1. Audit source code.
2. Periksa dampak perubahan.
3. Implementasikan fitur sesuai fase roadmap.
4. Jalankan test yang relevan.
5. Laporkan perubahan.
6. Jangan deployment tanpa persetujuan.
