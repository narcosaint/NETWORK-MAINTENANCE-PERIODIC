import { Capacitor, registerPlugin } from "@capacitor/core";
import type { SamplingObservation } from "../types";

export type Availability<T> =
  { available: true; data: T } | { available: false; reason: string };
export type WifiConnection = {
  source: "android_native";
  transport: "wifi";
  observedAt: string;
  ssid: string | null;
  bssid: string | null;
  frequencyMhz: number | null;
  channel: number | null;
  band: "2.4 GHz" | "5 GHz" | null;
  rssiDbm: number | null;
  linkSpeedMbps: number | null;
  ipAddress: string | null;
  gateway: string | null;
};
export type WifiScan = {
  ssid: string;
  bssid: string;
  frequencyMhz: number;
  channel: number | null;
  rssiDbm: number;
  observedAt: string;
  cached: boolean;
};
export type WifiScanBatch = {
  source: "android_native";
  band: "2.4 GHz" | "5 GHz";
  observedAt: string;
  cached: boolean;
  reason: string | null;
  networks: WifiScan[];
};
export type RadioDraft = { connection?: WifiConnection; scan?: WifiScanBatch };
export function radioFromObservation(
  observation?: Pick<
    SamplingObservation,
    "wifi_connection" | "wifi_scan"
  > | null,
): RadioDraft {
  const connection = observation?.wifi_connection,
    scan = observation?.wifi_scan;
  return {
    ...(connection
      ? {
          connection: {
            source: connection.source,
            transport: connection.transport,
            observedAt: connection.observed_at,
            ssid: connection.ssid,
            bssid: connection.bssid,
            frequencyMhz: connection.frequency_mhz,
            channel: frequencyChannel(connection.frequency_mhz),
            band: frequencyBand(connection.frequency_mhz),
            rssiDbm: connection.rssi_dbm,
            linkSpeedMbps: connection.link_speed_mbps,
            ipAddress: connection.ip_address,
            gateway: connection.gateway,
          },
        }
      : {}),
    ...(scan
      ? {
          scan: {
            source: scan.source,
            band: scan.requested_band,
            observedAt: scan.observed_at,
            cached: scan.cached,
            reason: scan.reason,
            networks: scan.networks.map((network) => ({
              ssid: network.ssid,
              bssid: network.bssid,
              frequencyMhz: network.frequency_mhz,
              channel: frequencyChannel(network.frequency_mhz),
              rssiDbm: network.rssi_dbm,
              observedAt: network.observed_at,
              cached: network.cached,
            })),
          },
        }
      : {}),
  };
}
interface WifiBridge {
  connection(): Promise<Availability<WifiConnection>>;
  scan(options: {
    band: "2.4 GHz" | "5 GHz";
  }): Promise<Availability<WifiScanBatch>>;
}
const bridge = registerPlugin<WifiBridge>("HotelWifi");
const unavailable = {
  available: false as const,
  reason:
    "Belum tersedia · Wi-Fi native hanya tersedia di aplikasi Android dengan plugin HotelWifi.",
};
const validTime = (value: string) =>
  typeof value === "string" && Number.isFinite(Date.parse(value));
const validMac = (value: string) =>
  /^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$/i.test(value) &&
  !["02:00:00:00:00:00", "00:00:00:00:00:00"].includes(value);
const numeric = (value: number | null, min: number, max: number) =>
  value === null ||
  (typeof value === "number" &&
    Number.isFinite(value) &&
    value >= min &&
    value <= max);
