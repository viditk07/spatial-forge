# Security Policy

## Supported versions

SpatialForge is pre-release software. Security fixes are applied only to the latest `0.2.x`
development line. Older artifacts should not be considered supported.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private project data, or
crafted image/model files. Use GitHub's **Report a vulnerability** action under the repository's
Security tab. Repository maintainers should enable private vulnerability reporting before making
the repository public.

Include the affected version, Windows version, reproduction steps, impact, and the smallest safe
fixture possible. Do not include real photographs, models, GPS metadata, or full local paths.

You should receive an initial acknowledgement within seven days. Public disclosure should wait
until a fix or mitigation is available and affected users have had reasonable time to update.

## Security boundaries

The desktop application and local API are intended to operate without internet access. The API
must remain bound to `127.0.0.1` and authenticated with a per-launch token. Build and release
systems may access package registries, but normal application operation must not upload data.
