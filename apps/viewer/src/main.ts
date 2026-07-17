import "./style.css";
import { listenForHostMessages, postHostEvent } from "./bridge";
import { estimateExportBytes, formatFileSize, type ExportFormat } from "./export";
import { calculateScaleFactor, normalizeBounds, scaledDistance, type Bounds3 } from "./geometry";
import { isCameraPose } from "./layers";
import { distanceUnits, formatDistance, type DistanceUnit } from "./units";
import { SpatialViewer, type ModelFormat } from "./viewer";

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Viewer host element is missing.");

app.innerHTML = `
  <header><div><span class="mark">SF</span><strong>Model Review</strong></div><span class="private">● LOCAL ONLY</span></header>
  <main>
    <section class="viewport" id="viewport"><div class="empty" id="empty">Drop a GLB, glTF, OBJ, or PLY model here</div></section>
    <aside>
      <section class="panel">
        <h2>Model</h2>
        <label class="file">Open model<input id="file" type="file" accept=".glb,.gltf,.obj,.ply" /></label>
        <div class="stats"><span>Vertices</span><output id="vertices">—</output><span>Faces</span><output id="faces">—</output></div>
        <div class="layers" id="layers" hidden></div>
        <label class="switch"><input id="model-visible" type="checkbox" checked /> Model</label>
        <label class="switch"><input id="grid-visible" type="checkbox" checked /> Grid</label>
        <label class="switch"><input id="wireframe" type="checkbox" /> Wireframe</label>
        <label>Lighting<input id="lighting" type="range" min="0" max="4" value="2" step="0.1" /></label>
      </section>
      <section class="panel">
        <h2>Selection & measurement</h2>
        <p class="hint">Click two points on the model. Measurements are approximate.</p>
        <output id="selection">No points selected</output>
        <div class="row"><input id="known-distance" type="number" min="0" step="any" placeholder="Known distance" /><select id="unit">${distanceUnits.map((unit) => `<option>${unit}</option>`).join("")}</select></div>
        <button id="apply-scale" class="primary">Apply scale</button>
        <button id="clear-selection">Clear points</button>
      </section>
      <section class="panel">
        <h2>Crop</h2>
        <p class="hint">Preview is reversible. Applying sends the bounds to SpatialForge.</p>
        <div class="crop-grid" id="crop-fields"></div>
        <button id="fit-crop">Use model bounds</button>
        <button id="preview-crop">Preview crop</button>
        <button id="apply-crop" class="primary">Apply crop</button>
        <button id="clear-crop">Clear preview</button>
      </section>
      <section class="panel actions"><button id="screenshot">Save screenshot</button></section>
      <section class="panel">
        <h2>Export</h2>
        <label>Preset<select id="export-preset"><option value="shareable">Shareable</option><option value="balanced" selected>Balanced</option><option value="full">Full Quality</option></select></label>
        <label>Format<select id="export-format"><option value="glb">GLB</option><option value="obj">OBJ</option><option value="ply">PLY</option></select></label>
        <label class="switch"><input id="include-point-cloud" type="checkbox" /> Point-cloud sidecar</label>
        <label class="switch"><input id="include-cameras" type="checkbox" /> Camera-position sidecar</label>
        <div class="stats"><span>Rough size</span><output id="estimated-size">—</output></div>
        <p class="hint">Estimate varies with source materials and compression.</p>
        <button id="export" class="primary">Export locally</button>
      </section>
      <p class="error" id="error" role="alert"></p>
    </aside>
  </main>`;

function element<T extends HTMLElement>(id: string): T {
  const value = document.querySelector<T>(`#${id}`);
  if (!value) throw new Error(`Viewer control ${id} is missing.`);
  return value;
}

const cropKeys = ["min-x", "min-y", "min-z", "max-x", "max-y", "max-z"] as const;
const cropFields = element<HTMLDivElement>("crop-fields");
for (const key of cropKeys) {
  const label = document.createElement("label");
  label.textContent = key.replace("-", " ");
  const input = document.createElement("input");
  input.id = key;
  input.type = "number";
  input.step = "any";
  label.append(input);
  cropFields.append(label);
}

const viewer = new SpatialViewer(element("viewport"));
const error = element<HTMLParagraphElement>("error");
let scaleFactor = 1;
let latestStatistics = { vertices: 0, faces: 0 };
const layerControls = new Map<string, HTMLInputElement>();

function reportError(reason: unknown): void {
  const message = reason instanceof Error ? reason.message : "The model could not be processed.";
  error.textContent = message;
  postHostEvent({ type: "error", message });
}

function displayStatistics(statistics: { vertices: number; faces: number }): void {
  latestStatistics = statistics;
  element<HTMLOutputElement>("vertices").value = statistics.vertices.toLocaleString();
  element<HTMLOutputElement>("faces").value = statistics.faces.toLocaleString();
  element("empty").hidden = true;
  postHostEvent({ type: "statistics", ...statistics });
  updateExportEstimate();
}

