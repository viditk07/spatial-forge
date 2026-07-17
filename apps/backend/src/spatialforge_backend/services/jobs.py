"""Durable reconstruction orchestration and restart-safe background execution."""

from __future__ import annotations

import asyncio
import json
import shutil
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, sessionmaker

from spatialforge_backend.core.config import Settings
from spatialforge_backend.core.errors import AppError, ErrorCode
from spatialforge_backend.core.logging import get_logger
from spatialforge_backend.db.models import (
    ImageAsset,
    JobStatus,
    PipelineStage,
    ProcessingPreset,
    Project,
    ProjectStatus,
    ReconstructionJob,
    StageStatus,
)
from spatialforge_backend.engines.cameras import write_camera_artifact
from spatialforge_backend.engines.colmap import (
    ColmapCommands,
    ColmapWorkspace,
    run_process,
    verify_stage_artifacts,
)

from .job_state import validate_job_transition
from .models import ModelService
from .reliability import ReliabilityService

PIPELINE_STAGES = (
    "prepare_images",
    "feature_extraction",
    "matching",
    "sparse_reconstruction",
    "sparse_export",
    "camera_export",
    "image_undistortion",
    "depth_maps",
    "dense_fusion",
    "mesh_generation",
)
DENSE_STAGES = {"image_undistortion", "depth_maps", "dense_fusion", "mesh_generation"}
ACTIVE_JOB_STATUSES = (JobStatus.QUEUED.value, JobStatus.PROCESSING.value)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _active_job_query(project_id: str) -> Select[tuple[ReconstructionJob]]:
    return select(ReconstructionJob).where(
        ReconstructionJob.project_id == project_id,
        ReconstructionJob.status.in_(ACTIVE_JOB_STATUSES),
    )


