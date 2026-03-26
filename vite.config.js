import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    // Keep the root admin app isolated from legacy HTML entrypoints elsewhere in the repo.
    entries: [path.resolve(__dirname, "index.html")],
    esbuildOptions: {
      loader: {
        ".js": "jsx",
      },
    },
  },
  build: {
    cssMinify: false,
  },
});
