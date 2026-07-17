import { describe, expect, it } from "vitest";
import { estimateExportBytes, formatFileSize } from "../src/export";

describe("local export estimates", () => {
  it("decreases with simplification and increases with sidecars", () => {
    const full = estimateExportBytes(500_000, 1_000_000, 4096, null, "glb", false, false);
    const shareable = estimateExportBytes(500_000, 1_000_000, 1024, 50_000, "glb", false, false);
    const withSidecars = estimateExportBytes(500_000, 1_000_000, 1024, 50_000, "glb", true, true);
    expect(shareable).toBeLessThan(full);
    expect(withSidecars).toBeGreaterThan(shareable);
  });

  it("formats readable approximate sizes", () => {
    expect(formatFileSize(512)).toBe("1 KiB");
    expect(formatFileSize(2 * 1024 ** 2)).toBe("2.0 MiB");
    expect(formatFileSize(1.5 * 1024 ** 3)).toBe("1.5 GiB");
  });

  it("estimates untextured point and interchange formats", () => {
    const obj = estimateExportBytes(1000, 0, null, null, "obj", false, false);
    const ply = estimateExportBytes(1000, 0, null, null, "ply", false, false);
    expect(obj).toBeGreaterThan(ply);
    expect(ply).toBeGreaterThan(1024);
  });
});
