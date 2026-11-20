# Pembaruan Web Nusa Maintenance

Instruksi operator: samakan logo/tulisan Web dengan Android dan hapus menu
Template Checklist. Logo utama dan favicon menggunakan PNG canonical dari
android-app/public/brand, berasal dari artwork operator.

Login, sidebar, dialog, judul tab dan footer memakai Nusa Maintenance; login
menggunakan palet hijau muda dan slogan Android. Label lokasi menggunakan area,
keterangan usang tentang belum tersedianya review PIC/PDF diperbarui, serta
keterangan sesi mengacu ke Wi-Fi HP. Menu Template Checklist dihilangkan untuk
supervisor dan teknisi. Render halaman template lama diarahkan ke Ringkasan.
Data template, checklist, API legacy dan riwayat tetap dipertahankan. Tidak ada
penghapusan database atau migration. Cache-buster aset diperbarui.

Verifikasi: test aset/security header, sintaks JavaScript, browser navigasi
supervisor/teknisi tanpa menu template, tab/breadcrumb, keyboard, responsivitas,
dashboard, sampling/offline, serta Web→FastAPI→SQLite→Android lulus. Screenshot
login tersedia di artifacts/web/nusa-login-desktop.png.

Aktif di https://maintenance.inisaja.id. Image: `hotel-maintenance-api:web-branding-20261119T063733Z`.
Backup database/foto: `/root/backups/hotel-maintenance/web-branding-20261119T063733Z`. Restore dan QA pada
salinan lulus; fingerprint seluruh data produksi tidak berubah. Schema tetap
0013. Pengecekan HTTPS publik memastikan title/logo/login baru, PNG identik
dengan Android, sidebar tanpa menu template, dan layout 390/1440 tanpa overflow.
