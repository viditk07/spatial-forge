"""Local preflight, cleanup, storage, and privacy-safe diagnostic services."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from spatialforge_backend.core.errors import AppError, ErrorCode
from spatialforge_backend.db.models import (
    Export,
    ImageAsset,
    JobStatus,
    ProcessingPreset,
    Project,
    ReconstructionJob,
    ReconstructionModel,
)
from spatialforge_backend.engines.cameras import read_camera_artifact

from .hardware import capture_hardware, dependency_report, nvidia_usage
from .paths import ensure_within


def _directory_size(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        except OSError:
            continue
    return total


class ReliabilityService:
    """Protect reconstruction resources and create privacy-safe local diagnostics."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def storage(self, project: Project) -> dict[str, int]:
        root = Path(project.root_path)
        usage = shutil.disk_usage(root)
        input_bytes = (
            self.session.scalar(
                select(func.sum(ImageAsset.file_size_bytes)).where(
                    ImageAsset.project_id == project.id,
                    ImageAsset.included.is_(True),
                )
            )
            or 0
        )
        preset = (
            self.session.get(ProcessingPreset, project.selected_preset_id)
            if project.selected_preset_id
            else None
        )
        multiplier = 4 if preset and preset.preset_type == "cpu_compatible" else 18
        estimated_required = max(int(input_bytes * multiplier), 512 * 1024**2)
        return {
            "disk_total_bytes": usage.total,
            "disk_free_bytes": usage.free,
            "project_size_bytes": _directory_size(root),
            "estimated_processing_bytes": estimated_required,
            "reserve_bytes": 2 * 1024**3,
        }

    def resources(self, project: Project) -> dict[str, float | int | None]:
        memory = psutil.virtual_memory()
        usage = shutil.disk_usage(Path(project.root_path))
        job = self.session.scalar(
            select(ReconstructionJob)
            .where(
                ReconstructionJob.project_id == project.id,
                ReconstructionJob.status.in_((JobStatus.QUEUED.value, JobStatus.PROCESSING.value)),
            )
            .order_by(ReconstructionJob.started_at.desc())
        )
        process_cpu: float | None = None
        process_memory_mb: float | None = None
        gpu_percent, gpu_memory_used_mb = nvidia_usage()
        registered_camera_count: int | None = None
        camera_artifact = Path(project.root_path) / "previews" / "cameras.json"
        if camera_artifact.is_file():
            try:
                registered_camera_count = len(read_camera_artifact(camera_artifact))
            except AppError:
                registered_camera_count = None
        if job and job.process_id:
            try:
                process = psutil.Process(job.process_id)
                process_cpu = process.cpu_percent(interval=None)
                process_memory_mb = process.memory_info().rss / 1024**2
            except psutil.Error:
                pass
        return {
            "system_cpu_percent": psutil.cpu_percent(interval=None),
            "memory_used_mb": (memory.total - memory.available) // 1024**2,
            "memory_available_mb": memory.available // 1024**2,
            "disk_free_bytes": usage.free,
            "process_cpu_percent": process_cpu,
            "process_memory_mb": process_memory_mb,
            "process_id": job.process_id if job else None,
            "gpu_percent": gpu_percent,
            "gpu_memory_used_mb": gpu_memory_used_mb,
            "registered_camera_count": registered_camera_count,
        }

    def validate_preflight(self, project: Project, preset: ProcessingPreset) -> None:
        project.selected_preset_id = preset.id
        hardware = capture_hardware()
        if preset.requires_cuda and not hardware.cuda_available:
            raise AppError(
                ErrorCode.CUDA_UNAVAILABLE,
                "CUDA acceleration is unavailable",
                "The selected preset requires a supported NVIDIA CUDA GPU.",
                "Choose Fast Preview or CPU-Compatible, or install a supported NVIDIA "
                "GPU and driver.",
                technical_details=f"Detected GPU={hardware.gpu_model or 'none'}",
                retry_safe=True,
            )
        storage = self.storage(project)
        required = storage["estimated_processing_bytes"] + storage["reserve_bytes"]
        if storage["disk_free_bytes"] < required:
            raise AppError(
                ErrorCode.INSUFFICIENT_STORAGE,
                "Not enough free storage",
                "The selected reconstruction could exhaust the project drive.",
                "Free storage or choose a lower-quality preset before retrying.",
                technical_details=f"Required={required}; free={storage['disk_free_bytes']}",
                retry_safe=True,
            )
        memory = psutil.virtual_memory()
        minimum_bytes = int(preset.minimum_ram_gb * 1024**3)
        included_bytes = (
            self.session.scalar(
                select(func.sum(ImageAsset.file_size_bytes)).where(
                    ImageAsset.project_id == project.id,
                    ImageAsset.included.is_(True),
                )
            )
            or 0
        )
        working_memory = max(512 * 1024**2, int(included_bytes * 2.5))
        if memory.total < minimum_bytes or memory.available < working_memory:
            raise AppError(
                ErrorCode.INSUFFICIENT_RAM,
                "Not enough memory is available",
                "The selected preset is unsafe for the current memory conditions.",
                "Close other applications or choose Fast Preview or CPU-Compatible.",
                technical_details=(
                    f"Preset minimum={preset.minimum_ram_gb:g} GiB; "
                    f"available={memory.available / 1024**3:.1f} GiB; "
                    f"estimated working={working_memory / 1024**3:.1f} GiB"
                ),
                retry_safe=True,
            )

    def compact(self, project: Project) -> dict[str, int]:
        active = self.session.scalar(
            select(ReconstructionJob.id).where(
                ReconstructionJob.project_id == project.id,
                ReconstructionJob.status.in_((JobStatus.QUEUED.value, JobStatus.PROCESSING.value)),
            )
        )
        if active:
            raise AppError(
                ErrorCode.PROCESS_RESOURCE_LIMIT,
                "Project is currently processing",
                "Temporary files cannot be removed while reconstruction is active.",
                "Cancel or wait for reconstruction to finish, then compact the project.",
            )
        root = ensure_within(Path(project.root_path), Path(project.root_path))
        before = _directory_size(root)
        primary_paths = {
            ensure_within(Path(model.file_path), root)
            for model in self.session.scalars(
                select(ReconstructionModel).where(
                    ReconstructionModel.project_id == project.id,
                    ReconstructionModel.is_primary.is_(True),
                )
            )
        }
        camera_artifact = root / "previews" / "cameras.json"
        if camera_artifact.is_file():
            primary_paths.add(ensure_within(camera_artifact, root))
        for directory_name in (
            "working_images",
            "thumbnails",
            "sparse",
            "dense",
            "previews",
            "logs",
            "temp",
        ):
            self._clear_directory(root / directory_name, primary_paths)
        self._clear_directory(root / "mesh", primary_paths)
        for model in list(
            self.session.scalars(
                select(ReconstructionModel).where(
                    ReconstructionModel.project_id == project.id,
                    ReconstructionModel.is_primary.is_(False),
                )
            )
        ):
            self.session.delete(model)
        self.session.commit()
        after = _directory_size(root)
        return {"bytes_before": before, "bytes_after": after, "bytes_reclaimed": before - after}

    def diagnostic_report(self, project: Project) -> Path:
        root = ensure_within(Path(project.root_path), Path(project.root_path))
        jobs = list(
            self.session.scalars(
                select(ReconstructionJob)
                .where(ReconstructionJob.project_id == project.id)
                .order_by(ReconstructionJob.started_at.desc())
            )
        )
        models = (
            self.session.scalar(
                select(func.count(ReconstructionModel.id)).where(
                    ReconstructionModel.project_id == project.id
                )
            )
            or 0
        )
        exports = (
            self.session.scalar(
                select(func.count(Export.id)).where(Export.project_id == project.id)
            )
            or 0
        )
        images = (
            self.session.scalar(
                select(func.count(ImageAsset.id)).where(ImageAsset.project_id == project.id)
            )
            or 0
        )
        report: dict[str, Any] = {
            "schema_version": 1,
            "generated_at": datetime.now(UTC).isoformat(),
            "privacy": {
                "contains_photographs": False,
                "contains_models": False,
                "contains_gps": False,
                "contains_source_paths": False,
            },
            "project": {
                "id": project.id,
                "project_type": project.project_type,
                "status": project.status,
                "image_count": images,
                "model_count": models,
                "export_count": exports,
            },
            "hardware": capture_hardware().to_dict(),
            "dependencies": dependency_report(),
            "storage": self.storage(project),
            "jobs": [
                {
                    "id": job.id,
                    "status": job.status,
                    "current_stage": job.current_stage,
                    "progress_percent": job.progress_percent,
                    "error_code": job.error_code,
                    "stage_statuses": {stage.stage_name: stage.status for stage in job.stages},
                }
                for job in jobs
            ],
        }
        output = root / "logs" / f"diagnostic_{datetime.now(UTC):%Y%m%d_%H%M%S}.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return output

    @staticmethod
    def _clear_directory(directory: Path, preserved: set[Path]) -> None:
        if not directory.exists():
            directory.mkdir(parents=True)
            return
        for child in directory.iterdir():
            resolved = child.resolve()
            if resolved in preserved:
                continue
            if child.is_symlink() or child.is_file():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                nested = {path for path in preserved if resolved in path.parents}
                if nested:
                    ReliabilityService._clear_directory(child, nested)
                else:
                    shutil.rmtree(child)
