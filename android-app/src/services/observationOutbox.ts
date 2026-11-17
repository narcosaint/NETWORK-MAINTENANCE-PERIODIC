import { ApiClient, ApiError } from "./api";
import { store } from "./storage";
import { radioPayload } from "./wifi";
import type {
  Point,
  PointDraft,
  Visit,
  SamplingNotes,
  ObservationSubmission,
  SamplingObservation,
} from "../types";

export function observationMatchesDraft(
  draft: PointDraft | undefined,
  fallback: SamplingNotes | undefined,
  observation: SamplingObservation,
) {
  if (
    JSON.stringify(observationNotes(draft, fallback)) !==
    JSON.stringify(observation.notes)
  )
    return false;
  if (!draft?.radio) return true;
  const normalize = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.map(normalize);
    if (value && typeof value === "object")
      return Object.fromEntries(
        Object.entries(value)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([key, val]) => [
            key,
            key === "observed_at" && typeof val === "string"
              ? new Date(val).toISOString()
              : normalize(val),
          ]),
      );
    return value;
  };
  return (
    JSON.stringify(normalize(radioPayload(draft.radio))) ===
    JSON.stringify(
      normalize({
        wifi_connection: observation.wifi_connection ?? null,
        wifi_scan: observation.wifi_scan ?? null,
      }),
    )
  );
}

export type PendingObservation = {
  payload: ObservationSubmission;
  conflict: boolean;
};
export function observationKey(scope: string, sessionId: string) {
  return scope + "observation-outbox:" + sessionId;
}
export function observationNotes(
  draft?: PointDraft,
  fallback?: SamplingNotes,
): SamplingNotes {
  const status = draft?.status || fallback?.condition || "untested";
  return {
    condition: ["good", "attention", "problem"].includes(status)
      ? (status as SamplingNotes["condition"])
      : "untested",
    notes: (draft?.notes ?? fallback?.notes ?? "").trim(),
    findings: (draft?.findings ?? fallback?.findings ?? "").trim(),
    action: (draft?.action ?? fallback?.action ?? "").trim(),
    recommendation: (
      draft?.recommendation ??
      fallback?.recommendation ??
      ""
    ).trim(),
  };
}

export async function submitObservation(
  api: ApiClient,
  scope: string,
  visit: Visit,
  point: Point,
  draft: PointDraft | undefined,
  online: boolean,
  rebase = false,
) {
  if (!point.session)
    throw new Error("Titik ini belum mempunyai sesi sampling server.");
  const key = observationKey(scope, point.id);
  let pending = await store.get<PendingObservation>(key);
  if (rebase) {
    if (!pending?.conflict)
      throw new Error(
        "Kirim ulang request sebelumnya dahulu untuk memastikan status penerimaan.",
      );
    if (
      pending.payload.expected_visit_version === visit.version &&
      pending.payload.expected_session_version === point.session.version
    )
      throw new Error(
        "Muat ulang kunjungan dan tinjau perubahan server dahulu.",
      );
    pending = undefined;
  }
  if (!pending) {
    const notes = observationNotes(draft, point.session.observation?.notes);
    if (["attention", "problem"].includes(notes.condition) && !notes.findings)
      throw new Error("Isi temuan untuk kondisi perlu perhatian/bermasalah.");
    pending = {
      conflict: false,
      payload: {
        id: crypto.randomUUID(),
        expected_visit_version: rebase
          ? visit.version
          : (draft?.baseVisitVersion ?? visit.version),
        expected_session_version: rebase
          ? point.session.version
          : (draft?.baseSessionVersion ?? point.session.version),
        captured_at: draft?.updatedAt || new Date().toISOString(),
        notes,
        ...(draft?.radio ? radioPayload(draft.radio) : {}),
      },
    };
    await store.put(key, pending);
  }
  if (!online)
    throw new Error(
      "Catatan tersimpan dalam antrean perangkat. Kirim kembali saat online.",
    );
  try {
    const result = await api.saveObservation(
      visit.id,
      point.id,
      pending.payload,
    );
    await store.remove(key);
    return result;
  } catch (error) {
    if (error instanceof ApiError && error.status === 409)
      await store.put(key, { ...pending, conflict: true });
    throw error;
  }
}
