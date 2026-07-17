import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./",
  build: {
    target: "es2023",
    sourcemap: true,
    assetsInlineLimit: 0,
  },
  server: {
    host: "127.0.0.1",
    strictPort: true,
  },
  test: {
    environment: "node",
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary"],
      include: ["src/export.ts", "src/geometry.ts", "src/layers.ts", "src/units.ts"],
      thresholds: { statements: 95, branches: 90, functions: 95, lines: 95 },
    },
  },
});
