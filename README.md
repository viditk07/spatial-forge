# SpatialForge

SpatialForge is a local-only Windows 11 desktop photogrammetry application. It imports
smartphone photographs, evaluates capture quality, orchestrates COLMAP-compatible
reconstruction, previews and scales results, and exports GLB models without uploading
user data.

The repository is under active MVP development. See [PROJECT_STATUS.md](PROJECT_STATUS.md)
for verified capabilities and limitations, and [ARCHITECTURE.md](ARCHITECTURE.md) for
the system design.

## Workspace layout

- `apps/backend` - Python FastAPI backend, CLI, SQLite models, migrations, image analysis,
  reconstruction orchestration, export services, and tests.
- `apps/desktop` - .NET/WPF desktop shell, MVVM core, WebView2 viewer host, and desktop tests.
- `apps/viewer` - TypeScript/Three.js embedded model viewer and viewer tests.
- `docs` - architecture, development, testing, deployment, product, and user-guide material.
- `packaging/windows` and `scripts/package-windows.ps1` - Windows packaging definition and release
  packaging script.
- `packages`, `engines`, `samples`, `tests`, and `tools` - shared contracts, engine placeholders,
  fixtures, end-to-end test space, and supporting tools.

## Repository quick start

Python 3.12+, Node.js 24+, and .NET SDK 10 are required for the full
workspace. External engines are optional in development because adapters have fake-tool
tests. Production reconstruction requires a separately verified COLMAP installation.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e 'apps/backend[dev,vision,packaging]'
cd apps/viewer && npm ci && cd ../..
.dotnet/dotnet restore apps/desktop/SpatialForge.sln
.venv/bin/python scripts/validate.py
```

The validation script runs backend formatting, linting, type checking, backend tests, viewer
formatting/lint/type checks/tests/build, and desktop formatting/build/tests.

## Local-only privacy model

SpatialForge is designed around local processing:

- The backend binds only to `127.0.0.1`.
- No telemetry, user accounts, cloud storage, or automatic uploads are part of the MVP.
- Imported originals are preserved unchanged; working copies and derived artifacts live inside the
  user project directory.
- Logs and diagnostic reports are local files intended for manual user sharing only.

## Packaging status

Windows packaging is performed by `scripts/package-windows.ps1`; see
`docs/deployment/windows-packaging.md` for the release gate and current external-engine policy.
The Linux development host can build and smoke-test host-native backend artifacts and cross-publish
the self-contained `win-x64` WPF output, but final installer execution, WPF/WebView2 runtime smoke,
and representative real-engine reconstruction must run on Windows 11 with approved engine binaries.

## Development rules

- Do not commit local virtual environments, toolchains, generated project data, packaged binaries,
  logs, databases, or proprietary engine binaries.
- Do not bundle COLMAP, OpenMVS, Blender, or other engine binaries until exact redistribution terms
  and transitive licences are verified.
- Keep `PROJECT_STATUS.md`, `CURRENT_TASK.md`, `DECISIONS.md`, and `CHANGELOG.md` aligned with
  implementation and validation evidence.
- Do not claim reconstruction, packaging, or Windows runtime support without an executed validation
  command recorded in `PROJECT_STATUS.md`.

SpatialForge has no cloud service and the API listens only on `127.0.0.1`.
