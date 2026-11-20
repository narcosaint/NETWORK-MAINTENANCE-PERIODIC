import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient, ApiError } from "../src/services/api";
import { store } from "../src/services/storage";
import { reportSamplingFailure } from "../src/services/samplingSpeedtests";
import {
  submitObservation,
  observationKey,
} from "../src/services/observationOutbox";
import type { Point, PointDraft, Visit } from "../src/types";

const records = vi.hoisted(() => new Map<string, unknown>());
vi.mock("../src/services/storage", () => ({
  store: {
    get: vi.fn(async (key: string) => records.get(key)),
    put: vi.fn(async (key: string, value: unknown) => {
      records.set(key, structuredClone(value));
    }),
    remove: vi.fn(async (key: string) => {
      records.delete(key);
    }),
  },
}));
const visit = { id: "visit", version: 3 } as Visit;
const point: Point = {
  id: "session-a",
  name: "A",
  session: {
    id: "session-a",
    sampling_point_id: "master-a",
    name: "A",
    location: null,
    device: null,
    status: "untested",
    version: 1,
  },
};
const draft: PointDraft = {
  status: "good",
  notes: "Catatan nyata",
  updatedAt: "2026-11-16T00:00:00Z",
};
it("only refreshes the session version when the saved note baseline is unchanged", async () => {
  const baseline = {
    condition: "good" as const,
    notes: "Original",
    findings: "",
    action: "",
    recommendation: "",
  };
  const refreshed = {
    ...point,
    session: {
      ...point.session!,
      version: 4,
      observation: { notes: baseline },
    },
  } as unknown as Point;
  const { api, save } = client();
  await submitObservation(
    api,
    "scope:",
    visit,
    refreshed,
    { ...draft, baseNotes: baseline, baseSessionVersion: 1 },
    true,
  );
  expect(save.mock.calls[0][2].expected_session_version).toBe(4);
  const changed = {
    ...refreshed,
    session: {
      ...refreshed.session!,
      observation: { notes: { ...baseline, notes: "Another technician edit" } },
    },
  } as unknown as Point;
  await submitObservation(
    api,
    "scope:",
    visit,
    changed,
    { ...draft, baseNotes: baseline, baseSessionVersion: 1 },
    true,
  );
  expect(save.mock.calls[1][2].expected_session_version).toBe(1);
});
beforeEach(() => {
  records.clear();
  vi.clearAllMocks();
});
afterEach(() => vi.restoreAllMocks());
function client() {
  const save = vi.fn().mockImplementation(async (_visit, _point, data) => ({
    visit: { ...visit, version: 4 },
    observation: { id: data.id, notes: data.notes },
    replayed: false,
  }));
  return { save, api: { saveObservation: save } as unknown as ApiClient };
}
describe("durable per-session notes outbox", () => {
  it("queues reasoned failures and retries the same UUID without generating metrics", async () => {
    const send = vi.fn(async (_visit, _point, payload) => ({
      attempt: { id: payload.id, error: payload.reason },
      visit,
    }));
    const api = { reportSpeedtestFailure: send } as unknown as ApiClient;
    const failure = { ...draft, failedTestReason: "Wi-Fi unavailable on site" };
    await expect(
      reportSamplingFailure(api, "scope:", visit, point, failure, false),
    ).rejects.toThrow("antrean");
    expect(send).not.toHaveBeenCalled();
    const pending = records.get(
      "scope:speedtest-failure-outbox:" + point.id,
    ) as { payload: { id: string } };
    await reportSamplingFailure(
      api,
      "scope:",
      { ...visit, version: 99 },
      point,
      { ...failure, failedTestReason: "New draft" },
      true,
    );
    expect(send.mock.calls[0][2].id).toBe(pending.payload.id);
    expect(send.mock.calls[0][2].reason).toBe("Wi-Fi unavailable on site");
    expect(send.mock.calls[0][2]).not.toHaveProperty("metrics");
    expect(records.size).toBe(0);
  });
  it("queues offline and retries the exact captured payload even after edits and reload", async () => {
    const { api, save } = client();
    await expect(
      submitObservation(api, "account-a:", visit, point, draft, false),
    ).rejects.toThrow("antrean");
    expect(save).not.toHaveBeenCalled();
    const pending = records.get(observationKey("account-a:", point.id));
    await submitObservation(
      api,
      "account-a:",
      { ...visit, version: 99 },
      point,
      { ...draft, notes: "New draft" },
      true,
    );
    expect(save.mock.calls[0][2]).toEqual(
      (pending as { payload: unknown }).payload,
    );
    expect(save.mock.calls[0][2].notes.notes).toBe("Catatan nyata");
    expect(records.size).toBe(0);
  });
  it("keeps UUID after a lost acknowledgment and does not offer unverified rebasing", async () => {
    const { api, save } = client();
    save.mockRejectedValueOnce(new ApiError("Lost response"));
    await expect(
      submitObservation(api, "scope:", visit, point, draft, true),
    ).rejects.toThrow("Lost response");
    const first = save.mock.calls[0][2];
    await expect(
      submitObservation(api, "scope:", visit, point, draft, true, true),
    ).rejects.toThrow("request sebelumnya");
    await submitObservation(api, "scope:", visit, point, draft, true);
    expect(save.mock.calls[1][2]).toEqual(first);
  });
  it("preserves draft base versions, then permits explicit rebase after server conflict and review", async () => {
    const { api, save } = client();
    save.mockRejectedValueOnce(new ApiError("Conflict", 409));
    await expect(
      submitObservation(
        api,
        "scope:",
        visit,
        point,
        { ...draft, baseVisitVersion: 1, baseSessionVersion: 1 },
        true,
      ),
    ).rejects.toThrow("Conflict");
    expect(save.mock.calls[0][2].expected_visit_version).toBe(1);
    const previousId = save.mock.calls[0][2].id;
    await submitObservation(api, "scope:", visit, point, draft, true, true);
    expect(save.mock.calls[1][2].expected_visit_version).toBe(3);
    expect(save.mock.calls[1][2].id).not.toBe(previousId);
  });
  it("does not send if durable local persistence fails and isolates account queues", async () => {
    const { api, save } = client();
    vi.mocked(store.put).mockRejectedValueOnce(new Error("quota"));
    await expect(
      submitObservation(api, "scope:", visit, point, draft, true),
    ).rejects.toThrow("quota");
    expect(save).not.toHaveBeenCalled();
    await expect(
      submitObservation(api, "account-a:", visit, point, draft, false),
    ).rejects.toThrow("antrean");
    await submitObservation(
      api,
      "account-b:",
      visit,
      point,
      { ...draft, notes: "Other account" },
      true,
    );
    expect(records.has(observationKey("account-a:", point.id))).toBe(true);
    expect(save.mock.calls[0][2].notes.notes).toBe("Other account");
  });
});

