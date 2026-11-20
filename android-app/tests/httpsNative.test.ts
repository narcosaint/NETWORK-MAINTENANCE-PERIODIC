import { afterEach, expect, it, vi } from "vitest";
import { Capacitor, CapacitorHttp } from "@capacitor/core";
import {
  ApiClient,
  DEFAULT_API_ORIGIN,
  normalizeOrigin,
} from "../src/services/api";
vi.mock("@capacitor/core", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@capacitor/core")>();
  return { ...actual, CapacitorHttp: { request: vi.fn() } };
});
afterEach(() => vi.restoreAllMocks());
it("uses native HTTPS for the configured login origin and keeps credentials out of URL", async () => {
  vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(true);
  const request = vi
    .mocked(CapacitorHttp.request)
    .mockResolvedValueOnce({
      status: 200,
      data: { access_token: "fixture-token" },
      headers: {},
      url: DEFAULT_API_ORIGIN + "/auth/login",
    })
    .mockResolvedValueOnce({
      status: 200,
      data: { id: "tech", role: "technician" },
      headers: {},
      url: DEFAULT_API_ORIGIN + "/auth/me",
    });
  const client = new ApiClient(normalizeOrigin(DEFAULT_API_ORIGIN, true));
  expect((await client.login("fixture-tech", "fixture-password")).role).toBe(
    "technician",
  );
  expect(request.mock.calls[0][0]).toMatchObject({
    url: "https://maintenance.inisaja.id/auth/login",
    method: "POST",
    data: { username: "fixture-tech", password: "fixture-password" },
    disableRedirects: true,
  });
  expect(request.mock.calls[1][0]).toMatchObject({
    url: "https://maintenance.inisaja.id/auth/me",
    headers: { Authorization: "Bearer fixture-token" },
  });
});
