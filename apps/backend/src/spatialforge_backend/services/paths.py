"""Project path validation and layout creation."""

from __future__ import annotations

from pathlib import Path

from spatialforge_backend.core.errors import AppError, ErrorCode

PROJECT_DIRECTORIES = (
    "originals",
    "working_images",
    "thumbnails",
    "database",
    "sparse",
    "dense",
    "mesh",
    "textures",
    "previews",
    "exports",
    "logs",
    "temp",
)


def ensure_within(path: Path, root: Path) -> Path:
    """Resolve a path and reject traversal or escape from the configured root."""
    resolved_root = root.expanduser().resolve()
    resolved_path = path.expanduser().resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise AppError(
            ErrorCode.PATH_INVALID,
            "Unsafe path",
            "The selected path is outside the configured project directory.",
            "Choose a folder inside the SpatialForge projects directory.",
            technical_details="Path failed containment validation.",
        )
    return resolved_path


def create_project_layout(root: Path) -> None:
    """Create a project atomically enough to detect and clean partial creation."""
    if root.exists():
        raise AppError(
            ErrorCode.PATH_INVALID,
            "Project folder already exists",
            "SpatialForge will not overwrite an existing project folder.",
            "Choose another project name or import the existing project.",
        )
    root.mkdir(parents=True)
    for directory in PROJECT_DIRECTORIES:
        (root / directory).mkdir()
