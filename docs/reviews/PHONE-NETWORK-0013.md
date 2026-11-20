# Review: pengukuran koneksi HP tanpa inventaris

Instruksi operator menggantikan pencocokan BSSID ke inventaris AP. Area baru
maupun area dengan pemetaan historis mengukur jaringan Wi-Fi aktual HP.
Tidak menghapus inventaris, endpoint lama, ataupun bukti pengukuran terdahulu.

Migration 0013 menambahkan FK nullable ke sampling_sessions, mengizinkan
visit_device_id kosong, dan mewajibkan tepat satu pemilik hasil. Run lama tetap
memakai visit_device_id; run area baru memakai sampling_session_id. RESTRICT
mencegah penghapusan sesi dengan bukti. Tidak ada backfill, UPDATE atau DELETE.
DDL diperiksa pada PHONE-NETWORK-0013.sql. Downgrade sengaja ditolak karena
pemulihan harus mempertahankan hasil area baru.

Dampak: APK lama tetap bisa mengakses API. Backend lama tidak boleh diaktifkan
kembali setelah run area baru dibuat. Pemulihan menggunakan perbaikan maju;
jangan restore backup di atas data baru. Backup database/foto dan percobaan
restore terisolasi wajib selesai sebelum aktivasi migration produksi.

Verifikasi data membandingkan seluruh baris dengan kolom semula; kolom baru
sampling_session_id dikecualikan dari fingerprint hanya pada tabel
network_speedtests. Pengukuran uji dilakukan pada database terisolasi.
