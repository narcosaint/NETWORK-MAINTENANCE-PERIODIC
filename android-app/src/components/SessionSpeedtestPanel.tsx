import { useState, useEffect, useRef } from "react";
import { libreSpeedService } from "../services/librespeed";
import type { SpeedProgress } from "../services/speedWorker";
import type { Point, PointDraft } from "../types";
import { Card, Message } from "./ui";
import { when } from "../domain";
export function SessionSpeedtestPanel({
  point,
  busy,
  editable,
  startTest,
}: {
  point: Point;
  draft?: PointDraft;
  change: (value: PointDraft) => void;
  reportFailure?: (rebase: boolean) => Promise<void>;
  busy: boolean;
  editable: boolean;
  startTest?: (
    signal: AbortSignal,
    progress: (value: SpeedProgress) => void,
  ) => Promise<void>;
}) {
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<SpeedProgress | null>(null);
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      controller.current?.abort();
    };
  }, []);
  const supported = !!startTest && libreSpeedService.capability().available;
  const measure = async () => {
    if (!startTest || busy || controller.current) return;
    const abort = new AbortController();
    controller.current = abort;
    setError("");
    setProgress({
      stage: "Mempersiapkan Wi-Fi",
      download: null,
      upload: null,
      ping: null,
      jitter: null,
    });
    try {
      await startTest(abort.signal, (value) => {
        if (mounted.current) setProgress(value);
      });
    } catch (error) {
      if (mounted.current) setError((error as Error).message);
    } finally {
      controller.current = null;
      if (mounted.current)
        setProgress((value) =>
          value
            ? { ...value, stage: "Pengujian berakhir · lihat hasil tersimpan" }
            : null,
        );
    }
  };
  return (
    <div className="stack">
      <Card title="Speedtest area">
        <button
          className="primary wide"
          disabled={!supported || !editable || busy}
          onClick={() => void measure()}
        >
          {supported ? "Mulai pengujian" : "Mulai Speedtest · Belum tersedia"}
        </button>
        {progress && (
          <>
            <p role="status">{progress.stage}</p>
            <p>
              ↓ {progress.download ?? "—"} Mbps · ↑ {progress.upload ?? "—"}{" "}
              Mbps · Ping {progress.ping ?? "—"} ms · Jitter{" "}
              {progress.jitter ?? "—"} ms
            </p>
            {busy && (
              <button
                className="secondary wide"
                onClick={() => controller.current?.abort()}
              >
                Batalkan pengujian
              </button>
            )}
          </>
        )}
        {error && <Message error>{error}</Message>}
      </Card>
      <Card title="Riwayat pengujian area" collapsible>
        {(point.session?.speedtests || []).map((attempt) => (
          <article key={attempt.id} className="history-item">
            <strong>
              {attempt.status === "failed"
                ? "Gagal Diuji"
                : attempt.status === "completed"
                  ? "Hasil pengujian tersimpan"
                  : attempt.status === "aborted"
                    ? "Dibatalkan"
                    : "Sedang diuji"}
            </strong>
            <p>{when(attempt.created_at)}</p>
            {attempt.run && (
              <p>
                Server uji:{" "}
                {String(attempt.run.context?.endpoint_origin || "—")}
              </p>
            )}
            {attempt.run?.metrics && (
              <p>
                ↓ {attempt.run.metrics.download_mbps ?? "—"} Mbps · ↑{" "}
                {attempt.run.metrics.upload_mbps ?? "—"} Mbps
                <br />
                Ping {attempt.run.metrics.ping_ms ?? "—"} ms · Jitter{" "}
                {attempt.run.metrics.jitter_ms ?? "—"} ms
              </p>
            )}
            {attempt.error && <p>{attempt.error}</p>}
            {attempt.finding && <p>Temuan gagal uji: {attempt.finding}</p>}
          </article>
        ))}
        {!point.session?.speedtests?.length && (
          <p>Belum ada pengujian pada area ini.</p>
        )}
      </Card>
    </div>
  );
}
