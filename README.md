# SpatialForge

SpatialForge is a privacy-first Windows 11 application for turning smartphone photographs into
local 3D reconstruction projects. It preserves imported originals, analyses image quality,
orchestrates a user-supplied COLMAP installation, and provides an offline 3D workspace for model
review, scaling, measurement, cropping, and export.

SpatialForge is currently an **early evaluation beta**, not a finished photogrammetry product.
The deterministic mock-engine workflow is well tested, but representative real-COLMAP,
full-resolution capture, clean-machine, and GPU validation are still release gates.

## Current release

[SpatialForge 0.2.1 Security Remediation](https://github.com/viditk07/spatial-forge/releases/tag/v0.2.1)
is the current public Windows pre-release. The Windows packaging workflow built the installer and
passed the frozen backend's authenticated loopback health check.

The installer is unsigned, so Windows may display a SmartScreen warning. It is provided only for
personal evaluation under [LICENSE.txt](LICENSE.txt). Do not use SpatialForge for production,
surveying, structural, safety-critical, or legal work. See the [installation guide](docs/user-guide/installation.md)
before running it.

## What the beta includes

- Local project creation with durable SQLite state and per-project file layouts.
- Immutable photo import, metadata extraction, thumbnails, blur/exposure/resolution/feature
  analysis, and exact or perceptual duplicate grouping.
- Hardware and dependency detection with Fast Preview, room, exterior, high-quality, and
  CPU-compatible processing presets.
- A durable, cancellable, retryable COLMAP command pipeline with stage checkpoints and structured
  local logs.
- An offline WPF and Three.js workspace for sparse, dense, mesh, texture, and camera layers.
- Approximate scale calibration, measurement, crop preview, mesh simplification, and validated
  GLB/OBJ/PLY export services.
- A self-contained Windows package containing the WPF shell, local Python backend, viewer assets,
  dependency notices, and no bundled reconstruction engine.

## Important limitations

- COLMAP, OpenMVS, and Blender are **not bundled**. Reconstruction is unavailable until a compatible
  COLMAP executable is installed separately; real-engine compatibility has not yet been certified.
- Dense reconstruction generally depends on an appropriate NVIDIA CUDA setup. CPU mode provides a
  conservative sparse path and does not promise dense or textured output.
- Dedicated production texture generation is not complete, so textured output is engine- and
  input-dependent.
- The automated 80-image regression uses synthetic fixtures. The previously reported crash with
  approximately 80 full-resolution phone photographs still needs reproduction on the affected
  Windows hardware.
- The packaged installer has not yet passed the complete clean-machine install, WPF/WebView2,
  high-DPI, representative capture, real-engine, and uninstall matrix.
- Geometry and measurements are approximate and are not survey-grade.

The complete list is maintained in [known limitations](docs/product/known-limitations.md), while
[PROJECT_STATUS.md](PROJECT_STATUS.md) records validation evidence and current release gates.

## Local-only privacy model

Normal application operation does not require a cloud service:

- The backend binds only to `127.0.0.1` and requires a per-launch authentication token.
- No user accounts, telemetry, crash uploads, cloud storage, or automatic update checks are enabled.
- Imported originals are preserved byte-for-byte; working copies and derived artifacts live in the
  selected local project directory.
- GPS is not shown in normal diagnostics and can be removed from working copies during import.
- Logs and diagnostic reports stay local unless the user manually shares them.

## Licence, security, and contributions

SpatialForge is **source-visible evaluation software, not an open-source project**.
[LICENSE.txt](LICENSE.txt) permits personal evaluation of unmodified official binaries but does not
grant rights to modify or redistribute the source or binaries. External code contributions are not
currently accepted; see [CONTRIBUTING.md](CONTRIBUTING.md).

Report vulnerabilities through GitHub's private vulnerability reporting flow and follow
[SECURITY.md](SECURITY.md). Never include photographs, models, GPS data, credentials, diagnostic
archives, or full local paths in a public report.

## Developer quick start

The full workspace requires Python 3.12+, Node.js 24+, and the .NET 10 SDK. On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "apps/backend[dev,vision,packaging]"
npm --prefix apps/viewer ci
dotnet restore apps/desktop/SpatialForge.sln
.\.venv\Scripts\python.exe scripts/validate.py
```

Build the Windows package with:

```powershell
pwsh ./scripts/package-windows.ps1
```

Fake engine fixtures are the deterministic development and CI path. A successful mocked pipeline
must not be presented as evidence that a particular COLMAP binary, camera set, GPU, or Windows
machine has completed a real reconstruction.

## Repository layout

- `apps/backend` — FastAPI backend, CLI, SQLite data layer, image analysis, reconstruction
  orchestration, model operations, packaging entry point, and tests.
- `apps/desktop` — .NET/WPF shell, MVVM core, WebView2 host, and desktop tests.
- `apps/viewer` — strict TypeScript/Three.js embedded viewer and Vitest suite.
- `docs` — architecture, product, development, testing, deployment, and user documentation.
- `packaging/windows` and `scripts/package-windows.ps1` — Inno Setup definition and reproducible
  Windows packaging workflow.
- `packages`, `engines`, `samples`, `tests`, and `tools` — contracts, adapter boundaries, legal
  fixtures, end-to-end tests, and development support.

Start with [ARCHITECTURE.md](ARCHITECTURE.md), [REPO_MAP.md](REPO_MAP.md), and
[AGENTS.md](AGENTS.md) before changing the implementation.
