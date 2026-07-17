import { describe, expect, it } from "vitest";
import { cameraFrustumVertices, isCameraPose, isLocalLayerUrl } from "../src/layers";

describe("desktop model-layer URLs", () => {
  it("accepts isolated WebView virtual hosts", () => {
    expect(isLocalLayerUrl("https://model0.spatialforge/sparse.ply")).toBe(true);
    expect(isLocalLayerUrl("https://model12.spatialforge/room%20mesh.glb")).toBe(true);
  });

  it.each([
    "http://model0.spatialforge/model.ply",
    "https://model0.spatialforge.evil.example/model.ply",
    "https://user@model0.spatialforge/model.ply",
    "https://modelx.spatialforge/model.ply",
    "not a URL",
  ])("rejects untrusted URL %s", (url) => {
    expect(isLocalLayerUrl(url)).toBe(false);
  });
});

describe("camera overlays", () => {
  it("validates finite numeric poses", () => {
    expect(
      isCameraPose({
        id: 1,
        position: { x: 1, y: 2, z: 3 },
        quaternion: { x: 0, y: 0, z: 0, w: 1 },
      }),
    ).toBe(true);
    expect(
      isCameraPose({
        id: 1,
        position: { x: Number.NaN, y: 2, z: 3 },
        quaternion: { x: 0, y: 0, z: 0, w: 1 },
      }),
    ).toBe(false);
  });

  it("creates eight scaled frustum line segments", () => {
    const vertices = cameraFrustumVertices(2);
    expect(vertices).toHaveLength(48);
    expect(Math.max(...vertices)).toBe(2);
    expect(() => cameraFrustumVertices(0)).toThrow("positive");
  });
});
