import { ApiClient, ApiError } from "./api";
import { store } from "./storage";
import type { Point, PointDraft, Visit, SpeedtestFailure } from "../types";
export type PendingFailure = { payload: SpeedtestFailure; conflict: boolean };
export async function reportSamplingFailure(
  api: ApiClient,
  scope: string,
  visit: Visit,
  point: Point,
  draft: PointDraft,
  online: boolean,
  rebase = false,
) {
  if (!point.session) throw new Error("Titik belum mempunyai sesi server.");
  const key = scope + "speedtest-failure-outbox:" + point.id;
  let pending = await store.get<PendingFailure>(key);
  if (rebase) {
    if (!pending?.conflict)
      throw new Error("Pastikan penerimaan kiriman sebelumnya dahulu.");
    if (
      pending.payload.expected_visit_version === visit.version &&
      pending.payload.expected_session_version === point.session.version
    )
      throw new Error("Muat ulang kunjungan dan tinjau riwayat dahulu.");
    pending = undefined;
  }
  if (!pending) {
    const reason = draft.failedTestReason?.trim();
    if (!reason) throw new Error("Isi alasan pengujian gagal.");
    pending = {
      conflict: false,
      payload: {
        id: crypto.randomUUID(),
        reason,
        expected_visit_version: rebase
          ? visit.version
          : (draft.baseVisitVersion ?? visit.version),
        expected_session_version: rebase
          ? point.session.version
          : (draft.baseSessionVersion ?? point.session.version),
      },
    };
    await store.put(key, pending);
  }
  if (!online)
    throw new Error(
      "Alasan gagal tersimpan dalam antrean. Kirim kembali saat online.",
    );
  try {
    const result = await api.reportSpeedtestFailure(
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
