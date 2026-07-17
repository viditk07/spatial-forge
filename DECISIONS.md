# Architecture Decisions

## ADR-001: WPF on the latest stable compatible .NET

Status: accepted. WPF has mature Windows tooling, predictable desktop lifecycle behavior,
WebView2 support, and simpler packaging than WinUI 3 for this MVP. .NET 10 is the active
LTS release and SDK 10.0.301 cross-build validation passed. Final executable validation
still runs on Windows because Microsoft notes non-Windows targeting output differences.

## ADR-002: Loopback FastAPI backend

Status: accepted. A versioned local HTTP API cleanly separates the native UI and Python
pipeline and can serve a future explicitly enabled phone-transfer workflow. It binds to
`127.0.0.1`, uses a launch token, and does not expose a LAN listener.

## ADR-003: CLI adapters for reconstruction engines

Status: accepted. COLMAP is invoked through typed command builders and subprocess argument
arrays. This isolates licensing, installation variants, cancellation, and fake-engine tests.

## ADR-004: WebView2 and bundled Three.js viewer

Status: accepted. Three.js provides GLB, point cloud, selection, and measurement support.
All viewer assets are bundled; CDN references are prohibited.

## ADR-005: SQLite plus Alembic

Status: accepted. SQLite is local, reliable, and requires no service. UUIDs are canonical
text, foreign keys are enabled per connection, and all released changes use migrations.

## ADR-006: Inno Setup release installer

Status: provisional. Inno Setup offers straightforward per-user offline installation and
can bundle the WPF publish output and isolated backend. Final acceptance requires Windows
CI and licence review.

## ADR-007: Conservative CPU fallback

Status: accepted. CUDA-absent systems receive sparse reconstruction and only engine-backed
dense capabilities proven to work. The UI must not imply that COLMAP dense reconstruction
is CPU-compatible when the installed build does not support it.

## ADR-008: Trimesh for local derived-model operations

Status: accepted. Trimesh 4.12 with its permissive licence provides deterministic local
mesh loading, format conversion, crop, validation, and GLB export without a heavyweight
GPU runtime. Fast Simplification is isolated behind the model service for quadric reduction.
The original reconstruction output is never overwritten; every crop or simplify action
creates a derived model record.
