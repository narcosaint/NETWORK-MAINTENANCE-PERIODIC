# Pemetaan template maintenance — draf untuk ditinjau

Sumber lokal, masing-masing satu halaman:

- `[NEW] Form Maintenance Periodik - FAVE HOTEL.pdf`
- `[NEW] Form Maintenance Periodik - LAMPIRAN1.pdf`

Kedua halaman telah dibaca sebagai teks dan diperiksa secara visual. File asli
utuh. Dokumen ini adalah analisis kebutuhan, bukan perubahan schema/API/UI atau
pengisian template/data ke produksi.

## Kesimpulan bentuk laporan

Form utama memuat identitas pelanggan/lokasi, backbone, LAN, hasil pekerjaan,
feedback/solusi serta tiga pihak penandatangan. Lampiran memuat 50 baris
lantai/access point dan pengukuran dua band. **Dikonfirmasi pengguna:** satu kunjungan menghasilkan satu laporan hotel yang
mencakup router, switch, jaringan lokal dan sampling beberapa AP. Bukan satu
laporan untuk setiap perangkat. Inventaris AP dapat lebih banyak daripada AP
yang diuji; AP yang tidak dipilih untuk sampling tidak dianggap gagal, lulus,
atau sudah diperiksa. Aplikasi saat ini masih per perangkat sehingga perlu
penyesuaian alur hotel dengan data lama tetap dipertahankan.

## Keputusan pengguna tentang cakupan dan sampling

- Sampling dipilih teknisi secara manual; jumlahnya fleksibel menurut hotel,
  lantai dan topologi. Contoh satu lantai berisi 26 kamar dengan satu AP per
  kamar: teknisi boleh memilih 4 AP kamar dan 2 AP koridor jika tersedia.
  Angka 4+2 bukan kuota wajib dan tidak dibuat sebagai sampling otomatis.
- Satu baris lampiran adalah satu AP yang benar-benar diuji. Beberapa baris
  berurutan dapat berada pada lantai yang sama; misalnya baris 1–6 di lantai
  26 mencatat enam AP sampling di lantai tersebut. Kolom No adalah urutan baris,
  bukan nomor lantai atau nomor kamar.
- Catat lantai dan identitas/lokasi AP (nomor kamar atau nama koridor/titik)
  agar sampel bisa ditelusuri. Nama AP dan lokasinya dibekukan dalam snapshot
  laporan. Inventaris seluruh AP terpisah dari hasil sampling kunjungan ini.
- Struktur lokasi/topologi tidak mengasumsikan satu AP per kamar pada semua
  hotel. Jumlah kamar/AP dan ketersediaan AP koridor berbeda menurut hotel.
- Backbone FO dan wireless bersifat independen: salah satu atau keduanya dapat
  dipakai. Jika keduanya ada, perannya dapat berupa failover atau bonding.
  Jangan memaksakan fiber sebagai utama atau wireless selalu sebagai backup.
  Simpan peran koneksi yang dipilih dan hasil pengukuran masing-masing terpisah.
- Cabang koneksi yang tidak dipakai diberi status tidak digunakan, bukan angka
  nol. Sampling yang tidak dilakukan tidak boleh ditampilkan sebagai hasil uji.


## Pemetaan form utama

| Bagian PDF | Data yang dibutuhkan | Bentuk penyimpanan yang diusulkan |
|---|---|---|
| Tanggal | Tanggal kunjungan lokal hotel | Tanggal laporan dan timezone hotel; waktu transaksi server tetap UTC |
| Informasi pelanggan | Nama pelanggan/perusahaan, lokasi hotel, alamat, nama PIC, kontak PIC | Pisahkan pelanggan/perusahaan dari nama hotel; ambil master lalu snapshot pada laporan |
| Fiber Optic | Service Agreement (Mbps), hasil speedtest (Mbps), sesuai/tidak sesuai | Nilai angka dan keputusan kesesuaian; kriteria kesesuaian perlu disepakati |
| Wireless backbone | Signal Strength (dbm), TX/RX Rate (Mbps), Link Test/CCQ (%), hasil speedtest (Mbps) | Pengukuran backbone terpisah dari sinyal Wi-Fi AP; raw value dan sumber/waktu pengukuran |
| LAN Wire | Konektor LAN Router normal/tidak normal; konektor LAN Switch normal/tidak normal; catatan | Hasil pemeriksaan dengan referensi perangkat, bukan satu nilai untuk seluruh inventaris |
| Wireless/Hotspot | Signal Test poor/good; blank spot tidak ada/ada; hotspot tidak ada/ada; catatan | Enum sesuai makna asli, terpisah dari jawaban generik baik/bermasalah |
| Summary/Result | Ringkasan temuan dan hasil tindakan | Teks laporan kunjungan |
| Time | Waktu tiba, selesai, durasi | Waktu server check-in/out; durasi turunan. Revisi laporan tidak mengubah waktu fisik kunjungan |
| Work Status | Selesai atau tidak selesai/pending, alasan pending | Hasil pekerjaan operasional, terpisah dari status review/approval |
| Feedback Customer | Feedback pelanggan | Teks, identitas pencatat dan waktu |
| Solusi | Solusi/tindak lanjut | Teks; bila pending, perlu keputusan jadwal/tugas tindak lanjut |
| Engineer | Nama lengkap dan tanda tangan | Identitas teknisi serta bukti/pernyataan tanda tangan |
| Supervisor/Manager | Nama lengkap dan tanda tangan | Reviewer supervisor dan bukti/pernyataan persetujuan |
| Customer | Nama lengkap dan tanda tangan | Identitas PIC/customer serta bukti/pernyataan persetujuan |

