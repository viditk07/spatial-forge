import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { PLYLoader } from "three/examples/jsm/loaders/PLYLoader.js";
import { describe, expect, it } from "vitest";

function tinyGlb(): ArrayBuffer {
  const document = JSON.stringify({
    asset: { version: "2.0", generator: "SpatialForge synthetic fixture" },
    buffers: [{ byteLength: 36 }],
    bufferViews: [{ buffer: 0, byteOffset: 0, byteLength: 36, target: 34962 }],
    accessors: [
      {
        bufferView: 0,
        componentType: 5126,
        count: 3,
        type: "VEC3",
        min: [0, 0, 0],
        max: [1, 1, 0],
      },
    ],
    meshes: [{ primitives: [{ attributes: { POSITION: 0 }, mode: 4 }] }],
    nodes: [{ mesh: 0 }],
    scenes: [{ nodes: [0] }],
    scene: 0,
  });
  const jsonBytes = new TextEncoder().encode(document);
  const paddedJsonLength = Math.ceil(jsonBytes.length / 4) * 4;
  const binaryLength = 36;
  const buffer = new ArrayBuffer(12 + 8 + paddedJsonLength + 8 + binaryLength);
  const view = new DataView(buffer);
  view.setUint32(0, 0x46546c67, true);
  view.setUint32(4, 2, true);
  view.setUint32(8, buffer.byteLength, true);
  view.setUint32(12, paddedJsonLength, true);
  view.setUint32(16, 0x4e4f534a, true);
  const jsonChunk = new Uint8Array(buffer, 20, paddedJsonLength);
  jsonChunk.fill(0x20);
  jsonChunk.set(jsonBytes);
  const binaryHeader = 20 + paddedJsonLength;
  view.setUint32(binaryHeader, binaryLength, true);
  view.setUint32(binaryHeader + 4, 0x004e4942, true);
  const positions = new Float32Array(buffer, binaryHeader + 8, 9);
  positions.set([0, 0, 0, 1, 0, 0, 0, 1, 0]);
  return buffer;
}

describe("bundled model loaders", () => {
  it("parses a synthetic GLB without network access", async () => {
    const gltf = await new GLTFLoader().parseAsync(tinyGlb(), "");
    const mesh = gltf.scene.getObjectByProperty("type", "Mesh") as THREE.Mesh;
    expect(mesh.geometry.getAttribute("position").count).toBe(3);
  });

  it("parses an ASCII PLY fixture", () => {
    const source = `ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
element face 1
property list uchar int vertex_indices
end_header
0 0 0
1 0 0
0 1 0
3 0 1 2
`;
    const geometry = new PLYLoader().parse(new TextEncoder().encode(source).buffer);
    expect(geometry.getAttribute("position").count).toBe(3);
    expect(geometry.index?.count).toBe(3);
  });
});