class JobService:
    """Create and recover durable job records independently of process execution."""

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings

    def create(self, project_id: str, preset_id: str) -> ReconstructionJob:
        project = self.session.get(Project, project_id)
        preset = self.session.get(ProcessingPreset, preset_id)
        if project is None or preset is None:
            raise AppError(
                ErrorCode.PROJECT_CORRUPTED,
                "Project or preset not found",
                "The selected project or processing preset is unavailable.",
                "Open the project again and select an available preset.",
            )
        if self.session.scalar(_active_job_query(project_id)) is not None:
            raise AppError(
                ErrorCode.PROCESS_RESOURCE_LIMIT,
                "A reconstruction is already active",
                "Only one reconstruction can run for a project at a time.",
                "Cancel or wait for the active reconstruction before starting another.",
            )
        if self.settings is not None and self.settings.resource_preflight_enabled:
            ReliabilityService(self.session).validate_preflight(project, preset)
        included = self.session.scalar(
            select(func.count(ImageAsset.id)).where(
                ImageAsset.project_id == project_id, ImageAsset.included.is_(True)
            )
        )
        if (included or 0) < 3:
            raise AppError(
                ErrorCode.INSUFFICIENT_IMAGES,
                "Too few included photographs",
                "At least three photographs are required to attempt camera registration.",
                "Import or include more overlapping photographs.",
            )
        job = ReconstructionJob(project_id=project_id, preset_id=preset_id)
        self.session.add(job)
        self.session.flush()
        dense_enabled = bool(json.loads(preset.configuration_json).get("dense_enabled", True))
        for sequence, name in enumerate(PIPELINE_STAGES, start=1):
            skipped = not dense_enabled and name in DENSE_STAGES
            job.stages.append(
                PipelineStage(
                    stage_name=name,
                    sequence_number=sequence,
                    status=(StageStatus.SKIPPED.value if skipped else StageStatus.PENDING.value),
                    progress_percent=100 if skipped else 0,
                )
            )
        project.status = ProjectStatus.QUEUED.value
        project.selected_preset_id = preset_id
        self.session.commit()
        return job

    def get(self, job_id: str) -> ReconstructionJob | None:
        return self.session.get(ReconstructionJob, job_id)

    def latest_for_project(self, project_id: str) -> ReconstructionJob | None:
        return self.session.scalar(
            select(ReconstructionJob)
            .where(ReconstructionJob.project_id == project_id)
            .order_by(ReconstructionJob.started_at.desc(), ReconstructionJob.id.desc())
        )

    def retry(self, job_id: str) -> ReconstructionJob:
        previous = self.get(job_id)
        if previous is None:
            raise self._missing_job_error()
        if previous.status not in {
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
            JobStatus.INTERRUPTED.value,
        }:
            raise AppError(
                ErrorCode.PROCESS_RESOURCE_LIMIT,
                "Reconstruction cannot be retried",
                "Only failed, cancelled, or interrupted reconstructions can be retried.",
                "Wait for the active reconstruction or start a new job after completion.",
            )
        completed_names = {
            stage.stage_name
            for stage in previous.stages
            if stage.status == StageStatus.COMPLETED.value
        }
        retried = self.create(previous.project_id, previous.preset_id)
        retried.retry_of_job_id = previous.id
        for stage in retried.stages:
            if stage.stage_name in completed_names:
                stage.status = StageStatus.COMPLETED.value
                stage.progress_percent = 100
        self.session.commit()
        return retried

    def recover_interrupted(self) -> list[str]:
        recovered: list[str] = []
        jobs = self.session.scalars(
            select(ReconstructionJob).where(ReconstructionJob.status == JobStatus.PROCESSING.value)
        )
        for job in jobs:
            validate_job_transition(JobStatus.PROCESSING, JobStatus.INTERRUPTED)
            job.status = JobStatus.INTERRUPTED.value
            job.error_code = ErrorCode.PROCESS_INTERRUPTED.value
            job.error_message = "SpatialForge stopped while reconstruction was running."
            job.process_id = None
            for stage in job.stages:
                if stage.status == StageStatus.RUNNING.value:
                    stage.status = StageStatus.FAILED.value
                    stage.error_message = "Processing was interrupted by application restart."
            project = self.session.get(Project, job.project_id)
            if project:
                project.status = ProjectStatus.FAILED.value
            recovered.append(job.id)
        self.session.commit()
        return recovered

    @staticmethod
    def _missing_job_error() -> AppError:
        return AppError(
            ErrorCode.PROJECT_CORRUPTED,
            "Reconstruction not found",
            "The reconstruction record no longer exists.",
            "Return to the project and create a new reconstruction.",
        )


