import type { CapacitorConfig } from "@capacitor/cli";
const config: CapacitorConfig = {
  appId: "id.nusanet.hotelmaintenance",
  appName: "NUSA MAINTENANCE",
  webDir: "dist",
  android: { allowMixedContent: false },
  server: { androidScheme: "https" },
};
export default config;
