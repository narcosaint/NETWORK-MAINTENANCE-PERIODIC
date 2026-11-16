import { useEffect, useRef, useState } from "react";
import { MapPin, RefreshCw } from "lucide-react";
import type { ApiClient } from "../services/api";
import {
  store,
  accountScope,
  visitScope,
  enqueueLocal,
  flushLocal,
} from "../services/storage";
import { gpsService } from "../services/native";
import type {
  LocalPhoto,
  PointDraft,
  Report,
  ReportDraft,
  User,
  Visit,
} from "../types";
import type { Route } from "../components/ui";
import {
  Badge,
  Card,
  Empty,
  Field,
  Message,
  Meter,
  Steps,
} from "../components/ui";
import {
  editable,
  period,
  pointEvidence,
  progress,
  reportForSave,
  samplingFloors,
  statusLabels,
  when,
} from "../domain";
import { ReportForm } from "./ReportForm";
import { SamplingDetail } from "./SamplingDetail";
import { SyncPanel } from "../components/SyncPanel";
import { ReviewInspectionSummary } from "../components/ReviewInspectionSummary";
type Props = {
  api: ApiClient;
  user: User;
  visitId: string;
  route: Route;
  go: (route: Route) => void;
  online: boolean;
  onVisit: (v: Visit) => void;
};
export function VisitWorkspace({
  api,
  user,
  visitId,
  route,
  go,
  online,
  onVisit,
}: Props) {
  const key = visitScope(accountScope(api.origin, user.id), visitId);
  const [visit, setVisit] = useState<Visit | null>(null),
    [draft, setDraft] = useState<ReportDraft>(),
    [notes, setNotes] = useState<Record<string, PointDraft>>({}),
    [photos, setPhotos] = useState<LocalPhoto[]>([]),
    [error, setError] = useState(""),
    [sync, setSync] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [reload, setReload] = useState(0),
    [cached, setCached] = useState(false),
    [pointId, setPointId] = useState(""),
    [gpsException, setGpsException] = useState("");
  const writes = useRef(Promise.resolve()),
    pending = useRef(0),
    reportVersion = useRef<number | null>(null);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void (async () => {
      try {
        await flushLocal(key).catch((err: Error) => {
          if (active) setError(err.message);
        });
        const [localReport, localNotes, localPhotos] = await Promise.all([
          store.get<ReportDraft>(key + "report"),
          store.get<Record<string, PointDraft>>(key + "notes"),
          store.get<LocalPhoto[]>(key + "photos"),
        ]);
        if (!active) return;
        setDraft(localReport);
        reportVersion.current = localReport?.version ?? null;
        setNotes(localNotes || {});
        setPhotos(localPhotos || []);
      } catch (err) {
        if (active) setError((err as Error).message);
      }
      try {
        const fresh = await api.visit(visitId);
        if (!active) return;
        setVisit(fresh);
        setCached(false);
        try {
          await store.put(key + "cache", fresh);
        } catch (err) {
          if (active) setError((err as Error).message);
        }
      } catch (err) {
        if (!active) return;
        setError((err as Error).message);
        try {
          const previous = await store.get<Visit>(key + "cache");
          if (active && previous) {
            setVisit(previous);
            setCached(true);
          }
        } catch (storageError) {
          if (active) setError((storageError as Error).message);
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [api, visitId, key, reload]);
  const persist = (operation: () => Promise<void>) => {
    pending.current++;
    setSync("Menyimpan draf lokal…");
    const task = enqueueLocal(key, operation);
    writes.current = task;
    void task.then(
      () => {
        pending.current--;
        if (!pending.current)
          setSync("Draf lokal tersimpan · perubahan belum disinkronkan");
      },
      (err) => {
        pending.current--;
        setSync("Gagal menyimpan draf lokal");
        setError((err as Error).message);
      },
    );
    return task;
  };
  const accept = async (updated: Visit) => {
    setVisit(updated);
    setCached(false);
    onVisit(updated);
    try {
      await store.put(key + "cache", updated);
    } catch (err) {
      setError((err as Error).message);
    }
  };
  if (loading) return <p role="status">Memuat kunjungan dan draf lokal…</p>;
  if (!visit)
    return (
      <Card>
        <Message error>{error || "Kunjungan belum tersedia."}</Message>
        <button className="secondary" onClick={() => setReload((v) => v + 1)}>
          Coba lagi
        </button>
      </Card>
    );
  const canEdit = editable(visit, user.id),
    totals = progress(visit),
    floors = samplingFloors(visit.devices),
    points = floors.flatMap((f) => f.points),
    point = points.find((p) => p.id === pointId),
    report = draft?.report || visit.report;
  const checkIn = async (exception = false) => {
    setBusy(true);
    setError("");
    try {
      if (!online) throw new Error("Check-in memerlukan koneksi server.");
      const data = exception
        ? {
            expected_version: visit.version,
            device_time: new Date().toISOString(),
            gps_exception_reason: gpsException.trim(),
          }
        : { expected_version: visit.version, ...(await gpsService.current()) };
      await accept(await api.checkIn(visit.id, data));
      setSync("Check-in tersimpan di server.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const updateReport = (r: Report) => {
    if (!canEdit || busy) return;
    const next = {
      report: r,
      version: reportVersion.current ?? visit.version,
      updatedAt: new Date().toISOString(),
    };
    reportVersion.current = next.version;
    setDraft(next);
    void persist(() => store.put(key + "report", next));
  };
  const saveReport = async () => {
    if (!draft || !canEdit) return;
    setBusy(true);
    setError("");
    try {
      if (!online)
        throw new Error(
          "Offline. Draf tetap lokal; simpan ke server ketika koneksi tersedia.",
        );
      await writes.current;
      const updated = await api.saveReport(
        visit.id,
        draft.version,
        reportForSave(draft.report),
      );
      await accept(updated);
      await store.remove(key + "report");
      reportVersion.current = null;
      setDraft(undefined);
      setSync("Laporan tersimpan di server.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const local = !!draft || Object.keys(notes).length > 0 || photos.length > 0;
  return (
    <div className="stack">
      <Steps active={route} go={go} />
      <div className="context-row">
        <span>
          {visit.site?.name || "Hotel"} · {period(visit.planned_date)}
        </span>
        <button
          className="icon-button light"
          aria-label="Muat ulang kunjungan"
          disabled={busy}
          onClick={() => {
            void writes.current
              .catch(() => {})
              .then(() => setReload((n) => n + 1));
          }}
        >
          <RefreshCw size={17} />
        </button>
      </div>
      <SyncPanel
        local={local}
        status={sync}
        error={error}
        cached={cached}
        draftVersion={draft?.version}
        versionConflict={!!draft && draft.version !== visit.version}
      />
      {route === "hotel" ? (
        <>
          <Card
            title="Informasi hotel"
            action={<Badge>{statusLabels[visit.status]}</Badge>}
          >
            <h2>{visit.site?.name}</h2>
            <p className="muted">
              {visit.site?.address || "Alamat belum tersedia"}
            </p>
            <dl className="info-list">
              <div>
                <dt>Periode PM</dt>
                <dd>{period(visit.planned_date)}</dd>
              </div>
              <div>
                <dt>Teknisi</dt>
                <dd>{user.name}</dd>
              </div>
              <div>
                <dt>PIC</dt>
                <dd>{visit.report.pic_name || "Belum tersedia"}</dd>
              </div>
              <div>
                <dt>Check-in</dt>
                <dd>{when(visit.checkin?.server_time)}</dd>
              </div>
            </dl>
            <Meter {...totals} />
          </Card>
          {visit.status === "assigned" && (
            <Card title="Check-in GPS">
              <p className="muted">
                Lokasi aktual diminta saat check-in. Tidak ada koordinat
                default.
              </p>
              <button
                className="primary wide"
                disabled={busy || !online}
                onClick={() => void checkIn()}
              >
                <MapPin size={18} />
                {busy ? "Memproses…" : "Check-in dengan GPS"}
              </button>
              <details>
                <summary>GPS tidak tersedia?</summary>
                <Field label="Alasan pengecualian GPS">
                  <textarea
                    value={gpsException}
                    onChange={(e) => setGpsException(e.target.value)}
                    maxLength={1000}
                  />
                </Field>
                <button
                  className="secondary wide"
                  disabled={busy || !online || !gpsException.trim()}
                  onClick={() => void checkIn(true)}
                >
                  Check-in dengan alasan
                </button>
              </details>
            </Card>
          )}
          <Card title="Tahapan maintenance">
            <div className="stage-list">
              {(
                [
                  [
                    "report",
                    "Laporan Utama",
                    visit.report.summary ? "Data tersimpan" : "Belum diperiksa",
                  ],
                  [
                    "floors",
                    "Sampling Wi-Fi",
                    totals.total
                      ? `${totals.done}/${totals.total} titik selesai`
                      : "Belum diperiksa",
                  ],
                  ["review", "Review Laporan", "PIC belum tersedia"],
                ] as const
              ).map(([r, label, status]) => (
                <button key={r} onClick={() => go(r)}>
                  <span>
                    {label}
                    <small>{status}</small>
                  </span>
                  <span>→</span>
                </button>
              ))}
            </div>
          </Card>
        </>
      ) : route === "report" ? (
        <ReportForm
          visit={visit}
          report={report}
          onChange={updateReport}
          save={() => void saveReport()}
          editable={canEdit}
          busy={busy}
          hasDraft={!!draft}
        />
      ) : route === "floors" ? (
        <>
          <div className="section-heading">
            <h2>Sampling per lantai</h2>
            <Badge>{floors.length} lantai</Badge>
          </div>
          <Card>
            <Meter {...totals} />
            <p className="muted">
              Default 4 titik per lantai dari AP kunjungan. Target kosong belum
              menjadi record server. Konfigurasi lantai lokal Web belum
              tersinkron ke Android.
            </p>
          </Card>
          {floors.map((f) => (
            <details className="floor-card" key={f.id} open>
              <summary>
                <div>
                  <h3>Lantai {f.name}</h3>
                  <small>
                    {f.points.filter((p) => pointEvidence(p).done).length}/
                    {f.points.length} titik selesai
                  </small>
                </div>
                <span>⌄</span>
              </summary>
              <div className="floor-points">
                {f.points.map((p) => {
                  const e = pointEvidence(p);
                  return (
                    <button
                      key={p.id}
                      onClick={() => {
                        setPointId(p.id);
                        go("point");
                      }}
                    >
                      <span>
                        {notes[p.id]?.location || p.name}
                        <small>
                          {p.item?.device.name ||
                            "Target lokal · belum terhubung"}
                        </small>
                      </span>
                      <Badge
                        tone={
                          e.problem ? "danger" : e.done ? "success" : "neutral"
                        }
                      >
                        {e.label}
                      </Badge>
                    </button>
                  );
                })}
              </div>
            </details>
          ))}
          {!floors.length && (
            <Card>
              <Empty title="Belum ada lantai sampling">
                Pilih AP sampling melalui Web Dashboard. Android belum memiliki
                master lantai/titik tersinkron.
              </Empty>
            </Card>
          )}
        </>
      ) : route === "point" && point ? (
        <SamplingDetail
          key={point.id}
          point={point}
          draft={notes[point.id]}
          photos={photos.filter((p) => p.pointId === point.id)}
          editable={canEdit}
          busy={busy}
          change={(value) => {
            if (!canEdit) return;
            const next = { ...notes, [point.id]: value };
            setNotes(next);
            void persist(() => store.put(key + "notes", next));
          }}
          addPhoto={async (blob, category, caption) => {
            if (!canEdit) throw new Error("Kunjungan hanya dapat dibaca.");
            if (
              !["image/jpeg", "image/png", "image/webp"].includes(blob.type) ||
              !blob.size ||
              blob.size > 10 * 1024 * 1024
            )
              throw new Error("Pilih foto JPEG/PNG/WebP maksimal 10 MiB.");
            if (photos.filter((p) => p.pointId === point.id).length >= 10)
              throw new Error("Maksimal 10 foto lokal per titik.");
            const photo: LocalPhoto = {
              id: crypto.randomUUID(),
              pointId: point.id,
              category,
              caption,
              createdAt: new Date().toISOString(),
              blob,
            };
            const next = [...photos, photo];
            await persist(() => store.put(key + "photos", next));
            setPhotos(next);
          }}
        />
      ) : route === "review" ? (
        <>
          <Card title="Ringkasan laporan">
            <p className="muted">Ringkasan dari laporan server.</p>
            <p className="report-text">
              {visit.report.summary || "Belum diperiksa"}
            </p>
            <button className="secondary" onClick={() => go("report")}>
              Tinjau laporan utama
            </button>
          </Card>
          <ReviewInspectionSummary report={visit.report} points={points} />
          <Card title="Cakupan sampling">
            <Meter {...totals} />
            <p className="muted">
              Selesai membutuhkan outcome, foto server dan speedtest Wi-Fi yang
              diterima / gagal beralasan. Ini proyeksi bukti, bukan validasi
              submit resmi.
            </p>
            {points.map((p) => (
              <div className="review-point" key={p.id}>
                <span>{p.name}</span>
                <Badge tone={pointEvidence(p).done ? "success" : "warning"}>
                  {pointEvidence(p).done ? "Selesai" : "Belum selesai"}
                </Badge>
              </div>
            ))}
          </Card>
          <Card title="Temuan">
            {points
              .filter((p) => pointEvidence(p).problem)
              .map((p) => (
                <p key={p.id}>
                  {p.name}:{" "}
                  {p.item?.result?.notes ||
                    pointEvidence(p).run?.error ||
                    "Keterangan belum tersedia"}
                </p>
              ))}
            {!points.some((p) => pointEvidence(p).problem) && (
              <p className="muted">
                {points.some((p) => p.item)
                  ? "Belum ada titik bermasalah pada data server."
                  : "Belum diperiksa"}
              </p>
            )}
            {Object.entries(notes)
              .filter(([, d]) => d.findings)
              .map(([id, d]) => (
                <p key={id}>
                  <Badge tone="warning">Temuan lokal</Badge> {d.findings}
                </p>
              ))}
          </Card>
          <Card title="Persetujuan PIC">
            <Badge>Belum tersedia</Badge>
            <p>PIC: {visit.report.pic_name || "Belum tersedia"}</p>
            <p className="muted">
              Approval supervisor bukan tanda tangan PIC. Review PIC, signature,
              submit V2 dan PDF Android belum terintegrasi.
            </p>
            <button disabled className="primary wide">
              Submit / tanda tangan · Belum tersedia
            </button>
            <p className="muted">
              Gunakan alur review existing di Web Dashboard untuk pekerjaan yang
              saat ini didukung.
            </p>
          </Card>
        </>
      ) : (
        <Card>
          <Empty title="Pilih titik sampling">
            <button className="secondary" onClick={() => go("floors")}>
              Lihat lantai
            </button>
          </Empty>
        </Card>
      )}
    </div>
  );
}
