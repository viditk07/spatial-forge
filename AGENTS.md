# SpatialForge Contributor Guide

SpatialForge is a privacy-first Windows application that turns manually transferred
photographs into 3D models. Normal operation is strictly local: never add uploads,
telemetry, crash reporting, remote authentication, or update checks by default.

## Engineering rules

- Keep desktop, backend, viewer, contracts, and external-engine adapters separated.
- Validate every boundary input. Use typed interfaces and explicit state transitions.
- Preserve imported originals byte-for-byte; derived data belongs outside `originals/`.
- Invoke tools with argument arrays and `shell=False`. Validate paths before I/O.
- Bind the API to `127.0.0.1` only. Never log GPS or full user paths by default.
- Python uses Ruff, mypy, pytest, Pydantic, and complete public API type hints.
- C# enables nullable references, MVVM, DI, async I/O, and xUnit tests.
- TypeScript uses strict mode, ESLint, Prettier, and Vitest without `any`.
- Add tests and documentation with each behavior change. Never weaken a test to pass.

## Definition of done

Code alone is incomplete. A slice is done only when failure cases are handled, its
tests pass, relevant static checks and builds pass, outputs are inspected, and status
documentation records the exact validation performed. Never claim unrun validation.

## Commands

```bash
# backend setup/run
python -m venv .venv
.venv/Scripts/python -m pip install -e "apps/backend[dev,vision,packaging]"  # Windows
.venv/bin/python -m pip install -e "apps/backend[dev,vision,packaging]"     # Linux
python -m spatialforge_backend

# backend validation
python -m ruff format --check apps/backend
python -m ruff check apps/backend
python -m mypy apps/backend/src
python -m pytest apps/backend/tests tests/e2e

# viewer
npm --prefix apps/viewer ci
npm --prefix apps/viewer run format:check
npm --prefix apps/viewer run lint
npm --prefix apps/viewer run typecheck
npm --prefix apps/viewer test
npm --prefix apps/viewer run build

# desktop (Windows or a host with the .NET SDK)
dotnet format apps/desktop/SpatialForge.sln --verify-no-changes
dotnet build apps/desktop/SpatialForge.sln -c Release
dotnet test apps/desktop/SpatialForge.sln -c Release

# aggregate and packaging
python scripts/validate.py
pwsh ./scripts/package-windows.ps1
```

## Autonomous continuation

Inspect the current state, implement the highest-priority incomplete vertical slice,
validate it, update `CURRENT_TASK.md` and `PROJECT_STATUS.md`, then continue. Preserve
unrelated user changes. External binaries may be mocked, but real-engine support must
not be claimed until exercised. Proprietary or licence-unverified binaries are never
committed or packaged.
