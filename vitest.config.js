import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup-vitest.js"],
    include: ["admin-ui/src/**/*.test.{js,jsx}"],
    exclude: ["tests/unit/**", "apps/shopify-widget/**", "dist/**", "node_modules/**"],
    css: true,
  },
});
