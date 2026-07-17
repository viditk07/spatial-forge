import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { PLYLoader } from "three/examples/jsm/loaders/PLYLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { Bounds3, Point3 } from "./geometry";
import { cameraFrustumVertices, isLocalLayerUrl, type CameraPose } from "./layers";

export type { CameraPose } from "./layers";

export type ModelFormat = "glb" | "gltf" | "obj" | "ply";
export type ModelStatistics = Readonly<{ vertices: number; faces: number }>;

type SupportedMesh = THREE.Mesh<THREE.BufferGeometry, THREE.Material | THREE.Material[]>;

function meshMaterials(mesh: SupportedMesh): THREE.Material[] {
  return Array.isArray(mesh.material) ? mesh.material : [mesh.material];
}

export class SpatialViewer {
  readonly canvas: HTMLCanvasElement;
  readonly scene = new THREE.Scene();
  readonly modelRoot = new THREE.Group();
  readonly selectedPoints: Point3[] = [];

  private readonly camera = new THREE.PerspectiveCamera(48, 1, 0.001, 100_000);
  private readonly renderer: THREE.WebGLRenderer;
  private readonly controls: OrbitControls;
  private readonly raycaster = new THREE.Raycaster();
  private readonly pointer = new THREE.Vector2();
  private readonly grid = new THREE.GridHelper(20, 40, 0x345469, 0x253745);
  private readonly selectionRoot = new THREE.Group();
  private readonly layers = new Map<string, THREE.Object3D>();
  private cropHelper: THREE.Box3Helper | undefined;
  private animationFrame = 0;
  private selectionListener: ((points: readonly Point3[]) => void) | undefined;

