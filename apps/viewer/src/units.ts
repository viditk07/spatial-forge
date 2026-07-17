export const distanceUnits = ["mm", "cm", "m", "in", "ft"] as const;
export type DistanceUnit = (typeof distanceUnits)[number];

const metresPerUnit: Readonly<Record<DistanceUnit, number>> = {
  mm: 0.001,
  cm: 0.01,
  m: 1,
  in: 0.0254,
  ft: 0.3048,
};

export function convertDistance(value: number, from: DistanceUnit, to: DistanceUnit): number {
  if (!Number.isFinite(value)) throw new Error("Distance must be finite.");
  return (value * metresPerUnit[from]) / metresPerUnit[to];
}

export function formatDistance(value: number, unit: DistanceUnit): string {
  if (!Number.isFinite(value)) return `— ${unit}`;
  const digits = Math.abs(value) >= 100 ? 1 : Math.abs(value) >= 10 ? 2 : 3;
  return `≈ ${value.toFixed(digits)} ${unit}`;
}
