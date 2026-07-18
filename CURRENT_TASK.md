# Current Task

## Objective

Complete the production-grade SpatialForge desktop visual refresh without changing local processing behavior.

## Acceptance criteria

- Shared semantic tokens and explicit dark templates cover all WPF controls.
- Shell, dashboard, wizard, review, processing, hardware, model, settings, and dialogs are consistent.
- Existing routes, bindings, commands, backend calls, WebView protocol, and project data remain intact.
- Theme, contrast, navigation, wizard, and missing-value regression tests pass.
- WPF builds and the complete repository validation suite passes.
- Windows screenshots, DPI checks, packaged launch, and installer are validated in Windows CI/hardware.

## Files being modified

Desktop resources, views, presentation view models/contracts, UI tests, version metadata, and UI documentation.

## Validation commands

See `AGENTS.md`; exact completed results are recorded in `PROJECT_STATUS.md`.
Latest host validation completed on 2026-07-17 with `.venv/bin/python scripts/validate.py`.

## Risks and blockers

- This Linux host cannot execute WPF/WebView2, capture Windows screenshots, or run Inno Setup.
- Windows DPI, keyboard traversal, packaged launch, and visual screenshot review remain external gates.
- Existing real-engine and redistribution blockers remain unrelated to the visual refresh.

## Status

Host-complete. The design system and all major desktop screens are refreshed, documented, and pass
the aggregate validation suite. Windows runtime, screenshot/DPI, keyboard, WebView2 composition, and
0.2.0 installer review remain external release gates.
