# Observasi dan catatan per sesi sampling

16 November 2026. Implementasi source lokal, belum deployment. Draft 0011 berada
di `docs/migrations/0011_sampling_observations.py`, di luar head aktif 0009.
Draft harus direview sebelum promosi/penerapan; tidak ada migration dijalankan
pada database produksi. Fondasi 0010 menjadi dependensi.

## Fungsi yang tersedia

Teknisi pemilik kunjungan dapat menyimpan catatan, temuan, tindakan, rekomendasi
dan penilaian kondisi per sesi titik. Catatan memakai lokasi snapshot, bukan
perangkat inventaris, sehingga dua lokasi yang dilayani AP sama tetap independen.

- GET/POST `/hotel-visits/{visit}/sampling-sessions/{session}/observations`.
- POST wajib UUID klien, expected_visit_version, expected_session_version,
  captured_at berzona waktu dan notes. Mutasi hanya untuk teknisi pemilik pada
  kunjungan in_progress/revision_requested. Supervisor boleh membaca histori.
- Kondisi attention/problem wajib temuan. Kondisi good adalah penilaian teknisi,
  bukan bukti pemeriksaan selesai. Status sesi/progress tidak dinaikkan hanya
  karena catatan tersimpan.
- GET berpaginasi, maksimal 100, versi terbaru dahulu. Detail cakupan/visit membawa
  observasi terakhir per sesi; histori lama tetap ada untuk audit.
- Replay UUID dengan payload identik mengembalikan observasi sama tanpa menambah
  versi. UUID berbeda isi/scope/aktor ditolak. Penulisan baru memeriksa versi dan
  menaikkan versi visit serta sesi dalam satu transaksi; konflik tidak menyimpan
  sebagian data. Lock visit mengikuti workflow laporan existing.

Web dan Android menampilkan catatan server, draf lokal, tombol simpan, dan tindakan
review konflik. IndexedDB menyimpan payload kiriman beserta UUID sebelum request.
Respons hilang dapat diulang dengan payload sama. Draf baru tidak mengganti
payload yang status penerimaannya belum diketahui. Setelah 409, pengguna harus
meninjau catatan server dan memuat ulang sebelum membuat kiriman pengganti dengan
UUID/versi baru. Versi dasar draf disimpan sejak edit pertama, sehingga reload
tidak otomatis menganggap draf lama cocok dengan versi server terbaru.

Antrean dipisahkan per origin/akun/visit/sesi (Web juga terisolasi oleh origin
IndexedDB). Sinkronisasi saat ini manual, bukan background sync. Foto tetap lokal
dan tidak dihapus oleh penyimpanan catatan. Kegagalan storage membatalkan kiriman;
tidak ada klaim synced sebelum acknowledgment server.

## Kontrak Wi-Fi dan batas kepercayaan

POST mendukung wifi_connection dan wifi_scan opsional dari klien Android. Field
source hanya menerima android_native; transport koneksi harus wifi. SSID/BSSID,
frequency MHz, RSSI dBm, link speed Mbps, alamat IP/gateway, observed_at berzona
waktu serta penanda cached scan divalidasi. Hasil null tetap null, nilai nol yang
valid tidak diganti. Scan dibatasi 256 jaringan per observasi.

Source adalah deklarasi klien, bukan attestation perangkat. Respons secara eksplisit
menyimpan measurement_trust=client_reported, radio_verified=false dan
completion_accepted=false. API tidak menjadikan data ini bukti validasi trafik
speedtest atau kecocokan AP. Field radio_verified/completion dari klien ditolak.
Plugin Wi-Fi Android sudah memakai kontrak ini pada source Phase 4. Capture radio
tersimpan di draf sesi lalu dikirim melalui outbox; metadata cache per jaringan
dan timestamp OS dipertahankan. Uji radio perangkat fisik belum dilakukan.
Tidak ada scan simulasi atau hasil speedtest buatan pada aplikasi.
Lihat [Phase 4](PHASE-4-NATIVE-WIFI.md).

## Draft schema untuk review

Tambahan satu tabel `sampling_observations`: id UUID PK, session_id FK RESTRICT,
actor_id FK RESTRICT, session_version >= 2, visit_version >= 1, captured_at,
received_at server, payload JSONB. UNIQUE(session_id, session_version) mencakup
pencarian FK sesi/histori; actor_id mempunyai indeks sendiri. Tidak ada perubahan
tabel existing, backfill, seed, drop atau operasi penghapusan histori.

Table append-only pada API; payload menyimpan request normalisasi untuk replay,
termasuk versi dasar. Waktu perangkat tidak menggantikan received_at server.
DDL tetap membutuhkan lock FK saat pembuatan: review SQL offline, audit head,
backup/restore dan PostgreSQL terisolasi sebelum penerapan. Downgrade penghapus
histori tidak disediakan; pemulihan melalui perubahan forward yang direview.

## Aktivasi dan verifikasi

Default write nonaktif. Memerlukan SAMPLING_MASTER_ENABLED=true dan
SAMPLING_OBSERVATIONS_ENABLED=true sesudah schema 0010/0011 tersedia. Tidak ada
environment server yang diubah. Membaca visit tetap dapat melihat observasi
tersimpan saat gate write dimatikan; schema 0010 tanpa tabel 0011 tetap didukung.

Test backend memeriksa ownership, scope lintas sesi, UUID/replay, konflik versi,
histori, validasi Wi-Fi, serta larangan memalsukan status selesai. SQL draft
dikompilasi offline dan head aktif tetap 0009. Test PostgreSQL opt-in menerapkan
draft hanya dalam schema acak database `_test`/`_staging`; jika URL tidak tersedia,
test dilewati dan tidak membuktikan PostgreSQL nyata.

Test outbox Android mencakup offline, acknowledgment hilang, versi dasar draf,
review konflik, kegagalan persistence dan pemisahan akun. Browser integration
memakai FastAPI sebenarnya dan SQLite terisolasi: catatan Web dibaca Android,
respons POST Android sengaja dihilangkan sesudah commit, lalu retry menghasilkan
dua revisi keseluruhan (Web + Android), tanpa duplikat kiriman Android.

Belum termasuk uji radio HP fisik, binding jaringan LibreSpeed, pengujian per
sesi, upload foto sesi, lifecycle temuan terstruktur, PIC, dan submit V2. Guard
submit V2 tetap aktif. Backbone FO/wireless dan Local Area Network tidak diubah.
