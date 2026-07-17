import { convertDistance, type DistanceUnit } from "./units";

export type Point3 = Readonly<{ x: number; y: number; z: number }>;
export type Bounds3 = Readonly<{ min: Point3; max: Point3 }>;

export function distance(a: Point3, b: Point3): number {
  return Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
}

export function calculateScaleFactor(
  a: Point3,
  b: Point3,
  actualDistance: number,
  unit: DistanceUnit,
): number {
  const reconstructed = distance(a, b);
  if (reconstructed <= Number.EPSILON) throw new Error("Select two distinct points.");
  if (!Number.isFinite(actualDistance) || actualDistance <= 0) {
    throw new Error("Known distance must be greater than zero.");
  }
  return convertDistance(actualDistance, unit, "m") / reconstructed;
}

export function scaledDistance(
  a: Point3,
  b: Point3,
  scaleFactor: number,
  unit: DistanceUnit,
): number {
  if (!Number.isFinite(scaleFactor) || scaleFactor <= 0) {
    throw new Error("Scale factor must be greater than zero.");
  }
  return convertDistance(distance(a, b) * scaleFactor, "m", unit);
}

export function normalizeBounds(a: Point3, b: Point3): Bounds3 {
  return {
    min: { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), z: Math.min(a.z, b.z) },
    max: { x: Math.max(a.x, b.x), y: Math.max(a.y, b.y), z: Math.max(a.z, b.z) },
  };
}

export function containsPoint(bounds: Bounds3, point: Point3): boolean {
  return (
    point.x >= bounds.min.x &&
    point.x <= bounds.max.x &&
    point.y >= bounds.min.y &&
    point.y <= bounds.max.y &&
    point.z >= bounds.min.z &&
    point.z <= bounds.max.z
  );
}
