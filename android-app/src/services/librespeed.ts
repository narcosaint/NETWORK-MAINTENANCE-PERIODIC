import { ApiClient, ApiError } from "./api";
import { store } from "./storage";
import {
  acquireWifiLease,
  nativeSpeedtestAvailable,
  type WifiLease,
} from "./wifiLease";
import { radioPayload } from "./wifi";
import {
  measureWithWorker,
  type SpeedProgress,
  type WorkerResult,
} from "./speedWorker";
import type {
  Point,
  Visit,
  SessionStart,
  SessionFinish,
  SamplingSpeedtestAttempt,
} from "../types";

export type SpeedtestOutbox = {
  start: SessionStart;
  attemptId?: string;
  finish?: SessionFinish;
};
type Reply = { attempt: SamplingSpeedtestAttempt; visit: Visit };
let active = false;
export const libreSpeedService = {
  capability() {
    return nativeSpeedtestAvailable()
      ? { available: true as const }
      : {
          available: false as const,
          reason:
            "Belum tersedia · speedtest membutuhkan plugin Android terbaru.",
        };
  },
};

async function startRequest(
  api: ApiClient,
  visitId: string,
  pointId: string,
  key: string,
  data: SessionStart,
) {
  try {
    return await api.startSessionSpeedtest(visitId, pointId, data);
  } catch (error) {
    // These responses reject the transaction definitively. A transport/500 error
    // is ambiguous, so retain the UUID for reconciliation instead.
    if (
      error instanceof ApiError &&
      [400, 401, 403, 404, 409, 422, 429].includes(error.status)
    )
      await store.remove(key);
    throw error;
  }
}

async function flushFinish(
  api: ApiClient,
  visitId: string,
  pointId: string,
  key: string,
  pending: SpeedtestOutbox,
): Promise<Reply> {
  if (!pending.attemptId || !pending.finish)
    throw new Error("Antrean hasil pengujian belum lengkap.");
  try {
    const result = await api.finishSessionSpeedtest(
      visitId,
      pointId,
      pending.attemptId,
      pending.finish,
    );
    await store.remove(key);
    return result;
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      const visit = await api.visit(visitId);
      const attempt = visit.sampling_coverage?.floors
        .flatMap((f) => f.points)
        .find((p) => p.id === pointId)
        ?.speedtests?.find((a) => a.id === pending.attemptId);
      if (attempt && attempt.status !== "running") {
        await store.remove(key);
        return { visit, attempt };
      }
    }
    throw error;
  }
}

export async function runSamplingSpeedtest(
  api: ApiClient,
  scope: string,
  visit: Visit,
  point: Point,
  signal: AbortSignal,
  progress: (value: SpeedProgress) => void,
  onVisit: (visit: Visit) => Promise<void>,
  dependencies = { acquire: acquireWifiLease, measure: measureWithWorker },
): Promise<Reply> {
  if (active) throw new Error("Pengujian lain masih berjalan.");
  if (!point.session)
    throw new Error("Titik belum mempunyai sesi sampling server.");
  active = true;
  const key = scope + "speedtest-outbox:" + point.id;
  let lease: WifiLease | undefined,
    released = false;
  try {
    const pending = await store.get<SpeedtestOutbox>(key);
    if (pending) {
      if (!pending.finish) {
        // Lost start response: never resume under an old binding/token.
        const replay = await startRequest(
          api,
          visit.id,
          point.id,
          key,
          pending.start,
        );
        pending.attemptId = replay.attempt.id;
        pending.finish = {
          result: {
            status: "aborted",
            metrics: null,
            error:
              "Pengujian sebelumnya tidak dapat dilanjutkan setelah respons/start terputus.",
          },
          connection: null,
          binding: null,
        };
        await store.put(key, pending);
      }
      const result = await flushFinish(api, visit.id, point.id, key, pending);
      await onVisit(result.visit);
      return result;
    }
    if (signal.aborted) throw new Error("Pengujian dibatalkan.");
    lease = await dependencies.acquire();
    if (signal.aborted) throw new Error("Pengujian dibatalkan.");
    const connection = radioPayload({
      connection: lease.connection,
    }).wifi_connection!;
    const start: SessionStart = {
      id: crypto.randomUUID(),
      expected_visit_version: visit.version,
      expected_session_version: point.session.version,
      connection,
      binding: lease.binding,
    };
    await store.put(key, { start } satisfies SpeedtestOutbox);
    const started = await startRequest(api, visit.id, point.id, key, start);
    const record: SpeedtestOutbox = { start, attemptId: started.attempt.id };
    await onVisit(started.visit);
    let result: WorkerResult = {
      status: "failed",
      metrics: null,
      error:
        "Tiket transfer tidak tersedia. Periksa riwayat dan ulangi pengujian.",
    };
    if (started.transfer) {
      try {
        if (!(await lease.check()))
          throw new Error("Binding Wi-Fi berubah sebelum transfer dimulai.");
        result = await dependencies.measure(
          started.transfer,
          api.origin,
          signal,
          lease.check,
          progress,
        );
      } catch (error) {
        result = {
          status: "failed",
          metrics: null,
          error: (error as Error).message,
        };
      }
    }
    let end: SessionFinish["connection"] = null,
      binding: SessionFinish["binding"] = null;
    if (result.status === "completed") {
      try {
        if (!(await lease.check()))
          throw new Error("Binding Wi-Fi tidak lagi valid saat selesai.");
        const after = await lease.snapshot();
        if (
          after.bssid?.toLowerCase() !== connection.bssid?.toLowerCase() ||
          after.frequencyMhz !== connection.frequency_mhz
        )
          throw new Error("AP/frekuensi Wi-Fi berubah selama pengujian.");
        end = radioPayload({ connection: after }).wifi_connection;
        binding = lease.binding;
      } catch (error) {
        result = {
          status: "failed",
          metrics: null,
          error: (error as Error).message,
        };
      }
    }
    // Worker is terminated before restoring the process network.
    try {
      await lease.release();
      released = true;
    } catch (error) {
      result = {
        status: "failed",
        metrics: null,
        error: (error as Error).message,
      };
      binding = null;
    }
    record.finish = { result, connection: end, binding };
    await store.put(key, record);
    const saved = await flushFinish(api, visit.id, point.id, key, record);
    await onVisit(saved.visit);
    return saved;
  } finally {
    if (lease && !released) await lease.release().catch(() => {});
    active = false;
  }
}