export function frequencyBand(
  frequency: number | null,
): WifiConnection["band"] {
  return frequency !== null && frequency >= 2400 && frequency <= 2500
    ? "2.4 GHz"
    : frequency !== null && frequency >= 5000 && frequency < 5925
      ? "5 GHz"
      : null;
}
export function frequencyChannel(frequency: number | null): number | null {
  if (frequency === 2484) return 14;
  if (
    frequency !== null &&
    frequency >= 2412 &&
    frequency <= 2472 &&
    (frequency - 2407) % 5 === 0
  )
    return (frequency - 2407) / 5;
  if (
    frequency !== null &&
    frequency >= 5000 &&
    frequency <= 5895 &&
    frequency % 5 === 0
  )
    return (frequency - 5000) / 5;
  return null;
}
export function createWifiService(
  native: WifiBridge,
  supported: () => boolean,
) {
  return {
    async connection(): Promise<Availability<WifiConnection>> {
      if (!supported()) return unavailable;
      try {
        const result = await native.connection();
        if (!result.available) return result;
        const data = result.data;
        if (
          !data ||
          data.source !== "android_native" ||
          data.transport !== "wifi" ||
          !validTime(data.observedAt) ||
          !numeric(data.frequencyMhz, 2300, 7200) ||
          (data.frequencyMhz !== null &&
            !Number.isInteger(data.frequencyMhz)) ||
          !numeric(data.rssiDbm, -126, 0) ||
          (data.rssiDbm !== null && !Number.isInteger(data.rssiDbm)) ||
          !numeric(data.linkSpeedMbps, 0, 100000) ||
          (data.bssid !== null && !validMac(data.bssid)) ||
          (data.ssid !== null &&
            (typeof data.ssid !== "string" || data.ssid.length > 32))
        )
          throw new Error("invalid");
        return {
          available: true,
          data: {
            ...data,
            channel: frequencyChannel(data.frequencyMhz),
            band: frequencyBand(data.frequencyMhz),
          },
        };
      } catch {
        return {
          available: false,
          reason:
            "Data koneksi native tidak tersedia atau tidak valid. Baca ulang Wi-Fi.",
        };
      }
    },
    async scan(
      band: "2.4 GHz" | "5 GHz",
    ): Promise<Availability<WifiScanBatch>> {
      if (!supported()) return unavailable;
      try {
        const result = await native.scan({ band });
        if (!result.available) return result;
        const data = result.data;
        if (
          !data ||
          data.source !== "android_native" ||
          data.band !== band ||
          !validTime(data.observedAt) ||
          typeof data.cached !== "boolean" ||
          !Array.isArray(data.networks) ||
          data.networks.length > 256 ||
          data.networks.some(
            (network) =>
              !validMac(network.bssid) ||
              !validTime(network.observedAt) ||
              typeof network.ssid !== "string" ||
              network.ssid.length > 32 ||
              typeof network.cached !== "boolean" ||
              !Number.isInteger(network.frequencyMhz) ||
              frequencyBand(network.frequencyMhz) !== band ||
              !Number.isInteger(network.rssiDbm) ||
              !numeric(network.rssiDbm, -127, 0),
          )
        )
          throw new Error("invalid");
        return {
          available: true,
          data: {
            ...data,
            networks: data.networks.map((network) => ({
              ...network,
              channel: frequencyChannel(network.frequencyMhz),
            })),
          },
        };
      } catch {
        return {
          available: false,
          reason:
            "Scan native tidak tersedia atau tidak valid. Tidak ada pengukuran dibuat.",
        };
      }
    },
  };
}
export const wifiService = createWifiService(
  bridge,
  () =>
    Capacitor.getPlatform() === "android" &&
    Capacitor.isPluginAvailable("HotelWifi"),
);

export function radioPayload(radio?: RadioDraft) {
  const connection = radio?.connection,
    scan = radio?.scan;
  return {
    wifi_connection: connection
      ? {
          source: connection.source,
          observed_at: connection.observedAt,
          transport: connection.transport,
          ssid: connection.ssid,
          bssid: connection.bssid,
          frequency_mhz: connection.frequencyMhz,
          rssi_dbm: connection.rssiDbm,
          link_speed_mbps: connection.linkSpeedMbps,
          ip_address: connection.ipAddress,
          gateway: connection.gateway,
        }
      : null,
    wifi_scan: scan
      ? {
          source: scan.source,
          observed_at: scan.observedAt,
          cached: scan.cached || scan.networks.some((n) => n.cached),
          requested_band: scan.band,
          reason: scan.reason,
          networks: scan.networks.map((network) => ({
            ssid: network.ssid,
            bssid: network.bssid,
            frequency_mhz: network.frequencyMhz,
            rssi_dbm: network.rssiDbm,
            observed_at: network.observedAt,
            cached: network.cached,
          })),
        }
      : null,
  };
}
