# Changelog

All notable changes follow semantic versioning.

## [Unreleased]

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
