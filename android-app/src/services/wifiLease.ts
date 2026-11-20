import { Capacitor, registerPlugin } from "@capacitor/core";
import { wifiService, type Availability, type WifiConnection } from "./wifi";
import type { WifiBinding } from "../types";
type LeaseData = {
  bindingId: string;
  networkHandle: string;
  connection: WifiConnection;
};
interface LeasePlugin {
  beginSpeedtest(): Promise<Availability<LeaseData>>;
  checkSpeedtest(options: { bindingId: string }): Promise<{ valid: boolean }>;
  endSpeedtest(options: { bindingId: string }): Promise<{ released: boolean }>;
}
const plugin = registerPlugin<LeasePlugin>("HotelWifi");
export const nativeSpeedtestAvailable = () =>
  Capacitor.getPlatform() === "android" &&
  Capacitor.isPluginAvailable("HotelWifi");
export type WifiLease = {
  binding: WifiBinding;
  connection: WifiConnection;
  check: () => Promise<boolean>;
  snapshot: () => Promise<WifiConnection>;
  release: () => Promise<void>;
};
export async function acquireWifiLease(): Promise<WifiLease> {
  if (!nativeSpeedtestAvailable())
    throw new Error(
      "Speedtest membutuhkan aplikasi Android dengan plugin Wi-Fi terbaru.",
    );
  const result = await plugin.beginSpeedtest();
  if (!result.available) throw new Error(result.reason);
  const data = result.data;
  if (
    !data?.bindingId ||
    !/^\d{1,30}$/.test(data.networkHandle) ||
    data.connection?.transport !== "wifi" ||
    !data.connection.bssid
  ) {
    if (data?.bindingId)
      await plugin.endSpeedtest({ bindingId: data.bindingId }).catch(() => {});
    throw new Error(
      "Binding Wi-Fi tidak valid. Tidak ada pengujian dijalankan.",
    );
  }
  return {
    binding: {
      id: data.bindingId,
      network_handle: data.networkHandle,
      source: "android_native",
    },
    connection: data.connection,
    check: async () =>
      (await plugin.checkSpeedtest({ bindingId: data.bindingId })).valid ===
      true,
    snapshot: async () => {
      const snapshot = await wifiService.connection();
      if (!snapshot.available) throw new Error(snapshot.reason);
      return snapshot.data;
    },
    release: async () => {
      if (!(await plugin.endSpeedtest({ bindingId: data.bindingId })).released)
        throw new Error(
          "Binding Wi-Fi gagal dilepas. Tutup aplikasi sebelum menguji ulang.",
        );
    },
  };
}
