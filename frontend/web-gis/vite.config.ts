import { defineConfig, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import path from "node:path";

const dir = path.dirname(fileURLToPath(import.meta.url));

const apiProxy: ProxyOptions = {
  target: "http://127.0.0.1:8000",
  changeOrigin: true,
  rewrite: (url) => url.replace(/^\/api/, ""),
  configure(proxy) {
    proxy.on("error", (_error, _request, response) => {
      // Vite otherwise returns an empty 500, hiding that the API is offline.
      if ("writeHead" in response && !response.headersSent && !response.writableEnded) {
        response.writeHead(503, { "Content-Type": "application/json" });
        response.end(JSON.stringify({ detail: "Backend API is not reachable on port 8000. Start Docker Desktop, then run docker compose up -d --build from D:/SIH. npm run dev starts only the frontend." }));
      }
    });
  },
};

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@shared": path.resolve(dir, "../shared"),
      // Shared components are a sibling directory. Pin React resolution to the
      // canonical web-gis install so their JSX compiles on a clean checkout.
      "react/jsx-runtime": path.resolve(dir, "node_modules/react/jsx-runtime.js"),
      "react/jsx-dev-runtime": path.resolve(dir, "node_modules/react/jsx-dev-runtime.js"),
      react: path.resolve(dir, "node_modules/react"),
    },
  },
  server: { port: 5173, proxy: { "/api": apiProxy } },
  preview: { proxy: { "/api": apiProxy } },
});
