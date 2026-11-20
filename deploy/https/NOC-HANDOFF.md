# Verifikasi publik berhasil — 18 November 2026

Setelah NOC mengonfirmasi forwarding, HTTPS langsung ke 110.232.70.162:443
menggunakan SNI maintenance.inisaja.id dan trust store standar berhasil.
Health/database mengembalikan ok; pemeriksaan origin lewat DNS juga lulus untuk
health, penolakan anonim auth/me serta kontrak login/kunjungan. Tidak ada password
atau data uji yang dikirim. Login akun teknisi di HP masih perlu diuji operator.
Origin APK: https://maintenance.inisaja.id. APK terbaru:
artifacts/android/hotel-maintenance-https-debug.apk.

Catatan status sebelumnya di bawah merupakan riwayat diagnosis.

# Tindakan NOC tersisa — sertifikat sudah terpasang

Let’s Encrypt untuk maintenance.inisaja.id sudah diterbitkan dan HTTPS privat
10.100.23.103:443 terverifikasi healthy. Mohon forward **TCP publik
110.232.70.162:443 → 10.100.23.103:443** (TLS passthrough). Sertifikat dikelola
Caddy di server ini; tidak perlu membeli SSL atau memindahkan private key.
Pembaharuan otomatis memakai TLS-ALPN-01 sehingga jalur 443 ini harus tetap aktif.
Saat pemeriksaan terakhir, port publik 443 masih connection refused.

Setelah forwarding, uji https://maintenance.inisaja.id/health dari luar jaringan.
Jika ok, baru uji login APK. Redirect HTTP ke HTTPS setelah jalur HTTPS teruji.

Catatan di bawah adalah diagnosis sebelumnya.

# Permintaan akses maintenance.inisaja.id

Domain final aplikasi Hotel Network Maintenance (Web + Android):
`maintenance.inisaja.id`.

Hasil cek 18 November 2026:

- A publik saat ini: `10.100.23.103` (IP privat server), TTL 14400 detik.
- AAAA tidak ditemukan.
- Backend kini sehat pada **`http://10.100.23.103:8000`**, setelah perubahan bind yang diminta operator.
- Belum ada listener HTTPS pada server; akses HTTPS ditolak.
- `110.232.68.9` tercantum pada hostname, tetapi IP inbound/NAT belum dikonfirmasi.

Mohon NOC pilih jalur akses yang dikelola kantor:

1. Reverse proxy HTTPS kantor yang dapat menjangkau server aplikasi. Gunakan upstream
   `http://10.100.23.103:8000`; binding sudah diterapkan dan diverifikasi dari
   server aplikasi. Mohon uji keterjangkauan dari mesin proxy NOC. Firewall/NAT
   di luar server belum diverifikasi atau diubah.
2. HTTPS pada server aplikasi, dengan DNS mengarah ke IP publik yang terverifikasi
   dan forwarding TCP 80/443 ke server aplikasi. Draft Caddy tersedia, belum dipasang.

Kebutuhan aplikasi:

- Dapat dijangkau HP dari Wi-Fi hotel/seluler, dengan sertifikat publik tepercaya.
- Semua path API diteruskan tanpa menambah/menghapus prefix /api.
- Header Host dan Authorization diteruskan; redirect tidak membuang request login.
- LibreSpeed download/upload tidak dicache, dikompresi atau dibuffer oleh proxy.
- Tidak memakai challenge/login gateway interaktif yang tidak didukung APK.
- Port backend/database tidak dibuka ke internet.
- Jangan membuat AAAA jika jalur IPv6 belum berfungsi.
- Bila VPN wajib, koordinasikan dahulu: alur validasi speedtest Android saat ini
  menolak VPN. Login dan pengukuran radio perlu diuji terpisah.

Setelah jalur dikonfirmasi, konfigurasi final dipasang dengan persetujuan operator,
lalu DNS/TLS/health/API diperiksa dari luar server. Origin APK baru dinyatakan siap
setelah pemeriksaan dan login HP berhasil:
`https://maintenance.inisaja.id`.

Untuk pengujian Phase 5, domain ini belum membuktikan backend/schema terbaru
terpasang. Jangan memakai data dummy di database produksi. Migration 0010–0012
masih memerlukan review serta lingkungan uji terpisah.

## Diagnosis setelah perubahan DNS

DNS Google Public DNS sekarang mengembalikan `110.232.70.162`. Probe dari server
menghasilkan:

- TCP publik port 80 terhubung. HTTP `/health` dengan Host maintenance.inisaja.id
  mengembalikan 200, application/json, `{"status":"ok"}`, Server uvicorn.
- TCP publik port 443 ditolak (connection refused).
- Backend privat 10.100.23.103:8000 terhubung; `/health` mengembalikan 200/ok.
- Tidak ada listener privat 443. Operator juga melaporkan gagal mengakses HTTPS
  dari HP melalui data seluler.

Kesimpulan: DNS dan jalur HTTP sudah mencapai backend. Terminasi TLS HTTPS belum
terverifikasi/tersedia. NOC perlu listener reverse proxy HTTPS dengan sertifikat
maintenance.inisaja.id dan jalur port 443 menuju listener tersebut, lalu upstream
HTTP ke 10.100.23.103:8000. Jangan sekadar meneruskan TLS port 443 ke port 8000
yang melayani HTTP biasa. Setelah HTTPS lulus, arahkan HTTP ke HTTPS.
Jangan login melalui HTTP; APK tetap mewajibkan HTTPS tepercaya.
