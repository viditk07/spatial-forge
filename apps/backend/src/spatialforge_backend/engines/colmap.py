"""Safe COLMAP command construction, execution, and artifact validation."""

from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import psutil

from spatialforge_backend.core.errors import AppError, ErrorCode

from .cameras import read_camera_artifact


@dataclass(frozen=True, slots=True)
class ColmapWorkspace:
    executable: Path
    project_root: Path

    @property
    def database(self) -> Path:
        return self.project_root / "database" / "colmap.db"

    @property
    def images(self) -> Path:
        return self.project_root / "working_images"

    @property
    def sparse(self) -> Path:
        return self.project_root / "sparse"

    @property
    def dense(self) -> Path:
        return self.project_root / "dense"

    @property
    def mesh(self) -> Path:
        return self.project_root / "mesh"

    @property
    def previews(self) -> Path:
        return self.project_root / "previews"

    @property
    def camera_text(self) -> Path:
        return self.previews / "colmap_text"

    @property
    def camera_artifact(self) -> Path:
        return self.previews / "cameras.json"


class ColmapCommands:
    """Build commands exclusively as argument arrays."""

    def __init__(self, workspace: ColmapWorkspace) -> None:
        self.workspace = workspace

    def feature_extraction(self, max_image_size: int, max_features: int) -> list[str]:
        args = [
            *self._base("feature_extractor"),
            "--database_path",
            str(self.workspace.database),
            "--image_path",
            str(self.workspace.images),
            "--ImageReader.single_camera_per_folder",
            "1",
            "--SiftExtraction.max_num_features",
            str(max_features),
        ]
        if max_image_size > 0:
            args += ["--SiftExtraction.max_image_size", str(max_image_size)]
        return args

    def matching(self, matcher: str = "exhaustive") -> list[str]:
        if matcher not in {"exhaustive", "sequential"}:
            raise ValueError("Matcher must be exhaustive or sequential")
        return [*self._base(f"{matcher}_matcher"), "--database_path", str(self.workspace.database)]

    def mapper(self) -> list[str]:
        return [
            *self._base("mapper"),
            "--database_path",
            str(self.workspace.database),
            "--image_path",
            str(self.workspace.images),
            "--output_path",
            str(self.workspace.sparse),
        ]

    def image_undistorter(self, input_model: Path) -> list[str]:
        self._ensure_project_path(input_model)
        return [
            *self._base("image_undistorter"),
            "--image_path",
            str(self.workspace.images),
            "--input_path",
            str(input_model),
            "--output_path",
            str(self.workspace.dense),
            "--output_type",
            "COLMAP",
        ]

    def patch_match_stereo(self) -> list[str]:
        return [
            *self._base("patch_match_stereo"),
            "--workspace_path",
            str(self.workspace.dense),
            "--workspace_format",
            "COLMAP",
        ]

    def stereo_fusion(self) -> list[str]:
        return [
            *self._base("stereo_fusion"),
            "--workspace_path",
            str(self.workspace.dense),
            "--workspace_format",
            "COLMAP",
            "--input_type",
            "geometric",
            "--output_path",
            str(self.workspace.dense / "fused.ply"),
        ]

    def poisson_mesher(self) -> list[str]:
        return [
            *self._base("poisson_mesher"),
            "--input_path",
            str(self.workspace.dense / "fused.ply"),
            "--output_path",
            str(self.workspace.mesh / "meshed-poisson.ply"),
        ]

    def model_converter(self, input_model: Path, output_path: Path, output_type: str) -> list[str]:
        self._ensure_project_path(input_model)
        self._ensure_project_path(output_path)
        if output_type not in {"TXT", "PLY", "NVM", "Bundler", "VRML"}:
            raise ValueError("Unsupported COLMAP model output type")
        return [
            *self._base("model_converter"),
            "--input_path",
            str(input_model),
            "--output_path",
            str(output_path),
            "--output_type",
            output_type,
        ]

    def _base(self, command: str) -> list[str]:
        return [str(self.workspace.executable), command]

    def _ensure_project_path(self, path: Path) -> None:
        root = self.workspace.project_root.resolve()
        resolved = path.resolve()
        if root not in resolved.parents and resolved != root:
            raise AppError(
                ErrorCode.PATH_INVALID,
                "Unsafe engine path",
                "A reconstruction path escaped the active project.",
                "Open the project again and retry the stage.",
                technical_details="COLMAP path containment validation failed.",
            )


def _has_ply_header(path: Path) -> bool:
    with path.open("rb") as artifact:
        return artifact.read(3) == b"ply"


