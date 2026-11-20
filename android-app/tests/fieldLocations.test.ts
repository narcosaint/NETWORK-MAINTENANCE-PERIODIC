import { beforeEach, expect, it, vi } from "vitest";
import { ApiClient, ApiError } from "../src/services/api";
import {
  fieldOutboxKey,
  submitFieldLocations,
} from "../src/services/fieldLocations";
import { store } from "../src/services/storage";
import type {
  FieldLocationInput,
  FieldLocationRequest,
  Visit,
} from "../src/types";
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
const input: FieldLocationInput = {
  floor_name: "Lokasi QA",
  reason: "Penambahan aktual QA",
  points: [{ name: "Koridor barat QA", location: null, device_id: null }],
};
beforeEach(() => {
  records.clear();
  vi.clearAllMocks();
});
it("persists before sending and retries a lost acknowledgment with exactly the same UUID/payload", async () => {
  const send = vi.fn(async (_id: string, data: FieldLocationRequest) => ({
    visit,
    replayed: !!data.id,
  }));
  const api = { addFieldLocations: send } as unknown as ApiClient;
  send.mockRejectedValueOnce(new ApiError("Lost response"));
  await expect(
    submitFieldLocations(api, "scope:", visit, input),
  ).rejects.toThrow("Lost response");
  const pending = records.get(fieldOutboxKey("scope:"));
  await submitFieldLocations(
    api,
    "scope:",
    { ...visit, version: 99 },
    { ...input, floor_name: "Edited draft" },
  );
  expect(send.mock.calls[0][1]).toEqual(pending);
  expect(send.mock.calls[1][1]).toEqual(pending);
  expect(records.size).toBe(0);
});
it("retains the editable draft but clears a definitively rejected request for review", async () => {
  records.set("scope:field-location-draft", input);
  const send = vi.fn().mockRejectedValueOnce(new ApiError("Conflict", 409));
  await expect(
    submitFieldLocations(
      { addFieldLocations: send } as unknown as ApiClient,
      "scope:",
      visit,
      input,
    ),
  ).rejects.toThrow("Conflict");
  expect(records.has(fieldOutboxKey("scope:"))).toBe(false);
  expect(records.get("scope:field-location-draft")).toEqual(input);
});
it("does not send if local persistence fails, and keeps visit/account queues separate", async () => {
  const send = vi.fn();
  vi.mocked(store.put).mockRejectedValueOnce(new Error("quota"));
  await expect(
    submitFieldLocations(
      { addFieldLocations: send } as unknown as ApiClient,
      "scope:",
      visit,
      input,
    ),
  ).rejects.toThrow("quota");
  expect(send).not.toHaveBeenCalled();
  expect(fieldOutboxKey("account-a:visit-a:")).not.toBe(
    fieldOutboxKey("account-b:visit-a:"),
  );
});
