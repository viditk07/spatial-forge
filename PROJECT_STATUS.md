# Project Status

- Version: 0.1.0-dev
- Completed phases: Phase 0 foundation; Phase 1 backend/CLI; Phase 2 desktop;
  Phase 3 viewer/export; Phase 4 reliability
- In progress: Phase 5 Windows packaging and clean-machine release validation
- Tests: 52 backend, 19 viewer, and 13 desktop tests passed
- Backend build: pinned wheel and OpenCV-enabled frozen executable built; authenticated
  loopback health smoke passed
- Viewer build: strict TypeScript production build passed; offline assets bundle into WPF
- Desktop build: .NET 10 Release cross-build and 172 MB self-contained `win-x64` publish passed
- Packaging: PyInstaller, self-contained publish, full dependency-notice gate, hash manifest,
  Inno Setup definition, and Windows CI workflow implemented; installer execution unvalidated
- Current blockers: this Linux host cannot run WPF/WebView2 or Inno Setup, and no approved
  real COLMAP/texture-engine binary is available
- Next recommended task: run Windows packaging CI and clean-machine install/viewer smoke tests,
  then run a representative real-engine reconstruction on approved NVIDIA and CPU-only hardware

## Latest validation

On 2026-07-17, `.venv/bin/python scripts/validate.py` completed successfully:

- Ruff format/check passed for 47 checked Python files; strict mypy passed for 27 source files.
- Pytest passed 52 tests in 13.67 seconds. Coverage includes migrations, authenticated loopback
  access, path/command safety, selected project/export directories, immutable imports, EXIF GPS
  and capture devices, OpenCV quality analysis, connected duplicate groups, hardware history,
  CPU/CUDA preflight, durable orchestration, cancellation/retry/recovery, sparse PLY fallback,
  privacy-safe camera-pose export, registered-camera resource counts, multi-layer registration,
  artifact validation, CLI GLB export, optional validated export sidecars, partial-output rollback,
  cleanup, and diagnostics.
- The mocked end-to-end flow imports and analyses images, runs all representative dense stages,
  registers sparse/dense/mesh layers, calibrates scale, and parses a validated GLB export.
- Prettier, ESLint, and strict TypeScript passed; Vitest passed 19 tests with 98% statement,
  95.16% branch, and 100% line coverage for tested geometry/unit/layer/camera/export modules;
  Vite produced the offline viewer bundle.
- `dotnet format --verify-no-changes`, the .NET 10 Release build, and 13 desktop tests passed;
  the build reported zero compiler warnings or errors.

Known non-failing advisories are Starlette's TestClient/httpx deprecation and Vite's 500 kB
chunk-size warning. Both remain follow-up items rather than hidden failures.

## Packaging evidence

The current pinned Python wheel contains Alembic configuration, the camera exporter, advanced
export service, registered-camera resource reporting, and both migrations.
A fresh 282 MB host-native PyInstaller backend explicitly contains OpenCV and fast-simplification,
starts successfully, and returns an authenticated local health response. The fresh self-contained
`win-x64` publish is 172 MB/416 files including `SpatialForge.exe`, WebView2 assemblies, and the
offline multi-layer viewer assets. The bundled viewer was inspected for model-layer virtual hosts,
camera-pose loading, registered-camera display, and advanced export protocols.

The fail-closed notice collector resolved 45 production runtime dependency groups and emitted
57 manifest/licence/notice files on this host. Windows packaging additionally requires the exact
Python and .NET runtime notices before it can build the installer.

No claim is made that the installer or WPF/WebView2 runtime passed Windows execution. COLMAP,
OpenMVS, and Blender remain unbundled pending exact-binary licence approval. Real reconstruction,
texture production, GPU compatibility, installer behavior, and clean-machine launch therefore
remain external release gates.
