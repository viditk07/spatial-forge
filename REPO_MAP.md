# Repository Map

- `apps/backend`: local FastAPI API, CLI, persistence, image analysis, jobs, exports.
- `apps/desktop`: WPF solution, MVVM screens, backend lifecycle and API client.
- `apps/viewer`: bundled Three.js/WebView2 application and viewer tests.
- `packages/contracts`: versioned cross-process JSON/OpenAPI contracts.
- `packages/shared`: generated or language-neutral shared assets.
- `packages/test-data`: small redistributable fixtures and fixture licence metadata.
- `engines`: COLMAP, OpenMVS, and Blender adapter documentation/configuration.
- `docs`: architecture, product, development, testing, deployment and user guides.
- `scripts`: cross-component validation, release-notice collection, and packaging entry points.
- `tests/e2e`: mocked-engine whole-workflow tests.
- `samples`: non-user sample configurations and tiny outputs.
- `tools`: development-only utilities; proprietary binaries are excluded.
- `packaging`: reproducible Windows packaging definitions.
- `.github/workflows`: CI and optional Windows packaging/engine jobs.

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
