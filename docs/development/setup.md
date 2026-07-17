# Developer Setup

Install Python 3.12, Node 24 or newer, .NET SDK 10, and platform build tools. Create `.venv`,
install `apps/backend[dev,vision]`, run `npm ci` in `apps/viewer`, restore the desktop
solution, then run `python scripts/validate.py`.

The backend binds only to `127.0.0.1`. Set `SPATIALFORGE_DATA_DIR`,
`SPATIALFORGE_PROJECTS_DIR`, and a random `SPATIALFORGE_LAUNCH_TOKEN` for manual runs.
Fake engine fixtures are the mandatory deterministic integration path. Real COLMAP smoke
tests are optional and must report the exact binary version and hardware.
