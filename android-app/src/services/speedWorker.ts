import type { SpeedMetrics, TransferRun } from "../types";
export type SpeedProgress = {
  stage: string;
  download: number | null;
  upload: number | null;
  ping: number | null;
  jitter: number | null;
};
export type WorkerResult = {
  status: "completed" | "failed" | "aborted";
  metrics: SpeedMetrics | null;
  error: string | null;
};
export const numeric = (value: unknown): number | null => {
  if (
    (typeof value !== "number" && typeof value !== "string") ||
    (typeof value === "string" && value.trim() === "")
  )
    return null;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
};
export function measureWithWorker(
  run: TransferRun,
  origin: string,
  signal: AbortSignal,
  checkBinding: () => Promise<boolean>,
  progress: (value: SpeedProgress) => void,
  factory: () => Worker = () => new Worker("/librespeed/speedtest_worker.js?v=1.6.0"),
): Promise<WorkerResult> {
  const endpoint = new URL(origin);
  if (
    endpoint.protocol !== "https:" ||
    endpoint.origin !== origin ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      run.id,
    ) ||
    run.transfer_base !== `/network-speedtests/transfer/${run.id}` ||
    !run.transfer_token ||
    run.duration_seconds < 1 ||
    run.duration_seconds > 15
  )
    return Promise.reject(new Error("Endpoint/tiket pengujian tidak valid."));
  return new Promise((resolve) => {
    let worker: Worker | undefined,
      settled = false,
      checking = false;
    let poll: ReturnType<typeof setInterval> | undefined,
      monitor: ReturnType<typeof setInterval> | undefined,
      timeout: ReturnType<typeof setTimeout> | undefined;
    const stop = (result: WorkerResult) => {
      if (settled) return;
      settled = true;
      clearInterval(poll);
      clearInterval(monitor);
      clearTimeout(timeout);
      worker?.terminate();
      signal.removeEventListener("abort", abort);
      document.removeEventListener("visibilitychange", background);
      resolve(result);
    };
    const abort = () =>
      stop({
        status: "aborted",
        metrics: null,
        error: "Pengujian dibatalkan atau halaman ditutup.",
      });
    const background = () => {
      if (document.hidden)
        stop({
          status: "aborted",
          metrics: null,
          error: "Aplikasi masuk background; pengujian dihentikan.",
        });
    };
    if (signal.aborted || document.hidden) {
      abort();
      return;
    }
    signal.addEventListener("abort", abort, { once: true });
    document.addEventListener("visibilitychange", background);
    try {
      worker = factory();
      worker.onmessage = (event) => {
        if (settled) return;
        let raw: Record<string, unknown>;
        try {
          raw = JSON.parse(event.data);
        } catch {
          return;
        }
        const dl = numeric(raw.dlStatus),
          ul = numeric(raw.ulStatus),
          ping = numeric(raw.pingStatus),
          jitter = numeric(raw.jitterStatus);
        const state = Number(raw.testState);
        progress({
          stage:
            (
              {
                0: "Menyiapkan",
                1: "Download",
                2: "Ping/jitter",
                3: "Upload",
                4: "Menyimpan",
                5: "Dihentikan",
              } as Record<number, string>
            )[state] || "Mengukur",
          download: dl,
          upload: ul,
          ping,
          jitter,
        });
        if (state === 4)
          stop(
            dl !== null && ul !== null && ping !== null
              ? {
                  status: "completed",
                  metrics: {
                    download_mbps: dl,
                    upload_mbps: ul,
                    ping_ms: ping,
                    jitter_ms: jitter,
                  },
                  error: null,
                }
              : {
                  status: "failed",
                  metrics: null,
                  error:
                    typeof raw.hotel_error === "string" && raw.hotel_error
                      ? raw.hotel_error
                      : "Pengujian belum lengkap. Periksa koneksi dan ulangi.",
                },
          );
        else if (state === 5)
          stop({
            status: "failed",
            metrics: null,
            error: "Mesin transfer berhenti sebelum pengukuran lengkap.",
          });
      };
      worker.onerror = () =>
        stop({
          status: "failed",
          metrics: null,
          error: "Mesin LibreSpeed gagal dimuat/dijalankan.",
        });
      poll = setInterval(() => {
        try {
          worker?.postMessage("status");
        } catch {
          stop({
            status: "failed",
            metrics: null,
            error: "Mesin transfer tidak merespons.",
          });
        }
      }, 200);
      monitor = setInterval(() => {
        if (checking || settled) return;
        checking = true;
        void checkBinding()
          .then(
            (valid) => {
              if (!valid)
                stop({
                  status: "failed",
                  metrics: null,
                  error:
                    "Jaringan Wi-Fi berubah atau binding tidak lagi valid.",
                });
            },
            () =>
              stop({
                status: "failed",
                metrics: null,
                error: "Validasi binding Wi-Fi gagal.",
              }),
          )
          .finally(() => {
            checking = false;
          });
      }, 1000);
      timeout = setTimeout(
        () =>
          stop({
            status: "failed",
            metrics: null,
            error: "Waktu pengujian habis.",
          }),
        75000,
      );
      worker.postMessage(
        "start " +
          JSON.stringify({
            test_order: "P_D_U",
            url_dl: origin + run.transfer_base + "/download",
            url_ul: origin + run.transfer_base + "/upload",
            url_ping: origin + run.transfer_base + "/ping",
            time_dl_max: run.duration_seconds,
            time_ul_max: run.duration_seconds,
            time_auto: false,
            count_ping: 5,
            xhr_dlMultistream: 2,
            xhr_ulMultistream: 1,
            xhr_ul_blob_megabytes: 1,
            hotel_dl_budget_bytes: Math.min(
              run.download_limit_bytes || 64 * 1024 * 1024,
              64 * 1024 * 1024,
            ),
            hotel_ul_budget_bytes: Math.min(
              run.upload_limit_bytes || 32 * 1024 * 1024,
              32 * 1024 * 1024,
            ),
            hotel_dl_chunk_bytes: 4 * 1024 * 1024,
            xhr_ignoreErrors: 0,
            telemetry_level: "disabled",
            getIp_ispInfo: false,
            overheadCompensationFactor: 1,
            ping_allowPerformanceApi: false,
            hotel_transfer_token: run.transfer_token,
            hotel_run_id: run.id,
            hotel_endpoint_origin: origin,
          }),
      );
    } catch {
      stop({
        status: "failed",
        metrics: null,
        error: "Mesin pengukuran tidak dapat dimulai.",
      });
    }
  });
}
