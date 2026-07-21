# Current Task

## Objective

Present SpatialForge's public 0.2.1 beta accurately in the repository landing documentation.

## Acceptance criteria

- The README identifies SpatialForge as an early evaluation beta rather than a finished product.
- The public 0.2.1 pre-release and unsigned-installer warning are visible.
- Implemented capabilities are separated clearly from real-engine and Windows validation claims.
- Privacy, licence, contribution, installation, and security-reporting context is explicit.
- Linked project status reflects the live public repository and release state.

## Files being modified

`README.md`, `CURRENT_TASK.md`, `PROJECT_STATUS.md`, and `CHANGELOG.md`.

## Validation commands

Markdown link and whitespace checks, repository diff review, and authenticated read-only GitHub API
checks for release, visibility, security configuration, open alerts, and branch protection.

## Risks and blockers

- The 0.2.1 installer is unsigned and complete installed-application validation remains pending.
- Real COLMAP reconstruction and the reported full-resolution 80-photo failure remain unverified.
- Documentation must not imply that mocked engine coverage proves real reconstruction support.

## Status

Complete. Public-facing documentation now distinguishes the available unsigned evaluation beta
from the pending real-engine, representative-capture, signed-release, and Windows runtime gates.