function clearLayerControls(): void {
  layerControls.clear();
  element<HTMLDivElement>("layers").replaceChildren();
  element<HTMLDivElement>("layers").hidden = true;
}

function upsertLayerControl(layerId: string, label: string, visible: boolean): void {
  let checkbox = layerControls.get(layerId);
  if (!checkbox) {
    const row = document.createElement("label");
    row.className = "layer";
    checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.addEventListener("change", () => {
      displayStatistics(viewer.setLayerVisible(layerId, checkbox?.checked ?? false));
    });
    const text = document.createElement("span");
    text.textContent = label;
    row.append(checkbox, text);
    element<HTMLDivElement>("layers").append(row);
    layerControls.set(layerId, checkbox);
  }
  checkbox.checked = visible;
  element<HTMLDivElement>("layers").hidden = false;
}

viewer.onSelection((points) => {
  postHostEvent({ type: "selection", points });
  const output = element<HTMLOutputElement>("selection");
  if (points.length < 2) {
    output.value = points.length === 1 ? "Point 1 selected — select point 2" : "No points selected";
    return;
  }
  const first = points[0];
  const second = points[1];
  if (!first || !second) return;
  const unit = element<HTMLSelectElement>("unit").value as DistanceUnit;
  output.value = formatDistance(scaledDistance(first, second, scaleFactor, unit), unit);
});

element<HTMLInputElement>("file").addEventListener("change", (event) => {
  const file = (event.currentTarget as HTMLInputElement).files?.[0];
  if (!file) return;
  error.textContent = "";
  clearLayerControls();
  void viewer.loadFile(file).then(displayStatistics).catch(reportError);
});

element("viewport").addEventListener("dragover", (event) => event.preventDefault());
element("viewport").addEventListener("drop", (event) => {
  event.preventDefault();
  const file = event.dataTransfer?.files[0];
  if (!file) return;
  clearLayerControls();
  void viewer.loadFile(file).then(displayStatistics).catch(reportError);
});

element<HTMLInputElement>("model-visible").addEventListener("change", (event) =>
  viewer.setModelVisible((event.currentTarget as HTMLInputElement).checked),
);
element<HTMLInputElement>("grid-visible").addEventListener("change", (event) =>
  viewer.setGridVisible((event.currentTarget as HTMLInputElement).checked),
);
element<HTMLInputElement>("wireframe").addEventListener("change", (event) =>
  viewer.setWireframe((event.currentTarget as HTMLInputElement).checked),
);
element<HTMLInputElement>("lighting").addEventListener("input", (event) =>
  viewer.setLightIntensity(Number((event.currentTarget as HTMLInputElement).value)),
);

element("clear-selection").addEventListener("click", () => viewer.clearSelection());
element("apply-scale").addEventListener("click", () => {
  try {
    const first = viewer.selectedPoints[0];
    const second = viewer.selectedPoints[1];
    if (!first || !second) throw new Error("Select two points before applying scale.");
    const actualDistance = Number(element<HTMLInputElement>("known-distance").value);
    const unit = element<HTMLSelectElement>("unit").value as DistanceUnit;
    scaleFactor = calculateScaleFactor(first, second, actualDistance, unit);
    element<HTMLOutputElement>("selection").value = formatDistance(actualDistance, unit);
    postHostEvent({
      type: "scale",
      points: [first, second],
      scaleFactor,
      actualDistance,
      unit,
    });
    error.textContent = "";
  } catch (reason) {
    reportError(reason);
  }
});

function setCropFields(bounds: Bounds3): void {
  const values = [
    bounds.min.x,
    bounds.min.y,
    bounds.min.z,
    bounds.max.x,
    bounds.max.y,
    bounds.max.z,
  ];
  cropKeys.forEach((key, index) => {
    element<HTMLInputElement>(key).value = String(values[index]);
  });
}

function readCropFields(): Bounds3 {
  const values = cropKeys.map((key) => Number(element<HTMLInputElement>(key).value));
  if (values.some((value) => !Number.isFinite(value)))
    throw new Error("Enter all six crop bounds.");
  const coordinate = (index: number): number => {
    const value = values[index];
    if (value === undefined) throw new Error("Enter all six crop bounds.");
    return value;
  };
  return normalizeBounds(
    { x: coordinate(0), y: coordinate(1), z: coordinate(2) },
    { x: coordinate(3), y: coordinate(4), z: coordinate(5) },
  );
}

element("fit-crop").addEventListener("click", () => {
  const bounds = viewer.modelBounds();
  if (bounds) setCropFields(bounds);
});
element("preview-crop").addEventListener("click", () => {
  try {
    viewer.previewCrop(readCropFields());
  } catch (reason) {
    reportError(reason);
  }
});
element("clear-crop").addEventListener("click", () => viewer.clearCrop());
element("apply-crop").addEventListener("click", () => {
  try {
    const bounds = readCropFields();
    viewer.previewCrop(bounds);
    postHostEvent({ type: "crop", ...bounds });
  } catch (reason) {
    reportError(reason);
  }
});

