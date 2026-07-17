import { describe, expect, it } from "vitest";
import { convertDistance, formatDistance } from "../src/units";

describe("distance units", () => {
  it("converts metric and imperial distances", () => {
    expect(convertDistance(1, "m", "cm")).toBe(100);
    expect(convertDistance(1, "ft", "in")).toBeCloseTo(12);
    expect(convertDistance(25.4, "mm", "in")).toBeCloseTo(1);
  });

  it("rejects non-finite conversions and formats approximate values", () => {
    expect(() => convertDistance(Number.POSITIVE_INFINITY, "m", "ft")).toThrow("finite");
    expect(formatDistance(2.5, "m")).toBe("≈ 2.500 m");
    expect(formatDistance(Number.NaN, "cm")).toBe("— cm");
  });
});
