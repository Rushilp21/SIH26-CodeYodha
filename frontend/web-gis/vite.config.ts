import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import path from "node:path";

const dir = path.dirname(fileURLToPath(import.meta.url));

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
  server: { port: 5173 },
});
