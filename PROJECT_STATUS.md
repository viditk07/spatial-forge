# Project Status

- Version: 0.2.0
- Completed phases: Phase 0 foundation; Phase 1 backend/CLI; Phase 2 desktop;
  Phase 3 viewer/export; Phase 4 reliability
- In progress: 0.2.0 Windows visual/runtime review and clean-machine release validation
- UI refresh: semantic design system and all desktop screens implemented; Windows screenshots pending
- Tests: 52 backend, 19 viewer, and 19 desktop/theme tests passed
- Backend build: pinned wheel and OpenCV-enabled frozen executable built; authenticated
  loopback health smoke passed
- Viewer build: strict TypeScript production build passed; offline assets bundle into WPF
- Desktop build: refreshed .NET 10 WPF Release cross-build passed with zero warnings or errors
- Packaging: 0.1.0 Windows CI installer succeeded previously; refreshed 0.2.0 installer/runtime and
  screenshot validation have not yet run
- Current blockers: this Linux host cannot run WPF/WebView2 or Inno Setup, and no approved
  real COLMAP/texture-engine binary is available
- Next recommended task: run 0.2.0 Windows packaging, capture the required screen/DPI matrix, and
  complete keyboard/WebView2/clean-machine smoke tests

## Latest validation

On 2026-07-18, `.venv/bin/python scripts/validate.py` completed successfully after the UI refresh:

- Ruff format/check passed for 47 checked Python files; strict mypy passed for 27 source files.
- Pytest passed 52 tests in 6.00 seconds. Coverage includes migrations, authenticated loopback
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
- `dotnet format --verify-no-changes`, the .NET 10 Release build, and 19 desktop tests passed;
  the build reported zero compiler warnings or errors. New coverage verifies required semantic
  resources, WCAG AA token contrast, explicit dark templates and popup resources, accessible names,
  navigation active state, wizard content, and visible hardware/engine fallbacks.

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
57 manifest/licence/notice files on this host. Windows packaging now restores NuGet packages before
notice collection, fails immediately on native-command errors, and emits frozen-backend stdout/stderr
when the health smoke fails. Windows packaging additionally requires the exact Python and .NET
runtime notices before it can build the installer.

No claim is made that the installer or WPF/WebView2 runtime passed Windows execution. COLMAP,
OpenMVS, and Blender remain unbundled pending exact-binary licence approval. Real reconstruction,
texture production, GPU compatibility, installer behavior, and clean-machine launch therefore
remain external release gates.

## UI refresh evidence

The WPF XAML compiler accepted the refreshed resources, shell, all eight major views, and the themed
privacy/confirmation dialog. The redesign retains existing commands, navigation routes, API calls,
WebView message types, model operations, and persistence contracts. Presentation-only properties
humanize project/stage/model/preset values and prevent blank optional capability fields.

This host cannot launch WPF or WebView2, so no claim is made that screenshots, tab traversal,
Windows title-bar composition, 100–200% DPI, or packaged 0.2.0 execution passed. Those remain the
specific Windows UI release gates documented in `docs/product/UI_REFRESH_PLAN.md`.
