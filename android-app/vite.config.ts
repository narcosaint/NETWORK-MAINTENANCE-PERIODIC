import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
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