Nama perusahaan dan alamat yang tercetak pada contoh tidak dijadikan nilai
bawaan untuk hotel lain. PIC/kontak perusahaan belum tersedia pada master hotel
saat ini; jangan memasukkan data contoh otomatis ke produksi.

## Nilai rekomendasi yang benar-benar tercetak

| Pengukuran wireless backbone | Poor | Good | Very Good |
|---|---|---|---|
| Signal Strength | < -80 | -60 s/d -80 (urutan pada PDF) | > -60 |
| TX/RX Rate (Mbps) | < 12 | 12 s/d 48 | > 48 |
| Link Test/CCQ (%) | < 40 | 40 s/d 80 | > 80 |

Ini referensi dari dokumen, belum aturan yang diaktifkan dalam aplikasi.
Jika disetujui, range signal tengah dapat direpresentasikan -80 sampai -60
inklusif; batas TX/RX 12/48 dan CCQ 40/80 perlu ditegaskan. Klasifikasi backbone
ini tidak otomatis diterapkan ke sinyal AP dalam lampiran.

Service Agreement/speedtest hanya menampilkan satu angka Mbps; PDF tidak
menentukan download/upload/latency, endpoint server maupun persentase toleransi
untuk keputusan sesuai/tidak sesuai. TX/RX Rate ditulis dalam satu field, sehingga
perlu konfirmasi apakah dua arah harus dicatat terpisah. Angka tidak boleh
menggantikan pengukuran yang belum dilakukan.

## Pemetaan lampiran AP

| Kolom PDF | Data yang diusulkan |
|---|---|
| No | Nomor urut tampilan/ekspor, bukan ID perangkat |
| Lantai | Lokasi/lantai pengukuran; bisa terkait lokasi inventaris AP |
| Access Point | Referensi AP dan snapshot nama/identitas |
| Signal (db), 2.4Ghz | Nilai pengukuran band 2,4; unit/sumber perlu dikonfirmasi |
| Signal (db), 5.8Ghz | Nilai pengukuran band bertuliskan 5,8; unit/label perlu dikonfirmasi |
| Bandwidth Test (Mbps), 2.4Ghz | Hasil bandwidth band 2,4; jenis download/upload perlu ditetapkan |
| Bandwidth Test (Mbps), 5.8Ghz | Hasil bandwidth band bertuliskan 5,8; jenis pengujian perlu ditetapkan |

PDF mempunyai 50 baris. Usulan: jumlah baris aplikasi mengikuti AP/titik yang
benar-benar diuji; ekspor menambah halaman jika lebih dari 50, bukan membatasi
inventaris pada 50 AP. Satu baris telah dikonfirmasi sebagai satu AP sampling; identitas kamar/koridor
dicatat sebagai lokasi AP. Pengukuran beberapa titik untuk AP yang sama belum
ditetapkan sebagai kebutuhan. Setiap band yang tidak tersedia atau
gagal diuji memerlukan status/alasan, bukan 0 atau hasil rekaan.

Label asli lampiran adalah Signal (db) dan 5.8Ghz; jangan mengubahnya menjadi dBm
atau seluruh band 5 GHz sebelum konfirmasi. Pengukuran sinyal AP dari HP dan
signal/CCQ backbone dari radio/perangkat merupakan sumber berbeda; kemampuan
scan Wi-Fi HP tidak dianggap dapat membaca CCQ radio backbone.

## Penyesuaian aplikasi yang diperlukan

1. Kunjungan berpusat pada hotel, dengan pemeriksaan router/switch/LAN dan hasil
   AP sampling yang dipilih, bukan mewajibkan seluruh AP hotel diuji.
   Jadwal/kunjungan per perangkat lama serta riwayatnya tetap dipertahankan.
   Perlu kontrak transisi/migrasi ke alur hotel tanpa menduplikasi laporan lama.
