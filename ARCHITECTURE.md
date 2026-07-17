# SpatialForge Architecture

SpatialForge is a monorepo with three runtime components:

1. A WPF desktop shell owns navigation, native file dialogs, lifecycle, and accessibility.
2. A packaged Python/FastAPI backend owns persistence, validation, jobs, engines, and models.
3. A bundled Three.js viewer runs inside WebView2 and communicates through explicit contracts.

The desktop launches the backend on a random loopback port with a per-launch token. The
backend binds only to `127.0.0.1`; no normal workflow requires internet access. SQLite is
the durable source of truth. Long reconstruction processes run outside the API event loop,
and stage state is checkpointed before and after execution.

Project originals are immutable. Working images, databases, engine outputs, previews, and
exports occupy distinct directories. Engine adapters construct argument arrays, classify
failures, stream structured logs, and verify expected artifacts in addition to exit codes.

See `DECISIONS.md` for rationale and `REPO_MAP.md` for code ownership.