  constructor(container: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      preserveDrawingBuffer: true,
    });
    this.canvas = this.renderer.domElement;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.localClippingEnabled = true;
    container.append(this.canvas);

    this.scene.background = new THREE.Color(0x0b1118);
    this.camera.position.set(4, 3, 5);
    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.enableDamping = true;
    this.controls.screenSpacePanning = true;
    this.controls.target.set(0, 0.5, 0);

    this.grid.material.opacity = 0.42;
    this.grid.material.transparent = true;
    this.scene.add(this.grid, this.modelRoot, this.selectionRoot);
    this.scene.add(new THREE.HemisphereLight(0xdbeeff, 0x17202a, 2.2));
    const key = new THREE.DirectionalLight(0xffffff, 2.6);
    key.position.set(4, 8, 5);
    this.scene.add(key);

    this.canvas.addEventListener("pointerdown", this.selectPoint);
    window.addEventListener("resize", this.resize);
    this.resize();
    this.render();
  }

  onSelection(listener: (points: readonly Point3[]) => void): void {
    this.selectionListener = listener;
  }

  async loadFile(file: File): Promise<ModelStatistics> {
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (extension !== "glb" && extension !== "gltf" && extension !== "obj" && extension !== "ply") {
      throw new Error("Supported preview formats are GLB, glTF, OBJ, and PLY.");
    }
    const url = URL.createObjectURL(file);
    try {
      return await this.loadUrl(url, extension);
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async loadBytes(bytes: Uint8Array<ArrayBuffer>, format: ModelFormat): Promise<ModelStatistics> {
    const blob = new Blob([bytes], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    try {
      return await this.loadUrl(url, format);
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async loadModelUrl(url: string, format: ModelFormat): Promise<ModelStatistics> {
    if (!url.startsWith("https://models.spatialforge/")) {
      throw new Error("The desktop host supplied an invalid local model URL.");
    }
    return this.loadUrl(url, format);
  }

  async loadLayerUrl(
    layerId: string,
    url: string,
    format: ModelFormat,
    visible: boolean,
  ): Promise<ModelStatistics> {
    if (!isLocalLayerUrl(url)) {
      throw new Error("The desktop host supplied an invalid local layer URL.");
    }
    const object = await this.parseUrl(url, format);
    this.replaceLayer(layerId, object, visible);
    return this.statistics();
  }

  clearLayers(): void {
    this.clearSelection();
    this.clearCrop();
    for (const object of this.layers.values()) this.disposeObject(object);
    this.layers.clear();
    this.modelRoot.clear();
  }

  setLayerVisible(layerId: string, visible: boolean): ModelStatistics {
    const layer = this.layers.get(layerId);
    if (layer) layer.visible = visible;
    return this.statistics();
  }

  setCameraPoses(cameras: readonly CameraPose[], visible: boolean): ModelStatistics {
    const layer = new THREE.Group();
    const boundsSize = this.modelBoundsSize();
    const size = Math.max(boundsSize * 0.025, 0.02);
    const vertices = cameraFrustumVertices(size);
    for (const camera of cameras) {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(vertices.slice(), 3));
      const frustum = new THREE.LineSegments(
        geometry,
        new THREE.LineBasicMaterial({ color: 0xf2b84b }),
      );
      frustum.position.set(camera.position.x, camera.position.y, camera.position.z);
      frustum.quaternion.set(
        camera.quaternion.x,
        camera.quaternion.y,
        camera.quaternion.z,
        camera.quaternion.w,
      );
      frustum.userData.cameraId = camera.id;
      layer.add(frustum);
    }
    this.replaceLayer("cameras", layer, visible);
    return this.statistics();
  }

  setWireframe(enabled: boolean): void {
    this.modelRoot.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      const mesh = object as SupportedMesh;
      for (const material of meshMaterials(mesh)) {
        if (
          material instanceof THREE.MeshStandardMaterial ||
          material instanceof THREE.MeshBasicMaterial
        ) {
          material.wireframe = enabled;
        }
      }
    });
  }

  setModelVisible(visible: boolean): void {
    this.modelRoot.visible = visible;
  }

  setGridVisible(visible: boolean): void {
    this.grid.visible = visible;
  }

  setLightIntensity(intensity: number): void {
    for (const child of this.scene.children) {
      if (child instanceof THREE.Light) child.intensity = intensity;
    }
  }

  previewCrop(bounds: Bounds3): void {
    this.clearCrop();
    const min = new THREE.Vector3(bounds.min.x, bounds.min.y, bounds.min.z);
    const max = new THREE.Vector3(bounds.max.x, bounds.max.y, bounds.max.z);
    const box = new THREE.Box3(min, max);
    this.cropHelper = new THREE.Box3Helper(box, 0x35b9d6);
    this.scene.add(this.cropHelper);
    const planes = [
      new THREE.Plane(new THREE.Vector3(1, 0, 0), -min.x),
      new THREE.Plane(new THREE.Vector3(-1, 0, 0), max.x),
      new THREE.Plane(new THREE.Vector3(0, 1, 0), -min.y),
      new THREE.Plane(new THREE.Vector3(0, -1, 0), max.y),
      new THREE.Plane(new THREE.Vector3(0, 0, 1), -min.z),
      new THREE.Plane(new THREE.Vector3(0, 0, -1), max.z),
    ];
    this.modelRoot.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      for (const material of meshMaterials(object as SupportedMesh))
        material.clippingPlanes = planes;
    });
  }

  clearCrop(): void {
    if (this.cropHelper) {
      this.scene.remove(this.cropHelper);
      this.cropHelper.geometry.dispose();
      const materials = Array.isArray(this.cropHelper.material)
        ? this.cropHelper.material
        : [this.cropHelper.material];
      for (const material of materials) material.dispose();
      this.cropHelper = undefined;
    }
    this.modelRoot.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      for (const material of meshMaterials(object as SupportedMesh)) material.clippingPlanes = null;
    });
  }

  modelBounds(): Bounds3 | undefined {
    const box = new THREE.Box3().setFromObject(this.modelRoot);
    if (box.isEmpty()) return undefined;
    return {
      min: { x: box.min.x, y: box.min.y, z: box.min.z },
      max: { x: box.max.x, y: box.max.y, z: box.max.z },
    };
  }

  clearSelection(): void {
    this.selectedPoints.splice(0);
    for (const child of [...this.selectionRoot.children]) {
      this.selectionRoot.remove(child);
      if (child instanceof THREE.Mesh) (child as SupportedMesh).geometry.dispose();
    }
    this.selectionListener?.(this.selectedPoints);
  }

  screenshot(): string {
    this.renderer.render(this.scene, this.camera);
    return this.canvas.toDataURL("image/png");
  }

  dispose(): void {
    cancelAnimationFrame(this.animationFrame);
    window.removeEventListener("resize", this.resize);
    this.canvas.removeEventListener("pointerdown", this.selectPoint);
    this.controls.dispose();
    this.renderer.dispose();
  }

  private async parseUrl(url: string, format: ModelFormat): Promise<THREE.Object3D> {
    let object: THREE.Object3D;
    if (format === "glb" || format === "gltf") {
      object = (await new GLTFLoader().loadAsync(url)).scene;
    } else if (format === "obj") {
      object = await new OBJLoader().loadAsync(url);
    } else {
      const geometry = await new PLYLoader().loadAsync(url);
      geometry.computeVertexNormals();
      object = geometry.index
        ? new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0xa9bdca }))
        : new THREE.Points(geometry, new THREE.PointsMaterial({ color: 0xa9bdca, size: 0.01 }));
    }
    return object;
  }

  private async loadUrl(url: string, format: ModelFormat): Promise<ModelStatistics> {
    const object = await this.parseUrl(url, format);
    this.replaceModel(object);
    return this.statistics();
  }

  private replaceModel(object: THREE.Object3D): void {
    this.clearLayers();
    this.replaceLayer("model", object, true);
  }

  private replaceLayer(layerId: string, object: THREE.Object3D, visible: boolean): void {
    const previous = this.layers.get(layerId);
    if (previous) {
      this.modelRoot.remove(previous);
      this.disposeObject(previous);
    }
    object.visible = visible;
    object.userData.layerId = layerId;
    this.layers.set(layerId, object);
    this.modelRoot.add(object);
    if (!visible) return;
    const box = new THREE.Box3().setFromObject(object);
    if (box.isEmpty()) return;
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const radius = Math.max(sphere.radius, 0.01);
    this.controls.target.copy(sphere.center);
    this.camera.near = Math.max(radius / 10_000, 0.0001);
    this.camera.far = Math.max(radius * 100, 100);
    this.camera.position
      .copy(sphere.center)
      .add(new THREE.Vector3(radius * 1.7, radius * 1.1, radius * 1.7));
    this.camera.updateProjectionMatrix();
    this.controls.update();
  }

  statistics(): ModelStatistics {
    let vertices = 0;
    let faces = 0;
    for (const layer of this.layers.values()) {
      if (!layer.visible) continue;
      layer.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          const geometry = (object as SupportedMesh).geometry;
          const positions = geometry.getAttribute("position");
          vertices += positions.count;
          faces += geometry.index ? geometry.index.count / 3 : positions.count / 3;
        } else if (object instanceof THREE.Points) {
          const points = object as THREE.Points<THREE.BufferGeometry, THREE.PointsMaterial>;
          vertices += points.geometry.getAttribute("position").count;
        }
      });
    }
    return { vertices, faces: Math.floor(faces) };
  }

  private disposeObject(object: THREE.Object3D): void {
    object.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const mesh = child as SupportedMesh;
        mesh.geometry.dispose();
        for (const material of meshMaterials(mesh)) material.dispose();
      } else if (child instanceof THREE.Points) {
        const points = child as THREE.Points<THREE.BufferGeometry, THREE.PointsMaterial>;
        points.geometry.dispose();
        points.material.dispose();
      } else if (child instanceof THREE.LineSegments) {
        const lines = child as THREE.LineSegments<THREE.BufferGeometry, THREE.LineBasicMaterial>;
        lines.geometry.dispose();
        lines.material.dispose();
      }
    });
  }

  private readonly resize = (): void => {
    const parent = this.canvas.parentElement;
    if (!parent) return;
    const width = Math.max(parent.clientWidth, 1);
    const height = Math.max(parent.clientHeight, 1);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  };

  private readonly render = (): void => {
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    this.animationFrame = requestAnimationFrame(this.render);
  };

  private readonly selectPoint = (event: PointerEvent): void => {
    if (event.button !== 0 || event.shiftKey || event.ctrlKey) return;
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObject(this.modelRoot, true)[0];
    if (!hit) return;
    if (this.selectedPoints.length === 2) this.clearSelection();
    const point = { x: hit.point.x, y: hit.point.y, z: hit.point.z };
    this.selectedPoints.push(point);
    const radius = Math.max(this.modelBoundsSize() * 0.008, 0.002);
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(radius, 16, 12),
      new THREE.MeshBasicMaterial({
        color: this.selectedPoints.length === 1 ? 0x35b9d6 : 0xf2b84b,
      }),
    );
    marker.position.copy(hit.point);
    this.selectionRoot.add(marker);
    this.selectionListener?.(this.selectedPoints);
  };

  private modelBoundsSize(): number {
    return new THREE.Box3().setFromObject(this.modelRoot).getSize(new THREE.Vector3()).length();
  }
}