def verify_stage_artifacts(stage: str, workspace: ColmapWorkspace) -> None:
    """Reject false-positive zero exits that did not create meaningful output."""
    expected_files: dict[str, tuple[Path, ...]] = {
        "feature_extraction": (workspace.database,),
        "matching": (workspace.database,),
        "sparse_export": (workspace.sparse / "sparse.ply",),
        "dense_fusion": (workspace.dense / "fused.ply",),
        "mesh_generation": (workspace.mesh / "meshed-poisson.ply",),
    }
    if stage in expected_files:
        if any(not path.is_file() or path.stat().st_size == 0 for path in expected_files[stage]):
            codes = {
                "feature_extraction": ErrorCode.FEATURE_EXTRACTION_FAILED,
                "matching": ErrorCode.MATCHING_FAILED,
                "sparse_export": ErrorCode.EMPTY_POINT_CLOUD,
                "dense_fusion": ErrorCode.EMPTY_POINT_CLOUD,
                "mesh_generation": ErrorCode.MESH_GENERATION_FAILED,
            }
            raise AppError(
                codes[stage],
                "Expected reconstruction output is missing",
                "The engine exited without creating a usable stage output.",
                "Open the stage log, correct the capture or engine issue, and retry.",
                retry_safe=True,
            )
        if stage in {"sparse_export", "dense_fusion", "mesh_generation"} and any(
            not _has_ply_header(path) for path in expected_files[stage]
        ):
            raise AppError(
                ErrorCode.EMPTY_POINT_CLOUD
                if stage != "mesh_generation"
                else ErrorCode.MESH_GENERATION_FAILED,
                "Reconstruction output is invalid",
                "The engine output is not a readable PLY artifact.",
                "Open the stage log, verify the engine build, and retry the failed stage.",
                retry_safe=True,
            )
    elif stage == "image_undistortion":
        if not any((workspace.dense / "images").glob("*")):
            raise AppError(
                ErrorCode.DENSE_RECONSTRUCTION_FAILED,
                "Undistorted images are missing",
                "COLMAP did not prepare images for dense reconstruction.",
                "Review the stage log and retry image undistortion.",
                retry_safe=True,
            )
    elif stage == "depth_maps":
        if not any((workspace.dense / "stereo" / "depth_maps").glob("*")):
            raise AppError(
                ErrorCode.DENSE_RECONSTRUCTION_FAILED,
                "Depth maps are missing",
                "COLMAP did not create usable stereo depth maps.",
                "Confirm CUDA support or choose a sparse/CPU-compatible preset.",
                retry_safe=True,
            )
    elif stage == "sparse_reconstruction":
        models = list(workspace.sparse.glob("*/cameras.*"))
        if not models:
            raise AppError(
                ErrorCode.TOO_FEW_REGISTERED_IMAGES,
                "No sparse model was created",
                "COLMAP did not produce a registered camera model.",
                "Review capture overlap and excluded images, then retry mapping.",
                retry_safe=True,
            )
    elif stage == "camera_export":
        read_camera_artifact(workspace.camera_artifact)


@dataclass(frozen=True, slots=True)
class ProcessResult:
    exit_code: int
    output: str


async def run_process(
    arguments: list[str],
    log_path: Path,
    timeout_seconds: float,
    on_started: Callable[[int], None] | None = None,
) -> ProcessResult:
    """Run a tool without a shell and capture a bounded stage log."""
    if not arguments:
        raise ValueError("Process argument list cannot be empty")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    creationflags = 0
    start_new_session = os.name != "nt"
    if os.name == "nt":
        creationflags = 0x00000200  # CREATE_NEW_PROCESS_GROUP
    process = await asyncio.create_subprocess_exec(
        *arguments,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        creationflags=creationflags,
        start_new_session=start_new_session,
    )
    if on_started is not None:
        on_started(process.pid)
    try:
        output_bytes, _ = await asyncio.wait_for(process.communicate(), timeout_seconds)
    except (TimeoutError, asyncio.CancelledError):
        terminate_process_tree(process.pid)
        await process.wait()
        raise
    output = output_bytes.decode("utf-8", errors="replace")
    await asyncio.to_thread(log_path.write_text, output, encoding="utf-8")
    return ProcessResult(process.returncode or 0, output)


def terminate_process_tree(process_id: int) -> None:
    """Terminate descendants before their parent during cancellation."""
    try:
        parent = psutil.Process(process_id)
    except psutil.Error:
        return
    children = parent.children(recursive=True)
    for process in children:
        try:
            process.terminate()
        except psutil.Error:
            pass
    psutil.wait_procs(children, timeout=3)
    try:
        if os.name == "nt":
            parent.terminate()
        else:
            os.killpg(process_id, signal.SIGTERM)
    except (OSError, psutil.Error):
        pass
