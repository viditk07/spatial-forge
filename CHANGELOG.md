# Changelog

All notable changes follow semantic versioning.

## [Unreleased]

### Added

- Explicit source-visible evaluation licence, security policy, contribution policy, community
  conduct guidance, and repository code ownership.
- Public-release regression coverage for an 80-image import/analysis set, unbounded local-operation
  HTTP duration, WebView virtual-host policy, and disabled backend access logging.
- Optional Authenticode signing with fail-closed `-RequireSigning` verification.

### Changed

- Upgraded Pillow to 12.3.0 after the public-release dependency audit and embedded the application
  licence in the backend wheel.
- Pinned GitHub Actions to immutable commit SHAs and Windows packaging to Inno Setup 6.7.1.
- Release checksum manifests now use portable relative paths instead of CI runner paths.

### Fixed

- Local image import and quality analysis are no longer abandoned by a global 30-second HTTP
  timeout; Uvicorn access logging no longer risks filling the desktop's redirected output pipe.
- Three.js model fetches now use a CSP-approved, CORS-capable local virtual-host mapping while
  top-level WebView navigation validates the exact trusted origin.
- Installation guidance no longer describes unsigned beta installers as signed.

## [0.2.0] - 2026-07-18

### Added

- A centralized dark-first WPF design system with semantic color, typography, spacing, radius,
  focus, status, surface, and motion tokens.
- Explicit accessible dark templates for buttons, text fields, dropdown popups, checks, lists,
  progress, menus, tooltips, data grids, and their hover, selected, focused, and disabled states.
- A premium spatial shell with cube/point brand mark, grouped icon navigation, obvious active state,
  local-processing privacy identity, and local service status strip.
- Redesigned dashboard, five-step project wizard, photo inspector, reconstruction timeline, hardware
  capability dashboard, model workstation, settings, empty/error states, and themed dialogs.
- Programmatic WCAG contrast, resource completeness, major-view theming, navigation state, readable
  wizard content, and missing hardware-value tests.
- UI refresh audit, implementation plan, design-system reference, and component guide.

### Changed

- Machine-facing project, stage, preset, engine, status, and missing-value text now has readable
  presentation properties without changing serialized API contracts.
- First-run privacy and destructive confirmations now use the SpatialForge dark visual system.

### Fixed

- Native light dropdown and input surfaces no longer leak into the dark application shell.
- Hardware and engine fields now render explicit fallbacks instead of blank or invisible values.
- The Hardware page now refreshes its local capability data when opened.

## [0.1.0] - 2026-07-17

### Added

- Initial SpatialForge monorepo, architecture, governance, and validation conventions.
- Local project API and CLI with safe per-project filesystem layouts.
- Immutable image import, metadata extraction, thumbnails, quality analysis, duplicate
  grouping, review inclusion, and working-copy GPS removal option.
- Five built-in reconstruction presets and formal durable state-transition rules.
- COLMAP command adapter with argument-array invocation, cancellation primitives, stage
  logs, project-path containment, and output artifact verification.
- Durable background reconstruction with global concurrency, database-enforced per-project
  exclusivity, cancellation, shutdown recovery, checkpoint-aware retry, API/CLI status,
  local JSONL events, and fake-engine end-to-end coverage.
- .NET 10 WPF desktop shell with loopback backend lifecycle, dark privacy-focused design,
  project dashboard/reopen, photo import and review, preset start, processing timeline,
  cancellation confirmation, hardware report, settings, error UX, and MVVM tests.
- Offline Three.js model review with GLB/glTF/OBJ/PLY parsing, orbit controls, layers,
  wireframe, lighting, point selection, scale/measurement, reversible crop preview,
  screenshots, and export presets embedded through locked-down WebView2 virtual hosts.
- Durable model records, scale references, derived mesh cropping, quadric simplification,
  validated GLB/OBJ/PLY export, and traversal-resistant model operations.
- Storage/RAM/CUDA preflight, conservative CPU and sparse-preview fallbacks, restart recovery,
  safe project compaction/deletion, local resource monitoring, and privacy-safe diagnostics.
- Expandable persisted job logs in the desktop processing screen and stable corrective API errors.
- Privacy-safe diagnostic creation with an explicit local logs-folder action.
- Reproducible Python wheel/frozen backend, self-contained Windows publish, Inno Setup installer
  definition, SHA-256 manifest, packaging smoke checks, and Windows packaging CI.
- Fail-closed release licence validation and generated third-party notice bundle.
- Installation, capture, processing, measurement, troubleshooting, packaging, release, licence,
  and known-limitations documentation.
- Native project/export folder selection with generated child filenames and manifest-verified
  deletion for projects outside the default root.
- OpenCV Laplacian/Tenengrad focus scoring, ORB feature estimates, transitive near-duplicate
  groups, EXIF GPS/capture-device persistence, thumbnails, full-screen review, and warning help.
- Persistent hardware history, Intel/AMD display-adapter reporting, NVIDIA utilisation/VRAM,
  executable checks, dashboard disk/thumbnail details, and status-aware project reopening.
- Verified sparse PLY conversion for CPU mode, sparse/dense/mesh model-layer registration,
  primary-layer-preserving cleanup, and point-cloud GLB export through API and CLI.
- Exact Python application/tool pins, transitive production licence resolution, explicit OpenCV
  freezing, and exclusion of unused ImageHash/SciPy and development-only frozen modules.
- Project-scoped model review with isolated local layer hosts, simultaneous sparse/dense/mesh
  compositing, independent visibility controls, and visible-layer aggregate statistics.
- Durable COLMAP camera-pose export, filename-free pose artifacts, validated loopback camera API,
  compact-project preservation, and independently visible Three.js camera frustums.
- Advanced export sidecars for validated point clouds and privacy-safe camera positions, atomic
  partial-output cleanup, persisted total output size, and clearly labelled rough size estimates.
- Verified registered-camera counts in resource snapshots and the Processing screen, kept distinct
  from the number of photographs merely included for reconstruction.

### Fixed

- Windows packaging now restores NuGet packages before release-notice collection, fails immediately
  on native command errors, and prints frozen-backend smoke logs when the health check fails.
