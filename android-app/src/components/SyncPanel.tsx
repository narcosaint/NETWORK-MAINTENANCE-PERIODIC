import { Badge } from "./ui";
export function SyncPanel({
  local,
  status,
  error,
  cached,
  draftVersion,
  versionConflict,
}: {
  local: boolean;
  status: string;
  error: string;
  cached: boolean;
  draftVersion?: number;
  versionConflict: boolean;
}) {
  const failed = status.startsWith("Gagal");
  const conflict = versionConflict || error.includes("Data server berubah");
  const label = conflict
    ? "Konflik server · draf dipertahankan"
    : error || failed
      ? "Perlu perhatian"
      : local
        ? "Perubahan belum disinkronkan"
        : cached
          ? "Data cache perangkat"
          : "Status penyimpanan";
  return (
    <section
      className={
        "sync-panel" + (error || failed || conflict ? " has-error" : "")
      }
      aria-label="Status sinkronisasi"
    >
      <details>
        <summary>
          <div>
            <span className="sync-panel-label">Status sinkronisasi</span>
            <strong>{label}</strong>
            {status && (
              <span
                className="sync-panel-status"
                role={failed ? "alert" : "status"}
              >
                {status}
              </span>
            )}
          </div>
          <span className="sync-toggle">
            Detail <span aria-hidden="true">⌄</span>
          </span>
        </summary>
        <div className="sync-panel-details">
          {cached && (
            <p>Data cache perangkat. Kondisi server belum diperbarui.</p>
          )}
          {local ? (
            <>
              <Badge tone="warning">Draf lokal</Badge>
              <p>
                {draftVersion !== undefined
                  ? `Draf laporan versi ${draftVersion}. `
                  : ""}
                Catatan dan foto sampling disimpan di perangkat; belum
                tersinkron ke server dan tidak dihitung sebagai progress server.
              </p>
            </>
          ) : (
            <p>
              Tidak ada draf kunjungan lokal. Status koneksi perangkat bukan
              bukti sinkronisasi server.
            </p>
          )}
          <p>
            Laporan utama dikirim melalui tombol simpan. Tidak ada sinkronisasi
            otomatis.
          </p>
        </div>
      </details>
      {error && (
        <p className="sync-panel-error" role="alert">
          {error}
        </p>
      )}
      {versionConflict && (
        <p className="sync-panel-error" role="alert">
          Versi draf berbeda dari server. Draf tetap dipertahankan. Tinjau
          konflik melalui Web Dashboard; versi tidak diganti otomatis.
        </p>
      )}
    </section>
  );
}
