# Release Checklist

- Run backend Ruff, mypy, all tests, and migration upgrade/downgrade tests.
- Run viewer Prettier, ESLint, strict type check, loader tests, and production build.
- Run .NET format verification, Release build, and desktop tests on Windows.
- Build the backend wheel and confirm packaged Alembic revisions.
- Freeze the backend and pass the launch-token loopback health smoke.
- Build the self-contained WPF publish and confirm bundled viewer files.
- Compile and silently install the Inno installer on a clean Windows 11 VM.
- Launch WebView2, import synthetic images, cancel/retry a fake job, and export GLB.
- Confirm normal use makes no external network connection.
- Confirm diagnostic reports contain no image/model/GPS/source-path content.
- Review third-party versions, notices, redistribution terms, and SHA-256 manifest.
- Confirm the packaged notice manifest records Pillow 12.3.0 or newer and remove every installer
  produced before the latest security dependency audit.
- Confirm the checksum manifest contains relative paths only.
- For production distribution, run packaging with `-RequireSigning` and verify a valid timestamped
  Authenticode signature. Label any permitted unsigned beta artifact explicitly.
- Record real COLMAP version/hardware if reconstruction claims are included.
- Update changelog, known limitations, version fields, and project status.