it("replays an old queue then saves the latest edit without clearing independently merged notes", async () => {
  const { api, save } = client();
  const older = { ...draft, notes: "Queued edit" };
  await expect(
    submitObservation(api, "scope:", visit, point, older, false),
  ).rejects.toThrow("antrean");
  save.mockImplementation(async (_visit, _point, data) => ({
    visit: { ...visit, version: 5 },
    observation: {
      id: data.id,
      session_version: 2,
      notes: {
        ...data.notes,
        recommendation: "Independent server recommendation",
      },
    },
    replayed: false,
  }));
  const { submitLatestObservation } =
    await import("../src/services/observationOutbox");
  const result = await submitLatestObservation(
    api,
    "scope:",
    visit,
    point,
    { ...draft, notes: "Latest edit" },
    true,
  );
  expect(save).toHaveBeenCalledTimes(2);
  expect(save.mock.calls[0][2].notes.notes).toBe("Queued edit");
  expect(save.mock.calls[1][2].notes.notes).toBe("Latest edit");
  expect(save.mock.calls[1][2].notes.recommendation).toBe(
    "Independent server recommendation",
  );
  expect(save.mock.calls[1][2].id).not.toBe(save.mock.calls[0][2].id);
  expect(result.submittedNotes.notes).toBe("Latest edit");
});
