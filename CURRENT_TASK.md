# Current Task

## Objective

Harden SpatialForge for public source visibility and remediate the pre-publication audit findings.

## Acceptance criteria

- Production dependencies have no known advisories in current pip, npm, and NuGet scans.
- Application and contribution rights are explicit before source visibility changes.
- WebView model loading permits only validated local virtual hosts and passes regression checks.
- CI actions and Windows installer tooling are pinned to immutable/reproducible versions.
- Public security, contribution, conduct, and ownership guidance exists.
- Personal email addresses are absent from the rewritten Git history.
- Full backend, viewer, desktop, build, and disclosure scans pass.

## Files being modified

Backend dependency and import reliability files, WebView hosting, CI workflows, packaging,
governance documents, tests, and release-status documentation.

## Validation commands

See `AGENTS.md`; exact completed results are recorded in `PROJECT_STATUS.md`.

## Risks and blockers

- This Linux host cannot execute WPF/WebView2, Authenticode, or Inno Setup.
- GitHub security settings and the required force-with-lease push cannot be changed without the
  repository owner's authenticated GitHub session.
- The reported full-resolution 80-photo failure needs confirmation on the affected Windows PC.

## Status

Complete locally. Implementation, validation, history sanitisation, and the post-rewrite disclosure
scan pass. The rewritten branch must be pushed with the documented force-with-lease command before
repository visibility changes. Windows runtime and signed production-installer validation remain
external binary-release gates, not blockers for making the source repository visible.