2. Tambahkan identitas perusahaan/PIC/kontak/timezone hotel dan snapshot laporan.
3. Form terstruktur untuk backbone, LAN, lampiran AP, summary, feedback/solusi.
   Checklist boolean/generik sekarang belum cukup untuk angka dan enum di PDF.
4. Pisahkan hasil pekerjaan (selesai/pending) dari review (submitted, revisi,
   approved). Approval laporan pekerjaan pending tidak boleh otomatis dianggap
   menyelesaikan seluruh maintenance. Alur tindak lanjut/revisit perlu ditentukan.
5. Bukti foto/tanda tangan privat, verifikasi upload dan aturan kelengkapan;
   implementasi saat ini masih memakai alasan pengecualian PIC, belum tanda tangan.
6. PDF utama + lampiran mengambil snapshot versi laporan agar angka, nama,
   keputusan dan tanda tangan konsisten dengan versi yang disetujui.

## Rincian berikutnya yang belum diputuskan

Cakupan laporan hotel, koneksi FO/wireless dan satu baris per AP sampling sudah
dikonfirmasi. Hal berikut tetap perlu dibahas sebelum aturan wajib diaktifkan:

- Label signal/db, 5.8 GHz, TX/RX, jenis speedtest dan batas rekomendasi: mengikuti
  PDF persis atau diperjelas? Apa definisi kesesuaian Service Agreement?
- Ketiga tanda tangan: wajib atau ada pengecualian? Foto wajib untuk bagian mana?
- Bila pekerjaan pending: kapan jadwal selesai dan bagaimana kunjungan ulang
  dibuat? Approval laporan tetap dibedakan dari penyelesaian pekerjaan.

Urutan implementasi berikutnya: model jadwal/kunjungan hotel dan cakupan koneksi,
form pemeriksaan router/switch/LAN, lalu daftar sampling AP dengan lokasi dan
pengukuran per band. Data per perangkat dan snapshot lama tidak dikonversi atau
dihapus tanpa rancangan kompatibilitas yang telah diuji. Belum ada perubahan
schema atau deployment berdasarkan dokumen ini.

## Bukti foto dan pengukuran AP — dikonfirmasi pengguna

- Setiap router dan switch yang diperiksa wajib mempunyai foto kondisi perangkat
  pada kunjungan tersebut. Foto kunjungan lama tidak memenuhi bukti kunjungan baru.
- Setiap AP yang dipilih sebagai sampling wajib mempunyai foto AP. AP inventaris
  yang tidak dipilih tidak diwajibkan foto/pengukuran pada kunjungan tersebut.
- Form pemeriksaan perangkat memiliki aksi Ambil Foto; foto direlasikan dengan
  kunjungan dan perangkat/sampel yang tepat, bukan sekadar galeri umum hotel.
- Pada sampel AP yang sama, teknisi mengakses Wi-Fi analyzer (sinyal, channel,
  frekuensi, SSID/BSSID) dan speedtest. Pengalaman aplikasi seperti WiFiman adalah
  acuan alur, bukan integrasi/penyalinan aplikasi tersebut.
- Foto dan hasil pengukuran menjadi satu rangkaian bukti sampling. Hasil scan
  harus mencatat sumber/waktu; speedtest harus mencatat jaringan/koneksi yang
  digunakan agar hasil seluler atau AP lain tidak salah dilekatkan ke AP sampel.
  Pembatasan kemampuan scan/izin Android wajib diuji pada HP fisik.

Aturan minimum teknis yang diusulkan: satu foto valid per perangkat yang wajib
berbukti; batas jumlah/ukuran/format dan kebijakan pengambilan dari kamera versus
galeri masih perlu ditetapkan. Pengajuan laporan menunggu bukti wajib berhasil
tersimpan server. Penyimpanan lokal/outbox pada APK harus mempertahankan foto
hingga unggahan dikonfirmasi. Persyaratan pengecualian bila kamera/unggahan gagal
belum disepakati; jangan membuat bypass opsional secara otomatis.

Status implementasi: persyaratan ini sudah dicatat, tetapi upload foto,
validasi kelengkapan foto dan Wi-Fi analyzer/speedtest belum tersedia pada
aplikasi yang sedang berjalan.


## Pembaruan implementasi

Fondasi kebutuhan terkonfirmasi telah diterapkan pada revision 0007: kunjungan
hotel, cakupan router/switch, sampling AP per lantai/titik, foto wajib privat dan
form laporan backbone/LAN/hasil pekerjaan. Dokumen ini tetap menyimpan analisis
awal dan keputusan desain; status implementasi terbaru ada di HOTEL_VISITS.md.
Analyzer/speedtest native, tanda tangan dan PDF masih belum tersedia. Angka dan
kategori saat ini input manual, bukan hasil pengukuran otomatis atau ambang baku.
