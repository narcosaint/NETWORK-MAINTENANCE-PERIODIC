import type { Availability } from "./native";
import type { Run } from "../types";
export interface LibreSpeedService {
  capability(): Availability<never>;
  start(pointId: string): Promise<Run>;
}
// No test runs are created until Phase 5 can associate a run with the physical point
// and verify Android Wi-Fi transport. Existing server run history remains readable.
export const libreSpeedService: LibreSpeedService = {
  capability() {
    return {
      available: false,
      reason:
        "Belum tersedia · pengujian LibreSpeed Android per titik menunggu integrasi Phase 5.",
    };
  },
  async start() {
    throw new Error("Belum tersedia. Tidak ada speedtest yang dijalankan.");
  },
};
