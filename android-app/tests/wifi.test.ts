import { describe, expect, it, vi } from "vitest";
import {
  createWifiService,
  frequencyChannel,
  radioPayload,
  type WifiConnection,
  type WifiScanBatch,
} from "../src/services/wifi";
import { observationMatchesDraft } from "../src/services/observationOutbox";
import type { SamplingObservation } from "../src/types";
const connection: WifiConnection = {
  source: "android_native",
  transport: "wifi",
  observedAt: "2026-11-16T00:00:00Z",
  ssid: "Actual device snapshot",
  bssid: "aa:bb:cc:dd:ee:ff",
  frequencyMhz: 5180,
  channel: 36,
  band: "5 GHz",
  rssiDbm: -65,
  linkSpeedMbps: 0,
  ipAddress: "192.0.2.2",
  gateway: "192.0.2.1",
};
const scan: WifiScanBatch = {
  source: "android_native",
  observedAt: connection.observedAt,
  band: "5 GHz",
  cached: false,
  reason: null,
  networks: [
    {
      ssid: "",
      bssid: connection.bssid!,
      frequencyMhz: 5180,
      channel: 36,
      rssiDbm: -65,
      observedAt: connection.observedAt,
      cached: true,
    },
  ],
};
describe("native Wi-Fi boundary", () => {
  it("never invokes a radio bridge outside supported Android", async () => {
    const bridge = { connection: vi.fn(), scan: vi.fn() },
      service = createWifiService(bridge, () => false);
    expect((await service.connection()).available).toBe(false);
    expect((await service.scan("5 GHz")).available).toBe(false);
    expect(bridge.connection).not.toHaveBeenCalled();
    expect(bridge.scan).not.toHaveBeenCalled();
  });
  it("keeps real zeros and hidden SSIDs, derives channels, and retains cache provenance", async () => {
    const service = createWifiService(
      {
        connection: async () => ({ available: true, data: connection }),
        scan: async () => ({ available: true, data: scan }),
      },
      () => true,
    );
    expect(await service.connection()).toMatchObject({
      available: true,
      data: { linkSpeedMbps: 0, channel: 36 },
    });
    expect(await service.scan("5 GHz")).toMatchObject({
      available: true,
      data: { networks: [{ ssid: "", cached: true }] },
    });
    const payload = radioPayload({ connection, scan });
    expect(payload.wifi_scan?.cached).toBe(true);
    expect(payload.wifi_scan?.networks[0].observed_at).toBe(
      connection.observedAt,
    );
    expect(frequencyChannel(2484)).toBe(14);
    expect(frequencyChannel(2412)).toBe(1);
    expect(frequencyChannel(5975)).toBeNull();
  });
  it("rejects placeholder identifiers, cellular results and invalid RSSI without fabricating data", async () => {
    for (const patch of [
      { bssid: "02:00:00:00:00:00" },
      { transport: "cellular" },
      { rssiDbm: -200 },
      { frequencyMhz: 0 },
    ]) {
      const service = createWifiService(
        {
          connection: async () => ({
            available: true,
            data: { ...connection, ...patch } as WifiConnection,
          }),
          scan: vi.fn(),
        },
        () => true,
      );
      expect((await service.connection()).available).toBe(false);
    }
    const service = createWifiService(
      {
        connection: vi.fn(),
        scan: async () => ({ available: false, reason: "Izin ditolak" }),
      },
      () => true,
    );
    expect(await service.scan("5 GHz")).toEqual({
      available: false,
      reason: "Izin ditolak",
    });
  });
  it("does not clear a newly captured radio draft when an older pending note is acknowledged", () => {
    const notes = {
      condition: "good" as const,
      notes: "",
      findings: "",
      action: "",
      recommendation: "",
    };
    const observation = {
      id: "old",
      notes,
      wifi_connection: null,
      wifi_scan: null,
    } as unknown as SamplingObservation;
    expect(
      observationMatchesDraft(
        {
          status: "good",
          updatedAt: connection.observedAt,
          radio: { connection },
        },
        notes,
        observation,
      ),
    ).toBe(false);
    const payload = radioPayload({ connection });
    expect(
      observationMatchesDraft(
        {
          status: "good",
          updatedAt: connection.observedAt,
          radio: { connection },
        },
        notes,
        { ...observation, ...payload },
      ),
    ).toBe(true);
  });
});
