/** Accept only WebView2 virtual hosts created by the trusted desktop shell. */
export function isLocalLayerUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:" &&
      /^model\d+\.spatialforge$/u.test(url.hostname) &&
      url.port === "" &&
      url.username === "" &&
      url.password === ""
    );
  } catch {
    return false;
  }
}

export type CameraPose = Readonly<{
  id: number;
  position: Readonly<{ x: number; y: number; z: number }>;
  quaternion: Readonly<{ x: number; y: number; z: number; w: number }>;
}>;

export function isCameraPose(value: unknown): value is CameraPose {
  if (!value || typeof value !== "object") return false;
  const camera = value as {
    id?: unknown;
    position?: Record<string, unknown>;
    quaternion?: Record<string, unknown>;
  };
  const numbers = [
    camera.position?.x,
    camera.position?.y,
    camera.position?.z,
    camera.quaternion?.x,
    camera.quaternion?.y,
    camera.quaternion?.z,
    camera.quaternion?.w,
  ];
  return (
    typeof camera.id === "number" &&
    Number.isInteger(camera.id) &&
    numbers.every((number) => typeof number === "number" && Number.isFinite(number))
  );
}

const unitFrustumSegments = [
  0, 0, 0, -0.7, -0.5, 1, 0, 0, 0, 0.7, -0.5, 1, 0, 0, 0, 0.7, 0.5, 1, 0, 0, 0, -0.7, 0.5, 1, -0.7,
  -0.5, 1, 0.7, -0.5, 1, 0.7, -0.5, 1, 0.7, 0.5, 1, 0.7, 0.5, 1, -0.7, 0.5, 1, -0.7, 0.5, 1, -0.7,
  -0.5, 1,
] as const;

export function cameraFrustumVertices(size: number): Float32Array {
  if (!Number.isFinite(size) || size <= 0) throw new Error("Camera size must be positive.");
  return Float32Array.from(unitFrustumSegments, (coordinate) => coordinate * size);
}
