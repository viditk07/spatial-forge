# Current Task

## Objective

Complete Phase 5 release validation for the local-only Windows package.

## Acceptance criteria

- Windows CI creates the frozen backend, self-contained WPF publish, hashes, and installer.
- The installer succeeds on a clean Windows 11 machine and uninstalls cleanly.
- WPF launches, enforces the first-run privacy statement, starts only an authenticated
  loopback backend, and renders the offline WebView2 viewer.
- A representative real COLMAP fixture produces and verifies sparse output; dense and texture
  capability is reported honestly for the tested hardware/engine build.
- Third-party binary redistribution terms are approved before any engine is bundled.

## Files being modified

Packaging scripts, CI workflows, release/licence documentation, and Windows smoke tests.

## Validation commands

See `AGENTS.md`; exact completed results are recorded in `PROJECT_STATUS.md`.
Latest host validation completed on 2026-07-17 with `.venv/bin/python scripts/validate.py`.

## Risks and blockers

- The current Linux host cannot execute WPF/WebView2 or compile/run the Inno installer.
- COLMAP is not installed, and no redistribution-approved Windows engine binary is available.
- Texture production depends on an external compatible engine and is not guaranteed by COLMAP
  alone in the current package.

## Status

In progress. All host-available Phase 4 gates passed on 2026-07-17. Fresh backend wheel,
host-native frozen backend, authenticated local health smoke, and self-contained `win-x64`
publish artifacts were produced. Windows installer/runtime validation and representative
real-engine reconstruction remain the release gates.
