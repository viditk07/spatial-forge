# Repository Map

- `apps/backend`: local FastAPI API, CLI, persistence, image analysis, jobs, exports.
- `apps/desktop`: WPF solution, MVVM screens, backend lifecycle and API client.
  Shared semantic tokens and templates live in `src/SpatialForge.Desktop/Resources`; the themed
  confirmation/privacy dialog is `SpatialForgeDialog`; presentation/resource tests live beside
  MVVM tests under `tests/SpatialForge.Desktop.Core.Tests`.
- `apps/viewer`: bundled Three.js/WebView2 application and viewer tests.
- `packages/test-data`: small redistributable fixtures and fixture licence metadata
  (currently `models/tetrahedron.ply`).
- `packages/contracts`: reserved for versioned cross-process JSON/OpenAPI contracts (currently empty).
- `packages/shared`: reserved for generated or language-neutral shared assets (currently empty).
- `engines`: reserved for COLMAP, OpenMVS, and Blender adapter documentation/configuration
  (currently empty). The engine adapter *code* lives in
  `apps/backend/src/spatialforge_backend/engines`.
- `docs`: architecture, product, development, testing, deployment and user guides.
- `scripts`: cross-component validation, release-notice collection, and packaging entry points.
- `samples`: reserved for non-user sample configurations and tiny outputs (currently empty).
- `tools`: reserved for development-only utilities; proprietary binaries are excluded (currently empty).
- `packaging`: reproducible Windows packaging definitions.
- `.github/workflows`: CI and optional Windows packaging/engine jobs.

The mocked-engine whole-workflow test lives in
`apps/backend/tests/test_job_orchestration.py`; the top-level `tests/` directory is reserved for
future cross-component end-to-end tests and is currently empty.

Backend entry points are `spatialforge_backend.__main__` and
`spatialforge_backend.api.app:create_app`. Database models live under `db`; migrations
live under `migrations`; services own safe filesystem, reconstruction, image, and local
mesh/export behavior. `apps/viewer/src/viewer.ts` owns Three.js rendering while
`geometry.ts` and `units.ts` contain independently tested measurement logic. The WPF
`ModelReviewView` hosts only built viewer assets through locked WebView2 virtual hosts.
Each reconstruction artifact receives an isolated `modelN.spatialforge` virtual host. The viewer
keeps project-scoped sparse, dense, and mesh objects in independently visible scene groups rather
than remapping one shared model host.
The reconstruction pipeline checkpoints image preparation, feature extraction, matching, sparse
mapping, sparse PLY conversion, privacy-safe camera-pose export, undistortion, depth maps, dense
fusion, and Poisson meshing. CPU presets skip only the four dense stages and retain a previewable
sparse point cloud plus registered camera frustums.

The desktop UI audit and plan live under `docs/product`; the design-system and reusable-component
references live under `docs/architecture`.
