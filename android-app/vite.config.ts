import { defineConfig, loadEnv, type Plugin } from "vite";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
function libreSpeedAssets(): Plugin {
  const source = fileURLToPath(
    new URL("../backend/app/web/librespeed/", import.meta.url),
  );
  const files = ["speedtest_worker.js", "LICENSE", "SOURCE.json"];
  return {
    name: "hotel-librespeed-assets",
    generateBundle() {
      for (const name of files)
        this.emitFile({
          type: "asset",
          fileName: "librespeed/" + name,
          source: readFileSync(source + name),
        });
    },
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const name = files.find(
          (file) => request.url?.split("?")[0] === "/librespeed/" + file,
        );
        if (!name) return next();
        response.setHeader(
          "Content-Type",
          name.endsWith(".js")
            ? "text/javascript"
            : name.endsWith(".json")
              ? "application/json"
              : "text/plain",
        );
        response.end(readFileSync(source + name));
      });
    },
  };
}
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react(), libreSpeedAssets()],
    server: {
      host: "127.0.0.1",
      ...(env.DEV_API_TARGET
        ? {
            proxy: {
              "/api": {
                target: env.DEV_API_TARGET,
                changeOrigin: true,
                rewrite: (path: string) => path.replace(/^\/api/, ""),
              },
            },
          }
        : {}),
    },
    preview: { host: "127.0.0.1" },
  };
});
