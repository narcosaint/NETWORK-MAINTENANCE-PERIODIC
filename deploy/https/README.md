# Verifikasi publik berhasil — 18 November 2026

Setelah NOC mengonfirmasi forwarding, HTTPS langsung ke 110.232.70.162:443
menggunakan SNI maintenance.inisaja.id dan trust store standar berhasil.
Health/database mengembalikan ok; pemeriksaan origin lewat DNS juga lulus untuk
health, penolakan anonim auth/me serta kontrak login/kunjungan. Tidak ada password
atau data uji yang dikirim. Login akun teknisi di HP masih perlu diuji operator.
Origin APK: https://maintenance.inisaja.id. APK terbaru:
artifacts/android/hotel-maintenance-https-debug.apk.

Catatan status sebelumnya di bawah merupakan riwayat diagnosis.

# HTTPS terpasang — 18 November 2026

Sertifikat publik Let’s Encrypt berhasil diterbitkan untuk maintenance.inisaja.id
melalui HTTP-01 pada NAT publik port 80 ke port privat 8000. API sempat dihentikan
untuk bootstrap lalu dihidupkan kembali; database/schema/volume tidak dimodifikasi.
Issuer YE2, masa berlaku 18 November 2026 sampai 16 Februari 2027.

Layanan systemd hotel-maintenance-https.service aktif dan enabled, user hotel-caddy,
binary Caddy 2.11.9 resmi pada /usr/local/bin/hotel-caddy. Config aktif:
/etc/hotel-maintenance-caddy/Caddyfile. State akun ACME dan private key di
/var/lib/hotel-maintenance-caddy, mode direktori 0700. Jangan salin private key
ke repo, APK atau chat. Hanya fullchain publik disalin ke
artifacts/https/maintenance.inisaja.id-fullchain.pem.

HTTPS listen pada **10.100.23.103:443**, upstream HTTP 10.100.23.103:8000.
Tidak menambah CORS global, mematikan validasi TLS atau mengubah firewall/router.
Pembaharuan sertifikat otomatis dikonfigurasikan Caddy lewat TLS-ALPN-01;
memerlukan port publik 443 diteruskan langsung ke service ini. Jalur renewal
publik belum terverifikasi karena forwarding 443 masih belum tembus.

## Yang sudah diuji

- Validasi kedua Caddyfile serta systemd unit lulus.
- Sertifikat SAN/issuer/expiry diperiksa; HTTPS privat diuji dengan curl --resolve
  dan validasi sertifikat normal, tanpa -k.
- Health API/database, 401 anonim /auth/me serta kontrak login/kunjungan lulus.
- DNS lokal server saat ini mengarah ke IP privat; keberhasilan lokal tidak
  menyatakan akses publik sudah siap. DNS Google/Cloudflare menunjuk 110.232.70.162.
- Probe ke 110.232.70.162:443 masih connection refused setelah service lokal aktif.
- APK mengembalikan HTTPS-only, menghapus pengecualian HTTP Android dan memakai
  default https://maintenance.inisaja.id hanya di native. Token/password tidak
  disimpan; login nyata dengan akun teknisi belum diuji di HP.
- 36 tes frontend dan 10 tes origin/scaffold lulus, lint/typecheck/build APK lulus.

## Permintaan tersisa ke NOC

Forward **TCP 110.232.70.162:443 ke 10.100.23.103:443**, dengan TLS passthrough
(tanpa terminasi/challenge gateway tambahan), agar sertifikat dan renewal Caddy
berfungsi. Port 443 jangan diarahkan ke 8000 karena upstream itu HTTP biasa.
Setelah jalur publik aktif, verifikasi /health dan /health/db dari jaringan luar
serta login APK di HP. Atur redirect HTTP ke HTTPS di sisi NOC setelah HTTPS
berfungsi; jalur HTTP port 80 saat ini masih menuju backend existing.

Tidak ada deployment source Phase 4/5 atau migration 0010–0012 pada langkah ini.
Akses login tidak berarti schema/gate sampling terbaru telah aktif.

## Operasi

- systemctl status hotel-maintenance-https.service
- journalctl -u hotel-maintenance-https.service
- Setelah perubahan config yang direview: validasi lalu restart service (admin
  endpoint Caddy dimatikan, sehingga tidak menggunakan reload admin API).
- Jangan jalankan bootstrap di samping API: port 8000 dipakai bersama hanya saat
  bootstrap awal. Config bootstrap tersimpan untuk audit, bukan service harian.
- Rollback proxy: stop/disable hanya hotel-maintenance-https.service; backend
  privat dan data tetap berjalan. Jangan hapus state sertifikat atau downgrade DB.

Rujukan: https://caddyserver.com/docs/automatic-https dan
https://letsencrypt.org/docs/challenge-types/.

---

Catatan persiapan historis di bawah.

# Status terbaru — binding privat telah diterapkan

18 November 2026: operator meminta perubahan bind ke IP privat. API aktif dan
terverifikasi sehat di **http://10.100.23.103:8000**. API/database healthy dan
checksum aset web identik setelah recreate. Docker database/network/volume serta
migration tidak diubah. Hanya published port API dan image pelestarian aset web
berubah. Healthcheck loopback di dalam container tetap dipertahankan.

Caddyfile sudah memakai upstream 10.100.23.103:8000 dan lolos validasi, tetapi
proxy HTTPS belum dipasang. NOC dapat meneruskan trafik domain ke IP/port privat
ini dari jaringan yang dapat menjangkaunya. Akses dari jaringan NOC dan HTTPS
publik masih perlu dibuktikan; health dari server bukan bukti akses eksternal.

