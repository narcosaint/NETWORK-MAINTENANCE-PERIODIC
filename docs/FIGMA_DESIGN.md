# Desain visual Hotel Network Maintenance

File editable: https://www.figma.com/design/6ZO8RUdgiWNr0adMxffeIh
Frame awal Ringkasan: https://www.figma.com/design/6ZO8RUdgiWNr0adMxffeIh?node-id=2-822

Dibuat 13 November 2026 berdasarkan struktur UI existing, dengan palet hijau gelap,
putih dan font Inter. Terdapat 7 frame desktop (Ringkasan, Maintenance Hotel,
Detail Hotel, Detail Lantai, Detail Titik Sampling, Speedtest, Foto dan Catatan),
1 frame mobile Detail Titik, dan panduan Mulai di sini. Semua UI menggunakan layer
native editable, bukan screenshot; 220 node teks, nol image fill. Navigasi dan
statistik memakai instance Simple Design System dengan penyesuaian palet produk.
Prototype menghubungkan layar utama dan tab pengujian; tombol Tim Teknisi,
Template Checklist dan kontrol form adalah representasi visual, belum prototype
aplikasi lengkap. Data contoh hanya ada di Figma, tidak ditulis ke produksi.

Cara pakai: buka file, pilih frame lalu edit layer melalui panel Design. Gunakan
Present untuk mengecek navigasi. Kirim URL frame yang direvisi untuk diterapkan
ke frontend existing. Perubahan Figma tidak otomatis mengubah dashboard server.
Validasi: screenshot desktop/mobile diperiksa; audit seluruh frame tidak menemukan
children yang melewati batas tinggi parent dan memastikan layer teks editable.
