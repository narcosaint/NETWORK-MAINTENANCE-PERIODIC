import { Capacitor } from "@capacitor/core";
import { Camera, CameraResultType, CameraSource } from "@capacitor/camera";
import { Geolocation } from "@capacitor/geolocation";
export { wifiService } from "./wifi";
export type { Availability, WifiConnection, WifiScan } from "./wifi";
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
