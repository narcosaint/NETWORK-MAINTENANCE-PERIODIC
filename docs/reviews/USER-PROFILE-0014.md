# Review migration 0014 — profil kontak teknisi

Permintaan operator: lengkapi nomor WA, email kantor, divisi dan wilayah kerja;
operator telah menyetujui aktivasi backend/Web pada giliran ini.

SQL yang akan diterapkan:

```sql
ALTER TABLE users ADD COLUMN contact_profile JSON;
```

Satu kolom nullable tanpa DEFAULT, backfill, constraint atau index. Tidak ada
UPDATE/DELETE/INSERT atau perubahan tabel kunjungan, hasil ukur, foto maupun
snapshot tanda tangan. Akun existing tetap bernilai NULL (profil belum diisi).
JSON berisi empat field kontak dan versi untuk optimistic concurrency. Username,
nama, password, peran, status akun dan token login tidak dapat diubah endpoint ini.

Review dampak: ALTER mengambil lock singkat pada users; lock_timeout 10 detik dan
statement_timeout 60 detik saat migration. Jika lock gagal, transaksi dibatalkan.
Backward compatible dengan binary lama (kolom tambahan diabaikan). Jangan downgrade
atau menghapus kolom setelah profil mulai diisi. Pemulihan aplikasi menggunakan
image sebelumnya dan tetap mempertahankan kolom/data profil.

Sebelum produksi: uji SQL offline, migration pada PostgreSQL terisolasi, test
roundtrip/otorisasi/validasi/versi, serta backup konsisten DB+foto dan restore pada
salinan. Fingerprint membandingkan seluruh kolom lama users secara eksplisit,
sehingga penambahan kolom NULL tidak salah dibaca sebagai perubahan data.
Tidak ada pengisian data kontak produksi atau data QA di produksi.

Penerapan selesai 19 November 2026 setelah SQL offline, 31 test PostgreSQL dan
uji restore salinan lulus. Fingerprint seluruh kolom lama identik. Rincian dan
backup: docs/PROFILE-RELEASE-1.6.1.md.