Catatan persiapan di bawah adalah riwayat sebelum perubahan bind privat.

# Proposal akses HTTPS APK — belum dipasang

Audit 18 November 2026: `/health` dan `/health/db` backend aktif mengembalikan
status ok. API hanya listen pada 127.0.0.1:8000. Tidak ada listener 80/443 atau
instalasi Caddy/nginx yang ditemukan. Domain telah dikonfirmasi: maintenance.inisaja.id.

Caddyfile di direktori ini adalah proposal reverse proxy langsung ke backend
existing. Ini **bukan database staging terisolasi**. Mengaktifkannya akan membuat
aplikasi existing dapat dijangkau lewat domain. Tidak membuat user/data uji,
tidak mengganti backend, tidak mengubah Docker dan tidak menjalankan migration.
Domain khusus staging tidak dengan sendirinya mengisolasi data; Phase 5 memerlukan
backend/schema staging tersendiri sebelum percobaan dengan data uji.

## Konfigurasi yang direview

- Hostname final: `maintenance.inisaja.id`.
- Upstream existing: `127.0.0.1:8000`; port backend/database tetap privat.
- Caddy mengelola TLS publik dan redirect HTTP; memerlukan DNS yang benar serta
  konektivitas masuk TCP 80/443. Jangan memasang AAAA jika IPv6 belum tersedia.
- Tidak menambah encode/cache/buffering untuk trafik LibreSpeed.
- Admin endpoint Caddy dimatikan. Header auth dan Host diteruskan oleh proxy.
- Tidak menambah CORS global atau menonaktifkan pemeriksaan sertifikat Android.
- Jangan mematikan proxy, DNS atau autentikasi yang dimiliki layanan lain.

Referensi resmi: [automatic HTTPS](https://caddyserver.com/docs/automatic-https),
[reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).

## Sebelum aktivasi

1. Konfirmasi hostname dan kontrol DNS. Verifikasi A/AAAA ke server tujuan dari
   jaringan luar. Nama hostname mesin tidak membuktikan DNS/domain API tersedia.
2. Review file ini beserta Caddyfile; minta persetujuan pemasangan proxy/service
   dan akses 80/443 sesuai AGENTS.md. Belum ada perubahan server dilakukan.
3. Pasang Caddy dari distribusi resmi, file config dan
   service milik user Caddy. Simpan state/cert di direktori persisten user Caddy.
   Jangan menjalankan daemon di terminal sementara sebagai deployment permanen.
4. Validasi config sebelum memulai service. Jangan mengubah firewall/port tanpa
   persetujuan. Pastikan layanan existing tidak bentrok dan health tetap ok.
5. Verifikasi dari luar server memakai TLS tepercaya, tanpa `-k` atau redirect
   ke halaman login gateway. Jalankan:

   ```bash
   python3 scripts/check_android_origin.py https://maintenance.inisaja.id
   ```

6. Setelah lulus, operator login di APK dengan akun existing. Password tidak
   perlu dikirim di chat. Verifikasi jadwal/hak akses di HP. APK belum boleh
   disebut siap hanya karena APK berhasil dibangun atau endpoint health hidup.
7. Khusus Phase 5, backend/schema staging dan gate harus disiapkan terpisah
   setelah review draft migration. Jalankan pemeriksaan tambahan `--phase5`,
   lalu uji pengukuran radio/transfer nyata di HP. Script hanya memeriksa kontrak
   endpoint, bukan membuktikan migration/gate aktif atau throughput fisik.

Rollback akses HTTPS: hentikan hanya service proxy baru yang telah dipasang;
backend existing dan data tidak perlu dipulihkan atau dimigrasikan balik.
Tidak menghapus state sertifikat/backup otomatis.

## Pemeriksaan read-only

`check_android_origin.py` menggunakan TLS default terverifikasi dan timeout,
menolak redirect, memeriksa health/database, respons 401 anonim `/auth/me`, serta
kontrak OpenAPI untuk login dan kunjungan. Tidak mengirim password, membuat login
session atau menulis data. Test otomatis juga memastikan API lama tidak keliru
lulus sebagai dukungan Phase 5.

Verifikasi persiapan: 10 test pemeriksaan origin/scaffold lulus. Caddyfile
lulus `caddy validate` dengan hostname fixture `api.example.com`; tidak ada
service dimulai atau port dibuka. Ini bukan verifikasi DNS/sertifikat live.

## Hasil cek domain final — 18 November 2026

Resolver server dan Google Public DNS sama-sama menghasilkan A `10.100.23.103`,
TTL publik 14400 detik (4 jam), tanpa AAAA. HTTPS dari server ditolak (connection
refused); belum ada listener TLS. IP A tersebut privat, sehingga domain belum
siap untuk HP di jaringan hotel/seluler. Ini bukan masalah login/password APK.

`110.232.68.9` hanya tercantum dalam hostname `/etc/hosts`, bukan alamat interface
yang terverifikasi menerima koneksi publik. NOC harus memastikan IP inbound,
routing dan NAT sebelum DNS diarahkan ke alamat tersebut.

Permintaan untuk NOC tersedia di [NOC-HANDOFF.md](NOC-HANDOFF.md). Jika NOC
menggunakan reverse proxy kantor, TLS dapat dikelola di sana dan Caddy lokal
mungkin tidak perlu dipasang. Jangan pasang dua proxy tanpa memastikan jalurnya.
Nama domain final tidak mengubah kebutuhan isolasi staging atau persetujuan
migration/deployment.
