import { Capacitor } from "@capacitor/core";
import { Camera, CameraResultType, CameraSource } from "@capacitor/camera";
import { Geolocation } from "@capacitor/geolocation";
export type Availability<T> =
  { available: true; data: T } | { available: false; reason: string };
export type WifiConnection = {
  ssid: string | null;
  bssid: string | null;
  frequencyMhz: number | null;
  channel: number | null;
  band: "2.4 GHz" | "5 GHz" | null;
  rssiDbm: number | null;
  linkSpeedMbps: number | null;
  ipAddress: string | null;
  gateway: string | null;
  observedAt: string;
  source: "android_native";
};
export type WifiScan = {
  ssid: string;
  bssid: string;
  rssiDbm: number;
  frequencyMhz: number;
  channel: number;
  observedAt: string;
  cached: boolean;
};
export interface WifiService {
  connection(): Promise<Availability<WifiConnection>>;
  scan(band: "2.4 GHz" | "5 GHz"): Promise<Availability<WifiScan[]>>;
}
// Phase 4 implements this interface using Android APIs. No radio plugin is registered yet.
export const wifiService: WifiService = {
  async connection() {
    return {
      available: false,
      reason: "Belum tersedia · integrasi Wi-Fi native menunggu Phase 4.",
    };
  },
  async scan() {
    return {
      available: false,
      reason: "Belum tersedia · belum ada hasil scan Android.",
    };
  },
};
export const gpsService = {
  async current() {
    const result = await Geolocation.getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 0,
    });
    const { latitude, longitude, accuracy } = result.coords;
    if (
      ![latitude, longitude, accuracy].every(Number.isFinite) ||
      Math.abs(latitude) > 90 ||
      Math.abs(longitude) > 180 ||
      accuracy < 0
    )
      throw new Error("Hasil GPS tidak valid. Coba kembali.");
    return {
      latitude,
      longitude,
      accuracy_m: accuracy,
      device_time: new Date(result.timestamp).toISOString(),
    };
  },
};
export const cameraService = {
  async capture(): Promise<Blob> {
    if (!Capacitor.isNativePlatform())
      throw new Error(
        "Kamera native belum tersedia di browser. Gunakan pilih foto.",
      );
    const photo = await Camera.getPhoto({
      quality: 85,
      resultType: CameraResultType.Uri,
      source: CameraSource.Camera,
      correctOrientation: true,
    });
    if (!photo.webPath) throw new Error("Foto tidak tersedia.");
    const response = await fetch(photo.webPath);
    if (!response.ok) throw new Error("Foto tidak dapat dibaca.");
    return response.blob();
  },
};
