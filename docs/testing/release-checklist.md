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
- Record real COLMAP version/hardware if reconstruction claims are included.
- Update changelog, known limitations, version fields, and project status.
