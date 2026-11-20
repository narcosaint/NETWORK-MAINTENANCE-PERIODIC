import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { measureWithWorker, numeric } from "../src/services/speedWorker";
import type { TransferRun } from "../src/types";
const run = {
  id: "12345678-1234-1234-1234-123456789abc",
  transfer_base:
    "/network-speedtests/transfer/12345678-1234-1234-1234-123456789abc",
  transfer_token: "ephemeral-only",
  duration_seconds: 8,
} as TransferRun;
let worker: {
  postMessage: ReturnType<typeof vi.fn>;
  terminate: ReturnType<typeof vi.fn>;
  onmessage?: (event: { data: string }) => void;
  onerror?: () => void;
};
let page: EventTarget & { hidden: boolean };
beforeEach(() => {
  vi.useFakeTimers();
  page = Object.assign(new EventTarget(), { hidden: false });
  vi.stubGlobal("document", page);
  worker = { postMessage: vi.fn(), terminate: vi.fn() };
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
function measure(
  check = vi.fn(async () => true),
  controller = new AbortController(),
) {
  return measureWithWorker(
    run,
    "https://measure.test",
    controller.signal,
    check,
    vi.fn(),
    () => worker as unknown as Worker,
  );
}
it("keeps actual zero values, rejects missing/nonfinite values and preserves unavailable jitter", async () => {
  for (const value of [null, undefined, "", " ", false, NaN, Infinity, -1])
    expect(numeric(value)).toBeNull();
  const result = measure();
  const settings = JSON.parse(worker.postMessage.mock.calls[0][0].slice(6));
  expect(settings.hotel_transfer_token).toBe(run.transfer_token);
  expect(settings.hotel_endpoint_origin).toBe("https://measure.test");
  expect(settings.telemetry_level).toBe("disabled");
  expect(settings.hotel_ul_budget_bytes).toBeLessThanOrEqual(32*1024*1024);
  expect(settings.hotel_dl_budget_bytes).toBeLessThanOrEqual(64*1024*1024);
  worker.onmessage!({
    data: JSON.stringify({
      testState: 4,
      dlStatus: "0",
      ulStatus: "2.3",
      pingStatus: "4",
      jitterStatus: "",
    }),
  });
  expect(await result).toMatchObject({
    status: "completed",
    metrics: { download_mbps: 0, jitter_ms: null },
  });
  expect(worker.terminate).toHaveBeenCalledOnce();
  expect(vi.getTimerCount()).toBe(0);
});
it("does not fabricate missing throughput", async () => {
  const result = measure();
  worker.onmessage!({
    data: JSON.stringify({
      testState: 4,
      dlStatus: "",
      ulStatus: "2",
      pingStatus: "4",
    }),
  });
  expect(await result).toMatchObject({ status: "failed", metrics: null });
});
it("terminates before returning when binding is lost", async () => {
  const result = measure(vi.fn(async () => false));
  await vi.advanceTimersByTimeAsync(1000);
  expect(await result).toMatchObject({ status: "failed", metrics: null });
  expect(worker.terminate).toHaveBeenCalledOnce();
});
it("aborts on cancellation and backgrounding", async () => {
  const controller = new AbortController();
  const result = measure(undefined, controller);
  controller.abort();
  expect(await result).toMatchObject({ status: "aborted", metrics: null });
  const second = measure();
  page.hidden = true;
  page.dispatchEvent(new Event("visibilitychange"));
  expect(await second).toMatchObject({ status: "aborted", metrics: null });
});
it("rejects unsafe endpoints before creating a worker", async () => {
  await expect(
    measureWithWorker(
      run,
      "http://measure.test",
      new AbortController().signal,
      vi.fn(),
      vi.fn(),
      () => worker as unknown as Worker,
    ),
  ).rejects.toThrow("Endpoint");
  expect(worker.postMessage).not.toHaveBeenCalled();
});
