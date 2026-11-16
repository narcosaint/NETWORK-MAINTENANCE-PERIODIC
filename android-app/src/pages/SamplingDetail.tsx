import { useEffect, useState } from "react";
import { Camera, Wifi, Zap } from "lucide-react";
import type { LocalPhoto, Point, PointDraft } from "../types";
import { cameraService, wifiService } from "../services/native";
import { libreSpeedService } from "../services/librespeed";
import { Badge, Card, Empty, Field, Message } from "../components/ui";
import { pointEvidence, when } from "../domain";
export function SamplingDetail({
  point,
  draft,
  photos,
  change,
  addPhoto,
  editable,
  busy,
}: {
  point: Point;
  draft?: PointDraft;
  photos: LocalPhoto[];
  change: (value: PointDraft) => void;
  addPhoto: (file: Blob, category: string, caption: string) => Promise<void>;
  editable: boolean;
  busy: boolean;
}) {
  const [tab, setTab] = useState("analyzer"),
    [band, setBand] = useState<"2.4 GHz" | "5 GHz">("2.4 GHz"),
    [error, setError] = useState(""),
    [taking, setTaking] = useState(false),
    [category, setCategory] = useState("Foto Access Point"),
    [caption, setCaption] = useState("");
  const evidence = pointEvidence(point),
    notes = draft || { updatedAt: "" };
  const saved = point.item?.result?.[band === "2.4 GHz" ? "band_24" : "band_5"];
  const capture = async (file?: Blob) => {
    setTaking(true);
    setError("");
    try {
      await addPhoto(
        file || (await cameraService.capture()),
        category,
        caption,
      );
      setCaption("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setTaking(false);
    }
  };
  const capability = libreSpeedService.capability();
  return (
    <div className="stack">
      <div className="section-heading">
        <div>
          <p className="eyebrow">DETAIL SAMPLING</p>
          <h2>{draft?.location || point.name}</h2>
          <p className="muted">
            {point.item?.device.name || "AP belum dipilih"}
          </p>
        </div>
        <Badge
          tone={
            evidence.problem ? "danger" : evidence.done ? "success" : "neutral"
          }
        >
          {evidence.label}
        </Badge>
      </div>
      <Card title="Connected Network" action={<Wifi size={18} />}>
        <Badge>Belum tersedia</Badge>
        <p className="muted">AP Belum Teridentifikasi</p>
        <dl className="network-grid">
          {[
            "SSID",
            "BSSID",
            "Frequency",
            "Channel",
            "Band",
            "RSSI (dBm)",
            "Link speed",
            "IP Address",
            "Gateway",
          ].map((label) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>Belum tersedia</dd>
            </div>
          ))}
        </dl>
        <button
          className="text-button"
          onClick={async () => {
            const result = await wifiService.connection();
            if (!result.available) setError(result.reason);
          }}
        >
          Detail ketersediaan
        </button>
      </Card>
      <div
        className="detail-tabs"
        role="tablist"
        aria-label="Pengujian sampling"
      >
        {[
          ["analyzer", "Wi-Fi Analyzer"],
          ["speed", "Speedtest"],
          ["notes", "Foto & Catatan"],
        ].map(([id, label]) => (
          <button
            id={"tab-" + id}
            key={id}
            role="tab"
            aria-selected={tab === id}
            aria-controls="sampling-panel"
            tabIndex={tab === id ? 0 : -1}
            onClick={() => {
              setTab(id);
              setError("");
            }}
            onKeyDown={(e) => {
              const tabs = ["analyzer", "speed", "notes"];
              if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key))
                return;
              e.preventDefault();
              const next =
                tabs[
                  e.key === "Home"
                    ? 0
                    : e.key === "End"
                      ? 2
                      : (tabs.indexOf(id) + (e.key === "ArrowRight" ? 1 : 2)) %
                        3
                ];
              setTab(next);
              document.getElementById("tab-" + next)?.focus();
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {error && <Message error>{error}</Message>}
      <div id="sampling-panel" role="tabpanel" aria-labelledby={"tab-" + tab}>
        {tab === "analyzer" ? (
          <Card title="Wi-Fi Analyzer">
            <div className="segmented" aria-label="Band Wi-Fi">
              {(["2.4 GHz", "5 GHz"] as const).map((value) => (
                <button
                  key={value}
                  aria-pressed={band === value}
                  onClick={() => setBand(value)}
                >
                  {value}
                </button>
              ))}
            </div>
            <Empty title="Belum ada hasil scan">
              <span>
                Grafik sinyal, jumlah jaringan, channel overlap dan waktu scan:
                Belum tersedia.
              </span>
            </Empty>
            <button disabled className="secondary wide">
              Pindai Wi-Fi · Belum tersedia
            </button>
            {saved?.status === "measured" && (
              <div className="historical">
                <h3>Input manual tersimpan · {band}</h3>
                <p>
                  {saved.signal_dbm ?? "Belum tersedia"} dBm · Channel{" "}
                  {saved.channel ?? "Belum tersedia"}
                </p>
                <p>
                  {saved.ssid || "SSID belum dicatat"} ·{" "}
                  {saved.bssid || "BSSID belum dicatat"}
                </p>
                <p className="muted">
                  Data laporan server, bukan koneksi aktif atau scan native.
                </p>
              </div>
            )}
          </Card>
        ) : tab === "speed" ? (
          <div className="stack">
            <Card title="LibreSpeed" action={<Zap size={18} />}>
              <div className="measurement-grid">
                {["Download", "Upload", "Ping", "Jitter"].map((label, i) => (
                  <div key={label}>
                    <small>{label}</small>
                    <strong>—</strong>
                    <span>{i < 2 ? "Mbps" : "ms"}</span>
                  </div>
                ))}
              </div>
              <button disabled className="primary wide">
                Mulai Speedtest · Belum tersedia
              </button>
              <p className="muted">
                {!capability.available && capability.reason}
              </p>
              <p className="muted">
                Setiap titik wajib punya pengujian sendiri atau gagal beralasan.
                Hasil AP lama tidak mewakili target lokal.
              </p>
            </Card>
            <Card title="Riwayat pengujian server">
              {point.item?.speedtests.length ? (
                point.item.speedtests.map((run) => (
                  <article key={run.id} className="history-item">
                    <Badge
                      tone={run.status === "failed" ? "danger" : "neutral"}
                    >
                      {(
                        {
                          completed: "Selesai",
                          failed: "Gagal",
                          aborted: "Dibatalkan",
                          running: "Sedang diuji",
                        } as Record<string, string>
                      )[run.status] || run.status}
                    </Badge>
                    <p>{when(run.finished_at || run.created_at)}</p>
                    <p>
                      {run.context?.transport === "direct_https"
                        ? "HTTPS langsung"
                        : "Diagnostik / konteks belum tersedia"}
                    </p>
                    <p>
                      Server: {run.context?.endpoint_origin || "Belum tersedia"}
                    </p>
                    {run.status === "completed" ? (
                      <div className="measurement-grid">
                        {[
                          ["Download", run.metrics?.download_mbps, "Mbps"],
                          ["Upload", run.metrics?.upload_mbps, "Mbps"],
                          ["Ping", run.metrics?.ping_ms, "ms"],
                          ["Jitter", run.metrics?.jitter_ms, "ms"],
                        ].map(([label, value, unit]) => (
                          <div key={label}>
                            <small>{label}</small>
                            <strong>{value ?? "—"}</strong>
                            <span>{unit}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p>{run.error || "Hasil belum tersedia"}</p>
                    )}
                  </article>
                ))
              ) : (
                <Empty title="Belum diuji">
                  Belum ada hasil speedtest tersimpan pada titik ini.
                </Empty>
              )}
            </Card>
          </div>
        ) : (
          <div className="stack sampling-notes" aria-label="Foto & Catatan">
            <Card title="Kondisi & Temuan">
              <fieldset
                className="form-body"
                disabled={!editable || taking || busy}
              >
                <Field label="Lokasi sampling">
                  <input
                    value={notes.location ?? point.name}
                    maxLength={200}
                    onChange={(e) =>
                      change({
                        ...notes,
                        location: e.target.value,
                        updatedAt: new Date().toISOString(),
                      })
                    }
                  />
                </Field>
                <Field label="Status titik lokal">
                  <select
                    value={notes.status || "untested"}
                    onChange={(e) =>
                      change({
                        ...notes,
                        status: e.target.value,
                        updatedAt: new Date().toISOString(),
                      })
                    }
                  >
                    {[
                      ["untested", "Belum Diperiksa"],
                      ["good", "Baik"],
                      ["attention", "Perlu Perhatian"],
                      ["problem", "Bermasalah"],
                    ].map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                {(
                  [
                    ["notes", "Catatan teknisi"],
                    ["findings", "Temuan"],
                  ] as const
                ).map(([key, label]) => (
                  <Field label={label} key={key}>
                    <textarea
                      rows={3}
                      value={notes[key] || ""}
                      maxLength={5000}
                      onChange={(e) =>
                        change({
                          ...notes,
                          [key]: e.target.value,
                          updatedAt: new Date().toISOString(),
                        })
                      }
                    />
                  </Field>
                ))}
              </fieldset>
            </Card>
            <Card title="Tindakan & Rekomendasi">
              <fieldset
                className="form-body"
                disabled={!editable || taking || busy}
              >
                {(
                  [
                    ["action", "Tindakan"],
                    ["recommendation", "Rekomendasi"],
                  ] as const
                ).map(([key, label]) => (
                  <Field label={label} key={key}>
                    <textarea
                      rows={3}
                      value={notes[key] || ""}
                      maxLength={5000}
                      onChange={(e) =>
                        change({
                          ...notes,
                          [key]: e.target.value,
                          updatedAt: new Date().toISOString(),
                        })
                      }
                    />
                  </Field>
                ))}
              </fieldset>
            </Card>
            <Card title="Dokumentasi Foto">
              <fieldset
                className="form-body"
                disabled={!editable || taking || busy}
              >
                <Field label="Kategori foto">
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    {[
                      "Foto Access Point",
                      "Foto perangkat",
                      "Foto area sampling",
                      "Foto temuan",
                    ].map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Keterangan foto">
                  <input
                    value={caption}
                    maxLength={500}
                    onChange={(e) => setCaption(e.target.value)}
                  />
                </Field>
                <button
                  type="button"
                  className="secondary wide"
                  disabled={taking}
                  onClick={() => void capture()}
                >
                  <Camera size={18} />
                  {taking ? "Menyimpan…" : "Ambil foto"}
                </button>
                <Field label="Pilih foto dari perangkat">
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    capture="environment"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      e.target.value = "";
                      if (file) void capture(file);
                    }}
                  />
                </Field>
              </fieldset>

              <div className="photo-grid">
                {photos.map((photo) => (
                  <LocalPhotoCard key={photo.id} photo={photo} />
                ))}
              </div>
              {!photos.length && (
                <p className="muted">
                  Belum ada foto lokal. {point.item?.photos.length || 0} foto
                  tersedia di server; pratinjau foto server belum terintegrasi.
                </p>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
function LocalPhotoCard({ photo }: { photo: LocalPhoto }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    const next = URL.createObjectURL(photo.blob);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [photo.blob]);
  return (
    <article>
      <img src={url || undefined} alt={photo.category} />
      <strong>{photo.category}</strong>
      <p>{photo.caption}</p>
      <small>{when(photo.createdAt)} · Lokal</small>
    </article>
  );
}
