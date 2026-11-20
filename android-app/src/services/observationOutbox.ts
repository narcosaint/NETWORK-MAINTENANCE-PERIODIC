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
  if (!sameNotes(observationNotes(draft, fallback), observation.notes))
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

export function sameNotes(a: SamplingNotes, b: SamplingNotes) {
  return (Object.keys(a) as (keyof SamplingNotes)[]).every(
    (key) => a[key] === b[key],
  );
}

function newerRadio(
  draft: PointDraft | undefined,
  observation?: SamplingObservation | null,
) {
  if (!draft?.radio) return false;
  const payload = radioPayload(draft.radio);
  return (["wifi_connection", "wifi_scan"] as const).some((key) => {
    const incoming = payload[key],
      saved = observation?.[key];
    return (
      !!incoming &&
      (!saved ||
        new Date(incoming.observed_at).getTime() >
          new Date(saved.observed_at).getTime())
    );
  });
}

export async function submitLatestObservation(
  api: ApiClient,
  scope: string,
  visit: Visit,
  point: Point,
  draft: PointDraft | undefined,
  online: boolean,
  rebase = false,
) {
  let result: Awaited<ReturnType<typeof submitObservation>>;
  try {
    result = await submitObservation(
      api,
      scope,
      visit,
      point,
      draft,
      online,
      rebase,
    );
  } catch (error) {
    const detail =
      error instanceof ApiError
        ? (error.detail as { code?: string } | undefined)
        : undefined;
    const pending = await store.get<PendingObservation>(
      observationKey(scope, point.id),
    );
    if (
      detail?.code !== "sampling_notes_conflict" ||
      !pending?.conflict ||
      sameNotes(
        observationNotes(draft, point.session?.observation?.notes),
        pending.payload.notes,
      )
    )
      throw error;
    // A definite rejection can be replaced by the newer draft; ambiguous sends keep their UUID.
    await store.put(
      scope + "rejected-observation:" + pending.payload.id,
      pending,
    );
    await store.remove(observationKey(scope, point.id));
    result = await submitObservation(api, scope, visit, point, draft, online);
  }
  const refreshed = result.visit.sampling_coverage?.floors
    .flatMap((f) => f.points)
    .find((p) => p.id === point.id);
  const desired = observationNotes(draft, point.session?.observation?.notes);
  if (
    !sameNotes(desired, result.submittedNotes) ||
    newerRadio(draft, refreshed?.observation)
  ) {
    const current = refreshed
      ? { id: refreshed.id, name: refreshed.name, session: refreshed }
      : point;
    const next = { ...result.observation.notes };
    for (const field of Object.keys(desired) as (keyof SamplingNotes)[]) {
      if (desired[field] !== result.submittedNotes[field]) {
        if (field === "condition") next.condition = desired.condition;
        else next[field] = desired[field];
      }
    }
    result = await submitObservation(
      api,
      scope,
      result.visit,
      current,
      {
        ...draft,
        ...next,
        status: next.condition,
        updatedAt: draft?.updatedAt || new Date().toISOString(),
        baseNotes: result.observation.notes,
        baseSessionVersion: result.observation.session_version,
        baseVisitVersion: result.visit.version,
      },
      online,
    );
  }
  return result;
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
    const measured = draft?.radio ? radioPayload(draft.radio) : undefined;
    const radio: Pick<ObservationSubmission, "wifi_connection" | "wifi_scan"> =
      {};
    if (measured)
      for (const key of ["wifi_connection", "wifi_scan"] as const) {
        const value = measured[key],
          saved = point.session.observation?.[key];
        if (
          value &&
          (!saved ||
            new Date(value.observed_at).getTime() >
              new Date(saved.observed_at).getTime())
        ) {
          Object.assign(radio, { [key]: value });
        }
      }
    if (
      ["attention", "problem"].includes(notes.condition) &&
      !notes.findings &&
      !notes.notes
    )
      throw new Error("Isi temuan untuk kondisi perlu perhatian/bermasalah.");
    pending = {
      conflict: false,
      payload: {
        id: crypto.randomUUID(),
        expected_visit_version: rebase
          ? visit.version
          : (draft?.baseVisitVersion ?? visit.version),
        expected_session_version:
          rebase ||
          (draft?.baseNotes &&
            JSON.stringify(draft.baseNotes) ===
              JSON.stringify(point.session.observation?.notes))
            ? point.session.version
            : (draft?.baseSessionVersion ?? point.session.version),
        captured_at: draft?.updatedAt || new Date().toISOString(),
        notes,
        ...radio,
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
    return { ...result, submittedNotes: pending.payload.notes };
  } catch (error) {
    if (error instanceof ApiError && error.status === 409)
      await store.put(key, { ...pending, conflict: true });
    throw error;
  }
}
