# Project Status

- Version: 0.2.1
- Completed phases: Phase 0 foundation; Phase 1 backend/CLI; Phase 2 desktop;
  Phase 3 viewer/export; Phase 4 reliability
- In progress: 0.2.1 Windows visual/runtime review, signed production release, and clean-machine validation
- UI refresh: semantic design system and all desktop screens implemented; Windows screenshots pending
- Tests: 58 backend, 19 viewer, and 21 desktop/theme tests passed
- Backend build: pinned wheel and OpenCV-enabled frozen executable built; authenticated
  loopback health smoke passed
- Viewer build: strict TypeScript production build passed; offline assets bundle into WPF
- Desktop build: refreshed .NET 10 WPF Release cross-build passed with zero warnings or errors
- Packaging: older Windows CI installers succeeded; remediated 0.2.1 installer/runtime and
  screenshot validation have not yet run
- Current blockers: this Linux host cannot run WPF/WebView2 or Inno Setup, and no approved
  real COLMAP/texture-engine binary is available
- Public-source audit: host remediation complete; no known Python/npm/NuGet advisories,
  high-confidence repository secrets, personal-email commit metadata, or large binary blobs are
  reachable from the rewritten local `main` history; force-with-lease push pending
- Next recommended task: force-with-lease the sanitised history, enable GitHub private vulnerability
  reporting/rulesets, then run Windows packaging and the required WebView2/80-photo/DPI smoke matrix

## Public visibility hardening

On 2026-07-19, the pre-publication audit findings were remediated on the development host:

- Pillow was upgraded from 11.3.0 to 12.3.0. Fresh `pip-audit`, `npm audit --omit=dev`, and NuGet
  direct/transitive scans each reported no known vulnerabilities.
- The application now has an explicit source-visible evaluation licence, packaged backend licence
  metadata, security/contribution/conduct policies, and code ownership.
- Every GitHub Action reference is pinned to a full commit SHA; Inno Setup is pinned to 6.7.1.
- WebView navigation validates the exact trusted origin. Model virtual hosts permit the CORS-checked
  Three.js loader request and the CSP permits only the local `*.spatialforge` host namespace.
- The desktop's global 30-second HTTP timeout was removed and Uvicorn access logging disabled. An
  80-image synthetic import/analysis regression passed; full-resolution Windows reproduction remains.
- Windows packaging emits relative checksum paths and supports optional signing with fail-closed
  `-RequireSigning` validation. The current beta artifact remains unsigned and is documented as such.
- Existing 0.1.0/0.2.0 installers were built before the Pillow 12.3.0 remediation and must not be
  exposed with a public repository. Rebuild from the sanitised branch, rerun the Windows package
  smoke, and replace or remove those release assets before changing repository visibility.

## Latest validation

On 2026-07-19, the aggregate host validation and explicit follow-up commands completed successfully
after public-visibility hardening:

- Ruff format/check passed for 47 checked Python files; strict mypy passed for 27 source files.
- Pytest passed 58 tests in 18.68 seconds. Coverage includes migrations, authenticated loopback
  access, path/command safety, selected project/export directories, immutable imports, EXIF GPS
  and capture devices, OpenCV quality analysis, connected duplicate groups, hardware history,
  CPU/CUDA preflight, durable orchestration, cancellation/retry/recovery, sparse PLY fallback,
  privacy-safe camera-pose export, registered-camera resource counts, multi-layer registration,
  artifact validation, CLI GLB export, optional validated export sidecars, partial-output rollback,
  cleanup, diagnostics, the backend access-log policy, and an 80-image import/analysis regression.
- The mocked end-to-end flow imports and analyses images, runs all representative dense stages,
  registers sparse/dense/mesh layers, calibrates scale, and parses a validated GLB export.
- Prettier, ESLint, and strict TypeScript passed; Vitest passed 19 tests with 98% statement,
  95.16% branch, and 100% line coverage for tested geometry/unit/layer/camera/export modules;
  Vite produced the offline viewer bundle.
- `dotnet format --verify-no-changes`, the .NET 10 Release build, and 21 desktop tests passed;
  the build reported zero compiler warnings or errors. New coverage verifies required semantic
  resources, WCAG AA token contrast, explicit dark templates and popup resources, accessible names,
  navigation active state, wizard content, visible hardware/engine fallbacks, exact WebView origin
  policy, CORS/CSP alignment, and removal of the global local-operation HTTP timeout.
- A pinned isolated 0.2.1 backend wheel built successfully and contains the migrations, application
  licence, and `LicenseRef-SpatialForge-Source-Visible-1.0` metadata.
- Current advisory checks reported no known vulnerabilities for the Python production closure,
  npm production dependencies, or NuGet direct/transitive dependencies.

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
Windows title-bar composition, 100–200% DPI, or packaged 0.2.1 execution passed. Those remain the
specific Windows UI release gates documented in `docs/product/UI_REFRESH_PLAN.md`.
