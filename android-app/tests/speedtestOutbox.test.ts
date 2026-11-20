import { beforeEach, expect, it, vi } from "vitest";
import { runSamplingSpeedtest } from "../src/services/librespeed";
import { ApiClient, ApiError } from "../src/services/api";
import type { WifiLease } from "../src/services/wifiLease";
import type { Point, Visit } from "../src/types";
const records = vi.hoisted(() => new Map<string, unknown>());
vi.mock("../src/services/storage", () => ({
  store: {
    get: vi.fn(async (key: string) => structuredClone(records.get(key))),
    put: vi.fn(async (key: string, value: unknown) => {
      records.set(key, structuredClone(value));
    }),
    remove: vi.fn(async (key: string) => {
      records.delete(key);
    }),
  },
}));
const visit = { id: "visit-a", version: 3 } as Visit;
const point = {
  id: "session-a",
  session: { id: "session-a", version: 1 },
} as Point;
function setup() {
  const connection = {
    source: "android_native",
    transport: "wifi",
    observedAt: "2026-11-18T00:00:00Z",
    ssid: "QA fixture",
    bssid: "aa:bb:cc:dd:ee:ff",
    frequencyMhz: 5180,
    channel: 36,
    band: "5 GHz",
    rssiDbm: -65,
    linkSpeedMbps: 100,
    ipAddress: null,
    gateway: null,
  } as const;
  const lease: WifiLease = {
    connection,
    binding: {
      id: crypto.randomUUID(),
      network_handle: "123",
      source: "android_native",
    },
    check: vi.fn(async () => true),
    snapshot: vi.fn(async () => connection),
    release: vi.fn(async () => {}),
  };
  const attempt = { id: "attempt", status: "running" };
  const start = vi.fn(async () => ({
    attempt,
    visit,
    transfer: { transfer_token: "never-persist-this" },
  }));
  const finish = vi.fn(async () => ({
    attempt: { ...attempt, status: "completed" },
    visit,
  }));
  const api = {
    origin: "https://measure.test",
    startSessionSpeedtest: start,
    finishSessionSpeedtest: finish,
  } as unknown as ApiClient;
  const deps = {
    acquire: vi.fn(async () => lease),
    measure: vi.fn(async () => ({
      status: "completed" as const,
      metrics: {
        download_mbps: 12,
        upload_mbps: 3,
        ping_ms: 4,
        jitter_ms: null,
      },
      error: null,
    })),
  };
  const run = () =>
    runSamplingSpeedtest(
      api,
      "scope:",
      visit,
      point,
      new AbortController().signal,
      vi.fn(),
      vi.fn(async () => {}),
      deps,
    );
  return { lease, start, finish, deps, run };
}
beforeEach(() => {
  records.clear();
  vi.clearAllMocks();
});
it("measures under a lease, releases before finish and keeps tickets out of local storage", async () => {
  const { run, lease, finish } = setup();
  finish.mockImplementation(async () => {
    expect(lease.release).toHaveBeenCalledOnce();
    expect(JSON.stringify([...records.values()])).not.toContain(
      "never-persist-this",
    );
    return { attempt: { id: "attempt", status: "completed" }, visit };
  });
  await run();
  expect(finish.mock.calls[0]).toHaveLength(4);
  expect(records.size).toBe(0);
});
it("drops metrics when Wi-Fi changes at the end", async () => {
  const { run, lease, finish } = setup();
  vi.mocked(lease.check)
    .mockResolvedValueOnce(true)
    .mockResolvedValueOnce(false);
  await run();
  expect((finish.mock.calls[0] as unknown[])[3]).toMatchObject({
    result: { status: "failed", metrics: null },
  });
  expect(lease.release).toHaveBeenCalledOnce();
});
it("recovers lost start using the same UUID and aborts without reacquiring Wi-Fi", async () => {
  const { run, start, deps, finish } = setup();
  start.mockRejectedValueOnce(new ApiError("response lost"));
  await expect(run()).rejects.toThrow("response lost");
  const pending = structuredClone([...records.values()][0]);
  await run();
  expect(start.mock.calls[1]).toEqual(start.mock.calls[0]);
  expect(pending).toHaveProperty("start.id");
  expect(deps.acquire).toHaveBeenCalledOnce();
  expect(deps.measure).not.toHaveBeenCalled();
  expect((finish.mock.calls[0] as unknown[])[3]).toMatchObject({
    result: { status: "aborted", metrics: null },
  });
});
it("retries persisted finish after lost acknowledgment without a second transfer", async () => {
  const { run, start, finish, deps } = setup();
  finish.mockRejectedValueOnce(new ApiError("response lost"));
  await expect(run()).rejects.toThrow("response lost");
  expect(JSON.stringify([...records.values()])).not.toContain(
    "never-persist-this",
  );
  await run();
  expect(finish.mock.calls[1]).toEqual(finish.mock.calls[0]);
  expect(start).toHaveBeenCalledOnce();
  expect(deps.measure).toHaveBeenCalledOnce();
  expect(records.size).toBe(0);
});
it("clears a rejected start so stale versions can be corrected", async () => {
  const { run, start, lease } = setup();
  start.mockRejectedValueOnce(new ApiError("version conflict", 409));
  await expect(run()).rejects.toThrow("version conflict");
  expect(records.size).toBe(0);
  expect(lease.release).toHaveBeenCalledOnce();
});
