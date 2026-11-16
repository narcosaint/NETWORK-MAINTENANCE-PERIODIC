# Revisi laporan utama hotel — 0009

Form baru mengurangi pengetikan berulang dengan profil site dan memisahkan hasil
pemeriksaan per bagian. Sudah diterapkan pada 12 November 2026.

## Pengaturan sekali oleh supervisor

Menu **Hotel → Ubah** memuat:

- Nama hotel/site dan nama pelanggan/perusahaan (opsional). Jika nama pelanggan
  khusus tidak diisi, identitas pelanggan pada laporan memakai nama site.
- Profil maintenance site: bandwidth layanan download/upload FO, bandwidth layanan
  download/upload backup wireless, dan persentase minimum kesesuaian.

Nilai layanan dan persentase harus berdasarkan kesepakatan/SLA nyata. Tidak ada
angka/default persentase yang ditanam ke data produksi. Kolom kosong tetap
kosong; upload layanan tidak diasumsikan sama dengan download. Profil boleh
berbeda per site. PUT /hotels/{id} adalah penggantian penuh; klien API harus
mengirim customer_name dan maintenance_profile yang ingin dipertahankan.

## Form teknisi

Nama pelanggan terbaca otomatis dari site dan tidak menjadi input ulang teknisi.
PIC aktual kunjungan tetap diisi teknisi karena dapat berbeda setiap kunjungan.

**BACKBONE**

1. FO: hasil download, upload, kesesuaian otomatis, keterangan.
2. Backup wireless: hasil download, upload, kesesuaian otomatis, hasil link test
   radio, signal strength dan keterangan. Kolom TX rate/RX rate/CCQ dihapus dari
   form baru. Hasil link test radio berupa teks agar unit/hasil alat dapat dicatat
   apa adanya; tidak mengarang satuan/nilai yang belum dikonfirmasi.

Koneksi FO saja/wireless saja/keduanya/failover/bonding tetap didukung. Bagian yang
tidak digunakan tidak perlu diisi dan tidak dianggap memiliki nilai nol.

**LOCAL AREA NETWORK**

1. LAN: (a) koneksi LAN router, (b) LAN to switch.
2. Wireless dan Hotspot: (a) signal test, (b) blank spot, (c) hotspot.

Masing-masing dari lima pemeriksaan mempunyai hasil dan keterangan sendiri.
Keterangan wajib di laporan baru; server menolak pengajuan jika salah satunya
kosong/whitespace. Router/switch yang tidak berlaku dapat ditandai demikian dan
wajib diberi penjelasan. Catatan LAN umum format lama tetap disimpan dan dapat
dibaca; tidak diubah otomatis menjadi lima hasil pemeriksaan baru.

## Penilaian otomatis

`download_terukur >= download_layanan × minimum_percent / 100`
dan
`upload_terukur >= upload_layanan × minimum_percent / 100`.

Kedua arah harus memenuhi batas untuk hasil **Sesuai**. Salah satu kurang memberi
**Tidak sesuai**. Jika profil/ambang belum lengkap atau pengukuran belum diisi,
hasil **belum dapat dinilai**/menunggu, bukan dipaksa sesuai/tidak sesuai.
Tidak ada pilihan kesesuaian manual pada form baru. Nilai baseline/ambang tidak
dapat diganti teknisi lewat payload laporan; server membaca master site dan
menghitung ulang. Server memakai Decimal untuk batas inklusif yang tepat.

Preview berubah ketika teknisi mengisi download/upload, lalu penilaian server
yang menjadi hasil tersimpan. Kesesuaian ini perhitungan angka, bukan pengukuran
speedtest otomatis dan bukan bukti kapasitas radio. Speedtest AP/tunnel tetap
memiliki konteks dan batas terpisah di SPEEDTEST.md; hasil AP tidak otomatis
dianggap hasil backbone FO/wireless.

Saat laporan disimpan, nama pelanggan, salinan profil dan nilai batas yang dipakai
ikut disimpan. Perubahan master setelah submitted/approved tidak menafsirkan
ulang hasil laporan tersebut. Jika diminta revisi lalu disimpan lagi, versi baru
menggunakan profil site terkini; snapshot versi lama tetap utuh.

## Kompatibilitas

Migration 0009 hanya menambahkan hotels.customer_name dan maintenance_profile,
keduanya nullable. Tidak ada seed, import nama dari contoh PDF, pengisian SLA,
persen default atau penulisan ulang JSON laporan lama.

Kunjungan baru dibuat dengan form_version 2; format yang sudah versi 2 tidak dapat
diturunkan ke versi 1. Laporan lama versi 1 tetap dapat dibaca dan diproses sesuai
kontrak lama, tanpa menjadikan angka speedtest tunggal lama sebagai download atau
upload. Nilai arah lama yang belum diketahui ditampilkan sebagai data lama. Data
TX/RX/CCQ historis yang ada dipertahankan; field kosong legacy tidak dibuat pada
branch laporan baru. Laporan approved tidak dapat diedit.

## Verifikasi

47 tes backend, 14 tes PostgreSQL staging dan 3 scaffold lulus. Kasus yang diuji:
batas inklusif, bandwidth asimetris, nilai hilang, persentase belum ditentukan,
upaya memalsukan nama pelanggan/ambang/keputusan dari klien, kewajiban lima
keterangan, larangan downgrade, serta laporan lama tetap dapat direview.
Chromium menguji form pada desktop/ponsel di database terpisah dan image Docker:
nama readonly, field manual conformity/TX/CCQ tidak ada, perubahan hasil langsung
mengubah penilaian, pengisian LAN dan seluruh alur foto/revisi/approval tetap jalan.

Screenshot pengujian (data staging saja) berada pada artifacts/web/revised-report-*.png.
Tidak ada akun/data contoh yang dibuat ke database utama.
