# Data pemeriksaan — bahan diskusi operasional

## Sudah tersedia

Inventaris perangkat memuat hotel, nama, jenis (router/switch/AP), serial, merek,
model, lokasi pemasangan, satu alamat IPv4/IPv6 manajemen, MAC address dan catatan.
Merek/model/lokasi/IP/MAC/catatan opsional; kosong disimpan NULL. Tidak ada nilai
contoh yang diisi otomatis. Jangan menyimpan password perangkat pada catatan.
Alamat IP adalah alamat perangkat, bukan hostname/URL/subnet; IPv6 disimpan dalam
bentuk ringkas. MAC memakai enam pasang heksadesimal, dinormalisasi huruf kecil
berpemisah titik dua. IP/MAC belum diberi constraint unik karena jaringan hotel
berbeda dapat memakai alamat privat yang sama.

Supervisor dapat menambah/mengubah detail inventaris. Kedua peran dapat membaca
inventaris sesuai kontrak API saat ini; teknisi hanya mengubah tugas miliknya.
Data inventaris terkini ditampilkan pada detail kunjungan. Snapshot pengajuan dan
keputusan menyimpan data saat itu; mengubah inventaris tidak menulis ulang
snapshot lama. PUT /devices/{id} adalah penggantian penuh: field opsional yang
tidak dikirim akan kosong. Aplikasi dashboard mengirim semua field pada form.

## Usulan checklist awal (belum dijadikan standar wajib)

| Perangkat | Topik yang bisa kita tentukan bersama |
|---|---|
| Router | Daya/suhu yang dapat diamati, kondisi kabel WAN/LAN, konektivitas, versi firmware, backup konfigurasi oleh operator berwenang |
| Switch | Daya/fan, kondisi port/uplink, konektivitas, status PoE bila tersedia, kerapian kabel dan label |
| Access point | Daya/PoE, kondisi pemasangan, uplink, SSID/BSSID, kekuatan sinyal per titik, konektivitas dan pengukuran kecepatan |

Saat ini jawaban checklist berupa baik/bermasalah/tidak berlaku serta catatan.
Nilai angka/jenis pengukuran terstruktur, ambang kelulusan, foto wajib per item dan
bukti tanda tangan akan ditambahkan pada modul berikutnya. Jangan menganggap
hasil uji kecepatan/sinyal tersedia otomatis pada versi web saat ini.

## Hal yang perlu diputuskan bersama sebelum penggunaan lapangan

- Field inventaris tambahan: firmware, nomor aset, lantai/ruang/rack terpisah,
  interface/IP lebih dari satu, PoE/VLAN atau data lain yang benar-benar dipakai.
- Daftar item wajib per jenis perangkat; apakah berbeda per hotel atau merek.
- Titik pengukuran (misalnya lobby, koridor, kamar) dan jenis koneksi yang diuji.
- Kriteria baik/bermasalah, batas sinyal/latensi/kecepatan yang disepakati per hotel.
- Bukti foto yang diperlukan, identitas PIC, dan kapan pengecualian boleh diterima.
- Prosedur tindakan teknisi jika perangkat bermasalah dan batas kewenangan perubahan.
- Kebutuhan offline: durasi tanpa jaringan, kapasitas foto, serta penyelesaian konflik.

Belum ada angka standar, template pemeriksaan atau data pengukuran yang dibuat
ke database utama. Template yang sudah dipakai tetap immutable; perubahan dibuat
sebagai template baru agar laporan sebelumnya konsisten.


## Cakupan yang sudah dikonfirmasi dari template PDF

Satu kunjungan/laporan mencakup satu hotel: router, switch, LAN dan sampling AP.
Teknisi memilih AP sampling secara manual berdasarkan lantai/topologi; jumlah
fleksibel. Contoh 4 kamar + 2 AP koridor tidak menjadi kuota wajib. Satu baris
lampiran mewakili satu AP yang diuji, dengan lantai dan identitas kamar/koridor.
AP inventaris yang tidak disampling tetap tidak diperiksa pada laporan tersebut.

FO dan wireless dapat dipakai sendiri-sendiri atau bersamaan, termasuk failover
atau bonding; hasil tiap koneksi dicatat terpisah. Rincian keputusan dan hal yang
masih perlu dibahas ada di TEMPLATE_MAPPING.md. Ini spesifikasi, belum perubahan
aplikasi yang sedang berjalan.

Bukti foto dikonfirmasi wajib untuk router/switch yang diperiksa dan setiap AP
sampling. AP yang tidak disampling tidak perlu difoto pada laporan itu. Form
sampling yang sama menyediakan foto AP, Wi-Fi analyzer (sinyal/channel dan
identitas radio) serta speedtest; bukti dikaitkan ke kunjungan/perangkat yang
tepat. Rincian ada di TEMPLATE_MAPPING.md. Modul ini belum diimplementasikan.