class JobExecutor:
    """Execute a pipeline while checkpointing every durable transition."""

    def __init__(self, factory: sessionmaker[Session], settings: Settings) -> None:
        self.factory = factory
        self.settings = settings
        self.logger = get_logger("reconstruction")

    async def execute(self, job_id: str) -> None:
        try:
            await self._execute(job_id)
        except asyncio.CancelledError:
            raise
        except AppError as error:
            self._mark_failed(job_id, error)
        except Exception as error:
            self._mark_failed(
                job_id,
                AppError(
                    ErrorCode.DATABASE_ERROR,
                    "Unexpected reconstruction failure",
                    "SpatialForge could not complete the current stage.",
                    "Open the technical log and retry the failed reconstruction.",
                    technical_details=f"{type(error).__name__}: {error}",
                    retry_safe=True,
                ),
            )

    async def _execute(self, job_id: str) -> None:
        with self.factory() as session:
            job = session.get(ReconstructionJob, job_id)
            if job is None:
                return
            validate_job_transition(JobStatus(job.status), JobStatus.PROCESSING)
            job.status = JobStatus.PROCESSING.value
            job.started_at = job.started_at or _now()
            project = session.get(Project, job.project_id)
            if project:
                project.status = ProjectStatus.PROCESSING.value
            session.commit()
            self.logger.info("job_started", project_id=job.project_id, job_id=job.id)

        for stage_name in PIPELINE_STAGES:
            with self.factory() as session:
                job = session.get(ReconstructionJob, job_id)
                if job is None:
                    return
                stage = next(item for item in job.stages if item.stage_name == stage_name)
                if stage.status == StageStatus.SKIPPED.value:
                    continue
                if stage.status == StageStatus.COMPLETED.value:
                    valid = await asyncio.to_thread(
                        self._checkpoint_valid, job, stage_name, session
                    )
                    if valid:
                        continue
                    stage.status = StageStatus.PENDING.value
                    stage.progress_percent = 0
                stage.status = StageStatus.RUNNING.value
                stage.started_at = _now()
                stage.progress_percent = 0
                job.current_stage = stage_name
                session.commit()
                self.logger.info(
                    "stage_started",
                    project_id=job.project_id,
                    job_id=job.id,
                    stage=stage_name,
                )
            await self._execute_stage(job_id, stage_name)
            self._complete_stage(job_id, stage_name)

        with self.factory() as session:
            job = session.get(ReconstructionJob, job_id)
            if job is None:
                return
            validate_job_transition(JobStatus(job.status), JobStatus.COMPLETED)
            job.status = JobStatus.COMPLETED.value
            job.progress_percent = 100
            job.completed_at = _now()
            job.process_id = None
            project = session.get(Project, job.project_id)
            if project:
                project.status = ProjectStatus.COMPLETED.value
                ModelService(session).register_job_output(job, project)
            session.commit()
            self.logger.info("job_completed", project_id=job.project_id, job_id=job.id)

    def _checkpoint_valid(self, job: ReconstructionJob, stage_name: str, session: Session) -> bool:
        project = session.get(Project, job.project_id)
        if project is None:
            return False
        if stage_name == "prepare_images":
            return self.available_image_count(self.session_images(session, project.id)) >= 3
        workspace = ColmapWorkspace(self._resolve_executable(), Path(project.root_path))
        try:
            verify_stage_artifacts(stage_name, workspace)
        except AppError:
            return False
        return True

    async def _execute_stage(self, job_id: str, stage_name: str) -> None:
        with self.factory() as session:
            job = session.get(ReconstructionJob, job_id)
            if job is None:
                return
            project = session.get(Project, job.project_id)
            preset = session.get(ProcessingPreset, job.preset_id)
            if project is None or preset is None:
                raise AppError(
                    ErrorCode.PROJECT_CORRUPTED,
                    "Project data is missing",
                    "The reconstruction references missing project configuration.",
                    "Restore the project metadata or create a new reconstruction.",
                )
            workspace = ColmapWorkspace(self._resolve_executable(), Path(project.root_path))
            stage = next(item for item in job.stages if item.stage_name == stage_name)
            log_path = workspace.project_root / "logs" / f"job_{job.id}_{stage_name}.log"
            if stage_name == "prepare_images":
                images = self.session_images(session, project.id)
                available = await asyncio.to_thread(self.available_image_count, images)
                if available < 3:
                    raise AppError(
                        ErrorCode.INSUFFICIENT_IMAGES,
                        "Working photographs are missing",
                        "Fewer than three included working photographs are available.",
                        "Reimport missing photographs or restore project files.",
                    )
                return
            arguments = self._arguments(stage_name, workspace, preset)
            if stage_name == "camera_export":
                workspace.camera_text.mkdir(parents=True, exist_ok=True)
            stage.command = json.dumps(
                [part.replace(str(workspace.project_root), "${PROJECT}") for part in arguments]
            )
            stage.log_path = str(log_path)
            session.commit()

        result = await run_process(
            arguments,
            log_path,
            self.settings.stage_timeout_seconds,
            on_started=lambda process_id: self._record_process(job_id, process_id),
        )
        if result.exit_code != 0:
            raise self._process_error(stage_name, result.exit_code, log_path)
        if stage_name == "camera_export":
            await asyncio.to_thread(
                write_camera_artifact,
                workspace.camera_text / "images.txt",
                workspace.camera_artifact,
            )
        verify_stage_artifacts(stage_name, workspace)

    @staticmethod
    def session_images(session: Session, project_id: str) -> list[ImageAsset]:
        return list(
            session.scalars(
                select(ImageAsset).where(
                    ImageAsset.project_id == project_id, ImageAsset.included.is_(True)
                )
            )
        )

    @staticmethod
    def available_image_count(images: list[ImageAsset]) -> int:
        return sum(Path(item.working_path).is_file() for item in images)

    def _arguments(
        self, stage: str, workspace: ColmapWorkspace, preset: ProcessingPreset
    ) -> list[str]:
        configuration = json.loads(preset.configuration_json)
        commands = ColmapCommands(workspace)
        builders = {
            "feature_extraction": lambda: commands.feature_extraction(
                int(configuration.get("max_image_size", 2400)),
                int(configuration.get("max_features", 8192)),
            ),
            "matching": lambda: commands.matching(str(configuration.get("matcher", "exhaustive"))),
            "sparse_reconstruction": commands.mapper,
            "sparse_export": lambda: commands.model_converter(
                workspace.sparse / "0", workspace.sparse / "sparse.ply", "PLY"
            ),
            "camera_export": lambda: commands.model_converter(
                workspace.sparse / "0", workspace.camera_text, "TXT"
            ),
            "image_undistortion": lambda: commands.image_undistorter(workspace.sparse / "0"),
            "depth_maps": commands.patch_match_stereo,
            "dense_fusion": commands.stereo_fusion,
            "mesh_generation": commands.poisson_mesher,
        }
        return builders[stage]()

    def _resolve_executable(self) -> Path:
        configured = self.settings.colmap_executable
        if (configured.is_absolute() or configured.parent != Path(".")) and configured.is_file():
            return configured
        located = shutil.which(str(configured))
        if located:
            return Path(located)
        raise AppError(
            ErrorCode.DEPENDENCY_MISSING,
            "COLMAP is not installed",
            "SpatialForge could not find the configured COLMAP executable.",
            "Install a compatible COLMAP build or select its executable in settings.",
        )

    def _record_process(self, job_id: str, process_id: int) -> None:
        with self.factory() as session:
            job = session.get(ReconstructionJob, job_id)
            if job:
                job.process_id = process_id
                session.commit()

    def _complete_stage(self, job_id: str, stage_name: str) -> None:
        with self.factory() as session:
            job = session.get(ReconstructionJob, job_id)
            if job is None:
                return
            stage = next(item for item in job.stages if item.stage_name == stage_name)
            stage.status = StageStatus.COMPLETED.value
            stage.progress_percent = 100
            stage.completed_at = _now()
            job.process_id = None
            completed = sum(
                item.status in {StageStatus.COMPLETED.value, StageStatus.SKIPPED.value}
                for item in job.stages
            )
            job.progress_percent = completed / len(job.stages) * 100
            session.commit()
            self.logger.info(
                "stage_completed",
                project_id=job.project_id,
                job_id=job.id,
                stage=stage_name,
                progress_percent=job.progress_percent,
            )

    def mark_cancelled(self, job_id: str) -> None:
        with self.factory() as session:
            job = session.get(ReconstructionJob, job_id)
            if job is None or job.status in {
                JobStatus.COMPLETED.value,
                JobStatus.FAILED.value,
                JobStatus.CANCELLED.value,
            }:
                return
            job.status = JobStatus.CANCELLED.value
            job.cancelled_at = _now()
            job.process_id = None
            for stage in job.stages:
                if stage.status == StageStatus.RUNNING.value:
                    stage.status = StageStatus.CANCELLED.value
                    stage.error_message = "Cancelled by the user."
            project = session.get(Project, job.project_id)
            if project:
                project.status = ProjectStatus.CANCELLED.value
            session.commit()
            self.logger.info(
                "job_cancelled",
                project_id=job.project_id,
                job_id=job.id,
                stage=job.current_stage,
            )

    def mark_interrupted(self, job_id: str) -> None:
        """Record application shutdown as a recoverable interruption."""
        with self.factory() as session:
            job = session.get(ReconstructionJob, job_id)
            if job is None or job.status not in ACTIVE_JOB_STATUSES:
                return
            job.status = JobStatus.INTERRUPTED.value
            job.error_code = ErrorCode.PROCESS_INTERRUPTED.value
            job.error_message = "SpatialForge stopped while reconstruction was running."
            job.process_id = None
            for stage in job.stages:
                if stage.status == StageStatus.RUNNING.value:
                    stage.status = StageStatus.FAILED.value
                    stage.error_message = "Processing was interrupted by application shutdown."
            project = session.get(Project, job.project_id)
            if project:
                project.status = ProjectStatus.FAILED.value
            session.commit()
            self.logger.warning(
                "job_interrupted",
                project_id=job.project_id,
                job_id=job.id,
                stage=job.current_stage,
                error_code=ErrorCode.PROCESS_INTERRUPTED.value,
            )

    def _mark_failed(self, job_id: str, error: AppError) -> None:
        with self.factory() as session:
            job = session.get(ReconstructionJob, job_id)
            if job is None:
                return
            job.status = JobStatus.FAILED.value
            job.error_code = error.code.value
            job.error_message = error.explanation
            job.technical_error = error.technical_details
            job.process_id = None
            for stage in job.stages:
                if stage.status == StageStatus.RUNNING.value:
                    stage.status = StageStatus.FAILED.value
                    stage.error_message = error.explanation
            project = session.get(Project, job.project_id)
            if project:
                project.status = ProjectStatus.FAILED.value
            session.commit()
            self.logger.error(
                "job_failed",
                project_id=job.project_id,
                job_id=job.id,
                stage=job.current_stage,
                error_code=error.code.value,
            )

    @staticmethod
    def _process_error(stage: str, exit_code: int, log_path: Path) -> AppError:
        codes = {
            "feature_extraction": ErrorCode.FEATURE_EXTRACTION_FAILED,
            "matching": ErrorCode.MATCHING_FAILED,
            "sparse_reconstruction": ErrorCode.TOO_FEW_REGISTERED_IMAGES,
            "sparse_export": ErrorCode.EMPTY_POINT_CLOUD,
            "camera_export": ErrorCode.TOO_FEW_REGISTERED_IMAGES,
            "image_undistortion": ErrorCode.DENSE_RECONSTRUCTION_FAILED,
            "depth_maps": ErrorCode.DENSE_RECONSTRUCTION_FAILED,
            "dense_fusion": ErrorCode.DENSE_RECONSTRUCTION_FAILED,
            "mesh_generation": ErrorCode.MESH_GENERATION_FAILED,
        }
        return AppError(
            codes[stage],
            "Reconstruction stage failed",
            f"The {stage.replace('_', ' ')} stage did not complete successfully.",
            "Open the stage log, correct the reported issue, and retry.",
            technical_details=f"Process exit code: {exit_code}",
            log_file=str(log_path),
            retry_safe=True,
        )


class JobManager:
    """Own background tasks and enforce process-wide concurrency."""

    def __init__(self, executor: JobExecutor, max_concurrent_jobs: int) -> None:
        self.executor = executor
        self.semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.shutting_down = False

    def start(self, job_id: str) -> None:
        if job_id in self.tasks and not self.tasks[job_id].done():
            return
        task = asyncio.create_task(self._guarded(job_id), name=f"spatialforge-job-{job_id}")
        self.tasks[job_id] = task
        task.add_done_callback(lambda _: self.tasks.pop(job_id, None))

    async def _guarded(self, job_id: str) -> None:
        try:
            async with self.semaphore:
                await self.executor.execute(job_id)
        except asyncio.CancelledError:
            if self.shutting_down:
                self.executor.mark_interrupted(job_id)
            else:
                self.executor.mark_cancelled(job_id)
            raise

    async def cancel(self, job_id: str) -> bool:
        task = self.tasks.get(job_id)
        if task is None or task.done():
            return False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True

    async def shutdown(self) -> None:
        self.shutting_down = True
        tasks: Sequence[asyncio.Task[None]] = tuple(self.tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
