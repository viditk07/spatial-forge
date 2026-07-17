import { describe, expect, it } from "vitest";
import {
  calculateScaleFactor,
  containsPoint,
  distance,
  normalizeBounds,
  scaledDistance,
} from "../src/geometry";

describe("geometry", () => {
  const origin = { x: 0, y: 0, z: 0 };

  it("calculates three-dimensional distance", () => {
    expect(distance(origin, { x: 2, y: 3, z: 6 })).toBe(7);
  });

  it("calibrates reconstructed coordinates in metres", () => {
    const factor = calculateScaleFactor(origin, { x: 2, y: 0, z: 0 }, 150, "cm");
    expect(factor).toBe(0.75);
    expect(scaledDistance(origin, { x: 4, y: 0, z: 0 }, factor, "m")).toBe(3);
  });

  it("rejects invalid scale references", () => {
    expect(() => calculateScaleFactor(origin, origin, 1, "m")).toThrow("distinct");
    expect(() => calculateScaleFactor(origin, { x: 1, y: 0, z: 0 }, 0, "m")).toThrow("greater");
    expect(() => scaledDistance(origin, { x: 1, y: 0, z: 0 }, Number.NaN, "m")).toThrow("greater");
  });

  it("normalizes crop bounds and tests containment", () => {
    const bounds = normalizeBounds({ x: 4, y: -1, z: 9 }, { x: 1, y: 3, z: 2 });
    expect(bounds).toEqual({ min: { x: 1, y: -1, z: 2 }, max: { x: 4, y: 3, z: 9 } });
    expect(containsPoint(bounds, { x: 1, y: 0, z: 9 })).toBe(true);
    expect(containsPoint(bounds, { x: 0, y: 0, z: 9 })).toBe(false);
  });
});
