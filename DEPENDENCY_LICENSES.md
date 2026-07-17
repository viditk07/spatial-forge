# Dependency and Licence Inventory

Versions below are the locked or installed versions validated on 2026-07-17. Dependencies are
used unmodified. Permissive licences allow commercial redistribution when their copyright and
licence notices are retained; this inventory is engineering documentation, not legal advice.

## Shipped runtime dependencies

| Dependency | Version | Licence | Source | Use and redistribution |
|---|---:|---|---|---|
| Python | 3.12.3 | PSF-2.0 | python.org | Embedded by PyInstaller; retain PSF notices |
| FastAPI | 0.139.2 | MIT | github.com/fastapi/fastapi | Bundled Python package; retain notice |
| Pydantic | 2.13.4 | MIT | github.com/pydantic/pydantic | Bundled Python package; retain notice |
| Pydantic Settings | 2.14.2 | MIT | github.com/pydantic/pydantic-settings | Bundled Python package; retain notice |
| SQLAlchemy | 2.0.51 | MIT | sqlalchemy.org | Bundled Python package; retain notice |
| Alembic | 1.18.5 | MIT | alembic.sqlalchemy.org | Bundled migrations/runtime; retain notice |
| Uvicorn | 0.51.0 | BSD-3-Clause | uvicorn.org | Loopback server; retain notice |
| HTTPX | 0.28.1 | BSD-3-Clause | github.com/encode/httpx | Bundled health/test client; retain notice |
| psutil | 7.2.2 | BSD-3-Clause | github.com/giampaolo/psutil | Bundled native wheel; retain notice |
| structlog | 25.5.0 | MIT OR Apache-2.0 | structlog.org | Bundled logging package; retain selected notice |
| Typer | 0.27.0 | MIT | github.com/fastapi/typer | Bundled CLI package; retain notice |
| python-multipart | 0.0.32 | Apache-2.0 | github.com/Kludex/python-multipart | Bundled API parser; include licence/NOTICE if present |
| Pillow | 11.3.0 | MIT-CMU | python-pillow.github.io | Bundled image codec package; retain notice |
| OpenCV headless | 4.13.0.92 | Apache-2.0 | github.com/opencv/opencv-python | Bundled native wheel; include licence/NOTICE |
| Trimesh | 4.12.2 | MIT | github.com/mikedh/trimesh | Bundled model operations; retain notice |
| Fast Simplification | 0.1.13 | MIT | github.com/pyvista/fast-simplification | Bundled native wheel; retain notice |
| Three.js | 0.185.1 | MIT | github.com/mrdoob/three.js | Compiled into offline viewer; retain notice |
| .NET runtime/WPF | 10.0.301 SDK line | MIT and Microsoft notices | github.com/dotnet | Self-contained publish; include distribution notices |
| Microsoft.Extensions.DependencyInjection | 10.0.10 | MIT | nuget.org | Bundled .NET assembly; retain notice |
| WebView2 SDK | 1.0.4078.44 | Microsoft software terms | nuget.org | Bundled loader/assemblies; runtime terms apply |

All transitive Python packages are resolved recursively from production extras by the fail-closed
notice collector. npm packages are locked by `apps/viewer/package-lock.json`; NuGet transitive
assets are resolved by `obj/project.assets.json` during the reproducible build. Release CI archives
a machine-readable dependency report and copies corresponding licence files into the installer. A
distributable release is blocked if that inventory contains an unknown, incompatible, or missing
licence.

## Build and test tools (not application runtime)

PyInstaller 6.21.0 is GPL-2.0-or-later with its explicit commercial-distribution exception.
Vite 8.1.5, Vitest 4.1.10, TypeScript 6.0.3, ESLint 10.7.0, Prettier 3.9.5, Ruff 0.15.22,
mypy 1.20.2, pytest 8.4.2, xUnit v3 3.2.2, and the .NET test SDK 18.8.1 are development-only.
Their code is not intentionally shipped except for build-tool bootstrap metadata or source maps,
which release packaging must exclude.

## External engines

COLMAP is invoked as a separate process and is not currently bundled. Its BSD-3-Clause project
licence does not by itself resolve the redistribution terms of every binary dependency. OpenMVS
and Blender are also not bundled; their copyleft and transitive terms require separate review.
No engine binary may enter a release until its exact build, source, modifications, notices,
commercial-use implications, and redistribution obligations are approved.
