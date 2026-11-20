import { useEffect, useState } from "react";
import { PhotoPicker } from "../components/PhotoPicker";
import { combinedAreaNotes } from "../services/areaNotes";
import { Camera } from "lucide-react";
import type { LocalPhoto, Point, PointDraft } from "../types";
import { cameraService } from "../services/native";
import { radioFromObservation, type RadioDraft } from "../services/wifi";
import { NativeWifiPanel } from "../components/NativeWifiPanel";
import { SessionSpeedtestPanel } from "../components/SessionSpeedtestPanel";
import type { SpeedProgress } from "../services/speedWorker";
import { Badge, Card, Field, Message } from "../components/ui";
import { pointEvidence, when } from "../domain";
export function SamplingDetail({
  point,
  draft,
  photos,
  remotePhotos = 0,
  change,
  addPhoto,
  addPhotos,
  editable,
  busy,
  saveNotes,
  rebaseNotes,
  captureRadio,
  reportFailure,
  startTest,
  areas,
  selectArea,
}: {
  point: Point;
  areas: { id: string; name: string }[];
  selectArea: (id: string) => void;
  initialTab?: string;
  draft?: PointDraft;
  photos: LocalPhoto[];
  remotePhotos?: number;
  change: (value: PointDraft) => void;
  addPhoto: (file: Blob, category: string, caption: string) => Promise<void>;
  addPhotos: (
    files: Blob[],
    category: string,
    caption: string,
  ) => Promise<void>;
  editable: boolean;
  busy: boolean;
  saveNotes?: () => void;
  rebaseNotes?: () => void;
  captureRadio?: (value: RadioDraft) => Promise<void>;
  reportFailure?: (rebase: boolean) => Promise<void>;
  startTest?: (
    signal: AbortSignal,
    progress: (value: SpeedProgress) => void,
  ) => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [taking, setTaking] = useState(false),
    [category, setCategory] = useState("Foto Access Point"),
    [caption, setCaption] = useState("");
  const [radioBusy, setRadioBusy] = useState(false);
  const evidence = pointEvidence(point),
    savedObservation = point.session?.observation,
    notes =
      draft ||
      (savedObservation
        ? {
            ...savedObservation.notes,
            status: savedObservation.notes.condition,
            updatedAt: savedObservation.captured_at,
          }
        : { updatedAt: "" });
  const radio = { ...radioFromObservation(savedObservation), ...draft?.radio };
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
  return (
    <div className="stack">
      <div className="section-heading">
        <div>
          <p className="eyebrow">DETAIL AREA</p>
          <h2>{draft?.location || point.name}</h2>
        </div>
        <Badge
          tone={
            evidence.problem ? "danger" : evidence.done ? "success" : "neutral"
          }
        >
          {evidence.label}
        </Badge>
      </div>
      <NativeWifiPanel
        mode="connection"
        point={point}
        radio={radio}
        capture={editable ? captureRadio : undefined}
        busy={busy || radioBusy}
        setBusy={setRadioBusy}
      />
      {!point.session && (
        <p className="muted">
          Pembacaan Wi-Fi disimpan di perangkat ini. Penyimpanan pengukuran ke
          server dan speedtest per area memerlukan sesi sampling dari
          supervisor.
        </p>
      )}
      {error && <Message error>{error}</Message>}
      <div id="sampling-panel" aria-label="Pengujian area">
        {point.session ? (
          <SessionSpeedtestPanel
            startTest={startTest}
            point={point}
            draft={draft}
            change={change}
            reportFailure={reportFailure}
            busy={busy || radioBusy}
            editable={editable}
          />
        ) : (
          <Card title="Riwayat pengujian lama">
            <p>Tambahkan area aktual untuk menjalankan pengujian baru.</p>
            {point.item?.speedtests.map((run) => (
              <p key={run.id}>
                {when(run.created_at)} · {run.status} · ↓{" "}
                {run.metrics?.download_mbps ?? "—"} / ↑{" "}
                {run.metrics?.upload_mbps ?? "—"} Mbps {run.error}
              </p>
            ))}
          </Card>
        )}
        <section aria-label="Wi-Fi Scanner">
          <NativeWifiPanel
            mode="scan"
            point={point}
            radio={radio}
            capture={editable ? captureRadio : undefined}
            busy={busy || radioBusy}
            setBusy={setRadioBusy}
          />
        </section>
        <div className="stack sampling-notes" aria-label="Foto & Catatan">
          <Card title="Temuan dan Tindakan" collapsible>
            <fieldset
              className="form-body"
              disabled={!editable || taking || busy || radioBusy}
            >
              <Field label="Lokasi sampling">
                <select
                  value={point.id}
                  onChange={(e) => selectArea(e.target.value)}
                >
                  {areas.map((area) => (
                    <option key={area.id} value={area.id}>
                      {area.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Kondisi area">
                <select
                  value={
                    notes.status || savedObservation?.notes.condition || "good"
                  }
                  onChange={(e) =>
                    change({
                      ...notes,
                      notes: combinedAreaNotes(draft, savedObservation?.notes),
                      combinedNotes: true,
                      findings: "",
                      action: "",
                      status: e.target.value,
                      updatedAt: new Date().toISOString(),
                    })
                  }
                >
                  <option value="untested">Belum diperiksa</option>
                  <option value="good">Baik</option>
                  <option value="attention">Perlu Perhatian</option>
                  <option value="problem">Bermasalah</option>
                </select>
              </Field>
              <Field label="Temuan dan Tindakan">
                <textarea
                  rows={4}
                  maxLength={5000}
                  value={combinedAreaNotes(draft, savedObservation?.notes)}
                  onChange={(e) =>
                    change({
                      ...notes,
                      notes: e.target.value,
                      combinedNotes: true,
                      findings: "",
                      action: "",
                      status:
                        notes.status ||
                        savedObservation?.notes.condition ||
                        "good",
                      updatedAt: new Date().toISOString(),
                    })
                  }
                />
              </Field>
            </fieldset>
          </Card>
          <Card title="Dokumentasi Foto">
            <fieldset
              className="form-body"
              disabled={!editable || taking || busy || radioBusy}
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
              <Field label="Keterangan">
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
              <PhotoPicker
                disabled={!editable || taking || busy || radioBusy}
                onFiles={async (files) => {
                  await addPhotos(files, category, caption);
                  setCaption("");
                }}
              />
            </fieldset>

            <div className="photo-grid">
              {photos.map((photo) => (
                <LocalPhotoCard key={photo.id} photo={photo} />
              ))}
            </div>
            {!photos.length && (
              <p className="muted">
                Belum ada foto lokal.{" "}
                {remotePhotos || point.item?.photos.length || 0} foto tersedia
                di server. Lihat dan kirim dokumentasi di halaman Review.
              </p>
            )}
          </Card>
          {point.session && (
            <Card>
              <button
                className="primary wide"
                disabled={!editable || busy || radioBusy || !saveNotes}
                onClick={saveNotes}
              >
                Simpan Hasil
              </button>
              {rebaseNotes && (
                <>
                  <p>
                    Tinjau catatan server dan draf, lalu muat ulang kunjungan
                    sebelum membuat kiriman pengganti.
                  </p>
                  <button
                    className="secondary wide"
                    disabled={!editable || busy || radioBusy}
                    onClick={rebaseNotes}
                  >
                    Kirim draf setelah review
                  </button>
                </>
              )}
            </Card>
          )}
        </div>
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