element("screenshot").addEventListener("click", () => {
  const link = document.createElement("a");
  link.download = `spatialforge-${new Date().toISOString().replaceAll(":", "-")}.png`;
  link.href = viewer.screenshot();
  link.click();
});

function exportSettings(): {
  textureResolution: number;
  targetFaceCount: number | null;
} {
  const preset = element<HTMLSelectElement>("export-preset").value;
  const settings = {
    shareable: { textureResolution: 1024, targetFaceCount: 50_000 },
    balanced: { textureResolution: 2048, targetFaceCount: 250_000 },
    full: { textureResolution: 4096, targetFaceCount: null },
  } as const;
  return preset === "shareable"
    ? settings.shareable
    : preset === "full"
      ? settings.full
      : settings.balanced;
}

function updateExportEstimate(): void {
  const format = element<HTMLSelectElement>("export-format").value as ExportFormat;
  const selected = exportSettings();
  const bytes = estimateExportBytes(
    latestStatistics.vertices,
    latestStatistics.faces,
    selected.textureResolution,
    selected.targetFaceCount,
    format,
    element<HTMLInputElement>("include-point-cloud").checked,
    element<HTMLInputElement>("include-cameras").checked,
  );
  element<HTMLOutputElement>("estimated-size").value = formatFileSize(bytes);
}

for (const controlId of [
  "export-preset",
  "export-format",
  "include-point-cloud",
  "include-cameras",
]) {
  element(controlId).addEventListener("change", updateExportEstimate);
}

element("export").addEventListener("click", () => {
  const format = element<HTMLSelectElement>("export-format").value as ExportFormat;
  const selected = exportSettings();
  postHostEvent({
    type: "export",
    format,
    ...selected,
    includePointCloud: element<HTMLInputElement>("include-point-cloud").checked,
    includeCameraPositions: element<HTMLInputElement>("include-cameras").checked,
  });
});

/* Keep the initial estimate visible before a model is loaded. */
updateExportEstimate();

listenForHostMessages((message) => {
  if (!message || typeof message !== "object") return;
  const request = message as {
    type?: unknown;
    format?: unknown;
    dataBase64?: unknown;
    layerId?: unknown;
    label?: unknown;
    visible?: unknown;
    url?: unknown;
    cameras?: unknown;
  };
  if (request.type === "clearLayers") {
    viewer.clearLayers();
    clearLayerControls();
    displayStatistics(viewer.statistics());
    element("empty").hidden = false;
    return;
  }
  if (
    request.type === "loadCameras" &&
    Array.isArray(request.cameras) &&
    typeof request.visible === "boolean"
  ) {
    const cameras = request.cameras.filter(isCameraPose);
    if (cameras.length !== request.cameras.length) {
      reportError(new Error("The desktop host supplied invalid camera positions."));
      return;
    }
    upsertLayerControl("cameras", "cameras", request.visible);
    displayStatistics(viewer.setCameraPoses(cameras, request.visible));
    return;
  }
  if (
    request.type === "setLayerVisibility" &&
    typeof request.layerId === "string" &&
    typeof request.visible === "boolean"
  ) {
    const label = typeof request.label === "string" ? request.label : request.layerId;
    upsertLayerControl(request.layerId, label, request.visible);
    displayStatistics(viewer.setLayerVisible(request.layerId, request.visible));
    return;
  }
  if (
    request.type === "loadLayerUrl" &&
    typeof request.layerId === "string" &&
    typeof request.url === "string" &&
    typeof request.visible === "boolean" &&
    ["glb", "gltf", "obj", "ply"].includes(String(request.format))
  ) {
    const label = typeof request.label === "string" ? request.label : request.layerId;
    upsertLayerControl(request.layerId, label, request.visible);
    void viewer
      .loadLayerUrl(request.layerId, request.url, request.format as ModelFormat, request.visible)
      .then(displayStatistics)
      .catch(reportError);
    return;
  }
  if (
    request.type === "loadModelUrl" &&
    typeof (request as { url?: unknown }).url === "string" &&
    ["glb", "gltf", "obj", "ply"].includes(String(request.format))
  ) {
    void viewer
      .loadModelUrl((request as { url: string }).url, request.format as ModelFormat)
      .then(displayStatistics)
      .catch(reportError);
    return;
  }
  if (request.type !== "loadModel" || typeof request.dataBase64 !== "string") return;
  if (!["glb", "gltf", "obj", "ply"].includes(String(request.format))) return;
  try {
    const binary = atob(request.dataBase64);
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    void viewer
      .loadBytes(bytes, request.format as ModelFormat)
      .then(displayStatistics)
      .catch(reportError);
  } catch (reason) {
    reportError(reason);
  }
});

postHostEvent({ type: "ready" });
