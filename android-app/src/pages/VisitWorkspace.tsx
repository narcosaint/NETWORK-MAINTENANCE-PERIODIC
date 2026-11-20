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
import { CompletionPanel } from "../components/CompletionPanel";
import {
  ObservationConflictCard,
  type ObservationConflict,
} from "../components/ObservationConflictCard";
import { EvidencePanel } from "../components/EvidencePanel";
import { uploadPhoto } from "../services/completion";
import { FieldLocationForm } from "../components/FieldLocationForm";
import { ReportForm } from "./ReportForm";
import { SamplingDetail } from "./SamplingDetail";
import { SyncPanel } from "../components/SyncPanel";
import { ReviewInspectionSummary } from "../components/ReviewInspectionSummary";
import { radioFromObservation } from "../services/wifi";
import { combinedAreaNotes } from "../services/areaNotes";
import { reportSamplingFailure } from "../services/samplingSpeedtests";
import { runSamplingSpeedtest } from "../services/librespeed";
import {
  submitLatestObservation,
  observationMatchesDraft,
  observationKey,
  type PendingObservation,
} from "../services/observationOutbox";
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
  const [pointTab, setPointTab] = useState("analyzer");
  const [noteConflict, setNoteConflict] = useState(false);
  const [observationConflict, setObservationConflict] =
    useState<ObservationConflict>();
  const writes = useRef(Promise.resolve()),
    pending = useRef(0),
    reportVersion = useRef<number | null>(null);
  useEffect(() => {
    let active = true;
    if (pointId)
      void store
        .get<PendingObservation>(observationKey(key, pointId))
        .then((pending) => {
          if (active) setNoteConflict(!!pending?.conflict);
        })
        .catch(() => {});
    return () => {
      active = false;
    };
  }, [key, pointId]);
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
    floors = samplingFloors(visit.devices, visit.sampling_coverage),
    points = floors.flatMap((f) => f.points),
    point = points.find((p) => p.id === pointId),
    report = canEdit ? draft?.report || visit.report : visit.report;
  const appendPhotos = async (
    files: Blob[],
    pointId: string,
    category: string,
    caption: string,
  ) => {
    if (!canEdit) throw new Error("Kunjungan hanya dapat dibaca.");
    if (
      files.some(
        (file) =>
          !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
          !file.size ||
          file.size > 10 * 1024 * 1024,
      )
    )
      throw new Error("Pilih foto JPEG/PNG/WebP maksimal 10 MiB per foto.");
    await persist(async () => {
      const existing = (await store.get<LocalPhoto[]>(key + "photos")) || [];
      const remote = (visit.evidence || []).filter(
        (p) =>
          (p.session_id || "infrastructure") === pointId &&
          (pointId !== "infrastructure" || p.category === category),
      ).length;
      if (
        existing.filter(
          (p) =>
            p.pointId === pointId &&
            (pointId !== "infrastructure" || p.category === category),
        ).length +
          remote +
          files.length >
        10
      )
        throw new Error(
          "Maksimal 10 foto per area atau kategori dokumentasi utama.",
        );
      const next = [
        ...existing,
        ...files.map((blob) => ({
          id: crypto.randomUUID(),
          pointId,
          category,
          caption,
          createdAt: new Date().toISOString(),
          blob,
        })),
      ];
      await store.put(key + "photos", next);
      setPhotos(next);
    });
  };
  const captureConflict = (error: unknown) => {
    const detail = (error as { detail?: ObservationConflict }).detail;
    if (detail?.code === "sampling_notes_conflict")
      setObservationConflict(detail);
  };
  const resolveConflict = async (local: boolean) => {
    if (!observationConflict) return;
    setBusy(true);
    try {
      await flushLocal(key);
      const id = observationConflict.session_id;
      const saved =
        (await store.get<Record<string, PointDraft>>(key + "notes")) || {};
      const pendingKey = observationKey(key, id);
      const pendingRequest = await store.get<PendingObservation>(pendingKey);
      if (pendingRequest && !pendingRequest.conflict)
        throw new Error(
          "Pastikan status kiriman sebelumnya sebelum mengganti draf.",
        );
      await store.put(key + "recovery:" + crypto.randomUUID(), {
        draft: saved[id],
        pendingRequest,
        conflict: observationConflict,
      });
      const selected = { ...observationConflict.merged_notes };
      if (local)
        for (const field of observationConflict.fields) {
          if (field === "condition")
            selected.condition = observationConflict.requested_notes.condition;
          else selected[field] = observationConflict.requested_notes[field];
        }
      saved[id] = {
        ...saved[id],
        ...selected,
        status: selected.condition,
        combinedNotes: false,
        baseNotes: observationConflict.current_notes,
        baseVisitVersion: observationConflict.current_visit_version,
        baseSessionVersion: observationConflict.current_session_version,
        updatedAt: new Date().toISOString(),
      };
      await store.put(key + "notes", saved);
      await store.remove(pendingKey);
      setNotes(saved);
      setObservationConflict(undefined);
      setError("");
      setSync(
        "Pilihan tersimpan sebagai draf. Tekan Review Hasil PDF atau Simpan Hasil untuk melanjutkan.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const prepareReview = async (): Promise<Visit> => {
    setBusy(true);
    try {
      await flushLocal(key);
      let current = await api.visit(visit.id);
      await accept(current);
      const localReport = await store.get<ReportDraft>(key + "report");
      if (localReport) {
        if (
          JSON.stringify(reportForSave(localReport.report)) !==
          JSON.stringify(reportForSave(current.report))
        ) {
          if (
            localReport.version !== current.version &&
            JSON.stringify(localReport.baseReport) !==
              JSON.stringify(current.report)
          )
            throw new Error(
              "Draf laporan berbeda dari server. Tinjau Laporan Utama dan simpan terlebih dahulu.",
            );
          current = await api.saveReport(
            current.id,
            current.version,
            reportForSave(localReport.report),
          );
          await accept(current);
        }
        await store.remove(key + "report");
        setDraft(undefined);
        reportVersion.current = null;
      }
      const pendingNotes =
        (await store.get<Record<string, PointDraft>>(key + "notes")) || {};
      for (const [id, value] of Object.entries(pendingNotes)) {
        const area = samplingFloors(current.devices, current.sampling_coverage)
          .flatMap((f) => f.points)
          .find((p) => p.id === id);
        if (!area?.session)
          throw new Error(
            "Draf area tidak lagi tersedia. Tinjau Network Test sebelum melanjutkan.",
          );
        if (
          (await store.get(observationKey(key, id))) ||
          !area.session.observation ||
          !observationMatchesDraft(
            value,
            area.session.observation.notes,
            area.session.observation,
          )
        ) {
          const response = await submitLatestObservation(
            api,
            key,
            current,
            area,
            value,
            true,
          );
          current = response.visit;
          await accept(current);
        }
        delete pendingNotes[id];
        await store.put(key + "notes", { ...pendingNotes });
        setNotes({ ...pendingNotes });
      }
      let pendingPhotos = (await store.get<LocalPhoto[]>(key + "photos")) || [];
      for (const photo of [...pendingPhotos]) {
        const response = await uploadPhoto(api, current, photo);
        current = response.visit;
        await accept(current);
        pendingPhotos = pendingPhotos.filter((p) => p.id !== photo.id);
        await store.put(key + "photos", pendingPhotos);
        setPhotos(pendingPhotos);
      }
      setError("");
      setSync("Seluruh perubahan tersimpan di server.");
      return current;
    } catch (e) {
      captureConflict(e);
      throw e;
    } finally {
      setBusy(false);
    }
  };
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
      baseReport: draft?.baseReport || visit.report,
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
      const current = await api.visit(visit.id);
      if (
        draft.version !== current.version &&
        JSON.stringify(draft.baseReport) !== JSON.stringify(current.report)
      )
        throw new Error(
          "Laporan server berubah. Tinjau perubahan sebelum menyimpan draf.",
        );
      const updated = await api.saveReport(
        visit.id,
        current.version,
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
  const savePointNotes = async (rebase = false) => {
    if (!point?.session || !canEdit) return;
    setBusy(true);
    setError("");
    try {
      await writes.current;
      const result = await submitLatestObservation(
        api,
        key,
        visit,
        point,
        notes[point.id],
        online,
        rebase,
      );
      await accept(result.visit);
      const next = { ...notes };
      delete next[point.id];
      await store.put(key + "notes", next);
      setNotes(next);
      setNoteConflict(false);
      let current = result.visit;
      let pendingPhotos = (await store.get<LocalPhoto[]>(key + "photos")) || [];
      for (const photo of pendingPhotos.filter((p) => p.pointId === point.id)) {
        const uploaded = await uploadPhoto(api, current, photo);
        current = uploaded.visit;
        await accept(current);
        pendingPhotos = pendingPhotos.filter((p) => p.id !== photo.id);
        await store.put(key + "photos", pendingPhotos);
        setPhotos(pendingPhotos);
      }
      setSync("Hasil area tersimpan di server.");
    } catch (error) {
      captureConflict(error);
      setError((error as Error).message);
      try {
        setNoteConflict(
          !!(await store.get<PendingObservation>(observationKey(key, point.id)))
            ?.conflict,
        );
      } catch {
        /* Keep original error. */
      }
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
        versionConflict={
          !!draft &&
          draft.version !== visit.version &&
          JSON.stringify(draft.baseReport) !== JSON.stringify(visit.report)
        }
      />
      {observationConflict && (
        <ObservationConflictCard
          conflict={observationConflict}
          name={
            points.find((p) => p.id === observationConflict.session_id)?.name ||
            ""
          }
          busy={busy}
          resolve={(local) => void resolveConflict(local)}
        />
      )}
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
                    "Network Test",
                    totals.total
                      ? `${totals.done}/${totals.total} area selesai`
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
            <h2>Test per lantai</h2>
            <Badge>{points.length} area</Badge>
          </div>
          <Card>
            <Meter {...totals} />
            <p className="muted">
              {visit.sampling_coverage ? (
                "Setiap area menyimpan hasil Wi-Fi dan speedtest sendiri. Teknisi dapat menambah lantai dan area aktual di bawah."
              ) : (
                <>
                  Lantai dan area mengikuti lokasi yang diperiksa. Tambahkan
                  area. Master lantai dan sesi pengujian belum tersedia pada
                  kunjungan ini. Supervisor mengatur lantai melalui Data Hotel
                  di Web.
                </>
              )}
            </p>
          </Card>
          {canEdit && (
            <FieldLocationForm
              api={api}
              scope={key}
              visit={visit}
              online={online}
              busy={busy}
              onVisit={accept}
            />
          )}
          {floors.map((f) => (
            <details className="floor-card" key={f.id} open>
              <summary>
                <div>
                  <h3>Lantai {f.name}</h3>
                  <small>
                    {f.points.filter((p) => pointEvidence(p).done).length}/
                    {f.points.length} area selesai
                  </small>
                </div>
                <span>⌄</span>
              </summary>
              <div className="floor-points">
                {f.points.map((p) => {
                  const e = pointEvidence(p);
                  return (
                    <div key={p.id} className="area-row">
                      <button
                        onClick={() => {
                          setPointTab("analyzer");
                          setPointId(p.id);
                          setNoteConflict(false);
                          go("point");
                        }}
                      >
                        <span>
                          {notes[p.id]?.location || p.name}
                          <small>{"Wi-Fi yang terhubung ke HP"}</small>
                        </span>
                        <Badge
                          tone={
                            e.problem
                              ? "danger"
                              : e.done
                                ? "success"
                                : "neutral"
                          }
                        >
                          {e.label}
                        </Badge>
                      </button>
                      {canEdit &&
                        p.session &&
                        !p.session.observation &&
                        !p.session.speedtests?.length &&
                        !notes[p.id] &&
                        !photos.some((photo) => photo.pointId === p.id) &&
                        !visit.evidence?.some(
                          (photo) => photo.session_id === p.id,
                        ) && (
                          <button
                            className="secondary"
                            disabled={busy}
                            onClick={async () => {
                              if (
                                !window.confirm(
                                  "Hapus area kosong ini dari daftar pemeriksaan?",
                                )
                              )
                                return;
                              setBusy(true);
                              try {
                                const response = await api.request<{
                                  visit: Visit;
                                }>(
                                  `/hotel-visits/${visit.id}/sampling-sessions/${p.id}/remove`,
                                  "POST",
                                  {
                                    id: crypto.randomUUID(),
                                    expected_visit_version: visit.version,
                                    expected_session_version:
                                      p.session!.version,
                                  },
                                );
                                await accept(response.visit);
                              } catch (e) {
                                setError((e as Error).message);
                              } finally {
                                setBusy(false);
                              }
                            }}
                          >
                            Hapus area kosong
                          </button>
                        )}
                    </div>
                  );
                })}
              </div>
            </details>
          ))}
          {!floors.length && (
            <Card>
              <Empty title="Belum ada lantai sampling">
                Check-in lalu gunakan Tambah Area untuk memasukkan lokasi
                pengujian.
              </Empty>
            </Card>
          )}
        </>
      ) : route === "point" && point ? (
        <SamplingDetail
          key={point.id}
          point={point}
          areas={floors.flatMap((f) =>
            f.points.map((p) => ({ id: p.id, name: `${f.name} · ${p.name}` })),
          )}
          initialTab={pointTab}
          selectArea={(id) => {
            setPointTab("notes");
            setPointId(id);
          }}
          draft={notes[point.id]}
          photos={photos.filter((p) => p.pointId === point.id)}
          startTest={
            point.session &&
            visit.sampling_coverage?.session_speedtests_enabled &&
            api.origin.startsWith("https://")
              ? async (signal, progress) => {
                  if (!canEdit)
                    throw new Error("Kunjungan hanya dapat dibaca.");
                  setBusy(true);
                  setError("");
                  try {
                    await writes.current;
                    const saved = await runSamplingSpeedtest(
                      api,
                      key,
                      visit,
                      point,
                      signal,
                      progress,
                      accept,
                    );
                    const local = notes[point.id];
                    if (
                      local &&
                      saved.visit.version === visit.version + 2 &&
                      local.baseVisitVersion === visit.version &&
                      local.baseSessionVersion === point.session?.version
                    ) {
                      const current = saved.visit.sampling_coverage?.floors
                        .flatMap((f) => f.points)
                        .find((p) => p.id === point.id);
                      const next = {
                        ...notes,
                        [point.id]: {
                          ...local,
                          baseVisitVersion: saved.visit.version,
                          baseSessionVersion: current?.version,
                          radio: {
                            ...local.radio,
                            ...radioFromObservation(current?.observation),
                          },
                        },
                      };
                      await persist(() => store.put(key + "notes", next));
                      setNotes(next);
                    }
                    setSync(
                      saved.attempt.status === "completed"
                        ? "Hasil Wi-Fi dan speedtest area tersimpan."
                        : saved.attempt.error || "Pengujian dihentikan.",
                    );
                  } finally {
                    setBusy(false);
                  }
                }
              : undefined
          }
          reportFailure={
            point.session && visit.sampling_coverage?.session_speedtests_enabled
              ? async (rebase) => {
                  if (!canEdit) return;
                  setBusy(true);
                  setError("");
                  try {
                    await writes.current;
                    const result = await reportSamplingFailure(
                      api,
                      key,
                      visit,
                      point,
                      notes[point.id] || {
                        updatedAt: new Date().toISOString(),
                      },
                      online,
                      rebase,
                    );
                    await accept(result.visit);
                    if (
                      notes[point.id]?.failedTestReason?.trim() ===
                      result.attempt.error
                    ) {
                      const next = { ...notes },
                        remaining = { ...next[point.id] };
                      delete remaining.failedTestReason;
                      const keys = Object.keys(remaining).filter(
                        (key) =>
                          ![
                            "updatedAt",
                            "baseVisitVersion",
                            "baseSessionVersion",
                          ].includes(key),
                      );
                      if (keys.length) next[point.id] = remaining;
                      else delete next[point.id];
                      await store.put(key + "notes", next);
                      setNotes(next);
                    }
                    setSync(
                      "Alasan gagal uji tersimpan. Lengkapi tindakan dan dokumentasi sebelum submit.",
                    );
                  } finally {
                    setBusy(false);
                  }
                }
              : undefined
          }
          captureRadio={async (radio) => {
            if (!canEdit) throw new Error("Kunjungan hanya dapat dibaca.");
            const value = {
              ...notes[point.id],
              radio: { ...notes[point.id]?.radio, ...radio },
              baseVisitVersion:
                notes[point.id]?.baseVisitVersion ?? visit.version,
              baseSessionVersion:
                notes[point.id]?.baseSessionVersion ?? point.session?.version,
              updatedAt: new Date().toISOString(),
            };
            const next = { ...notes, [point.id]: value };
            await persist(() => store.put(key + "notes", next));
            setNotes(next);
          }}
          editable={canEdit}
          busy={busy}
          saveNotes={
            point.session && visit.sampling_coverage?.observations_enabled
              ? () => void savePointNotes()
              : undefined
          }
          rebaseNotes={
            noteConflict ? () => void savePointNotes(true) : undefined
          }
          change={(value) => {
            if (!canEdit) return;
            const next = {
              ...notes,
              [point.id]: {
                ...value,
                baseNotes:
                  notes[point.id]?.baseNotes ||
                  point.session?.observation?.notes,
                baseVisitVersion:
                  notes[point.id]?.baseVisitVersion ?? visit.version,
                baseSessionVersion:
                  notes[point.id]?.baseSessionVersion ?? point.session?.version,
              },
            };
            setNotes(next);
            void persist(() => store.put(key + "notes", next));
          }}
          addPhoto={async (blob, category, caption) =>
            appendPhotos([blob], point.id, category, caption)
          }
          remotePhotos={
            (visit.evidence || []).filter(
              (photo) => photo.session_id === point.id,
            ).length
          }
          addPhotos={async (files, category, caption) =>
            appendPhotos(files, point.id, category, caption)
          }
        />
      ) : route === "review" ? (
        <>
          <Card title="Ringkasan laporan">
            <p className="report-text">{report.summary || "Belum diperiksa"}</p>
            <button className="secondary" onClick={() => go("report")}>
              Tinjau laporan utama
            </button>
          </Card>
          <ReviewInspectionSummary report={report} points={points} />
          <Card title="Ringkasan Network Test">
            <Meter {...totals} />
            <p className="muted">
              Status setiap area mengikuti hasil pengujian yang tersimpan.
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
          <Card title="Temuan dan Tindakan">
            {points
              .filter(
                (p) =>
                  combinedAreaNotes(
                    notes[p.id],
                    p.session?.observation?.notes,
                  ) || pointEvidence(p).problem,
              )
              .map((p) => (
                <p key={p.id}>
                  {p.name}:{" "}
                  {combinedAreaNotes(
                    notes[p.id],
                    p.session?.observation?.notes,
                  ) ||
                    p.item?.result?.notes ||
                    pointEvidence(p).run?.error ||
                    "Keterangan belum tersedia"}
                </p>
              ))}
            {!points.some(
              (p) =>
                combinedAreaNotes(notes[p.id], p.session?.observation?.notes) ||
                pointEvidence(p).problem,
            ) && (
              <p className="muted">
                Belum ada temuan atau tindakan yang dicatat.
              </p>
            )}
          </Card>
          <EvidencePanel
            api={api}
            visit={visit}
            photos={photos}
            busy={busy}
            online={online}
            editable={canEdit}
            addPhotos={async (values) =>
              appendPhotos(
                values.map((photo) => photo.blob),
                "infrastructure",
                values[0].category,
                values[0].caption,
              )
            }
            removePhoto={async (photo) => {
              const next = photos.filter((p) => p.id !== photo.id);
              await persist(() => store.put(key + "photos", next));
              setPhotos(next);
            }}
            upload={async (photo) => {
              if (busy) return;
              setBusy(true);
              try {
                await flushLocal(key);
                const response = await uploadPhoto(api, visit, photo);
                await accept(response.visit);
                const next = photos.filter((p) => p.id !== photo.id);
                await store.put(key + "photos", next);
                setPhotos(next);
                setSync("Foto diterima server dan siap dimasukkan ke PDF.");
              } finally {
                setBusy(false);
              }
            }}
          />
          <CompletionPanel
            api={api}
            visit={visit}
            scope={key}
            online={online}
            busy={busy}
            blocked={local}
            prepare={prepareReview}
            onVisit={accept}
          />
        </>
      ) : (
        <Card>
          <Empty title="Pilih area sampling">
            <button className="secondary" onClick={() => go("floors")}>
              Lihat lantai
            </button>
          </Empty>
        </Card>
      )}
    </div>
  );
}
