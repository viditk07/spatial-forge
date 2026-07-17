export type ExportFormat = "glb" | "obj" | "ply";

export function estimateExportBytes(
  vertices: number,
  faces: number,
  textureResolution: number | null,
  targetFaceCount: number | null,
  format: ExportFormat,
  includePointCloud: boolean,
  includeCameraPositions: boolean,
): number {
  const effectiveFaces = targetFaceCount === null ? faces : Math.min(faces, targetFaceCount);
  const ratio = faces > 0 ? effectiveFaces / faces : 1;
  const effectiveVertices = Math.ceil(vertices * ratio);
  const formatFactor = format === "obj" ? 1.8 : format === "ply" ? 1.15 : 0.8;
  const geometry = (effectiveVertices * 16 + effectiveFaces * 12) * formatFactor;
  const texture =
    textureResolution !== null && effectiveFaces > 0
      ? textureResolution * textureResolution * 0.75
      : 0;
  const pointCloud = includePointCloud ? vertices * 16 : 0;
  const cameras = includeCameraPositions ? 64 * 1024 : 0;
  return Math.max(Math.ceil(geometry + texture + pointCloud + cameras), 1024);
}

export function formatFileSize(bytes: number): string {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GiB`;
  if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(1)} MiB`;
  return `${Math.max(1, Math.round(bytes / 1024)).toString()} KiB`;
}
