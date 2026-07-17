"""Automation-friendly local command-line interface."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy import select
from sqlalchemy.orm import Session

from spatialforge_backend.core.config import Settings, get_settings
from spatialforge_backend.core.errors import AppError, ErrorCode
from spatialforge_backend.core.logging import configure_logging
from spatialforge_backend.db.models import (
    JobStatus,
    ProjectType,
    ReconstructionJob,
    ReconstructionModel,
)
from spatialforge_backend.db.session import (
    create_database_engine,
    initialise_database,
    session_factory,
)
from spatialforge_backend.services.images import ImageService
from spatialforge_backend.services.jobs import JobExecutor, JobService
from spatialforge_backend.services.models import ModelService
from spatialforge_backend.services.presets import seed_system_presets
from spatialforge_backend.services.projects import ProjectService

app = typer.Typer(help="SpatialForge local photogrammetry workflow.", no_args_is_help=True)
project_app = typer.Typer(help="Create and inspect local projects.")
images_app = typer.Typer(help="Import and analyse project photographs.")
process_app = typer.Typer(help="Start and inspect durable reconstruction jobs.")
export_app = typer.Typer(help="Export a verified local reconstruction model.")
app.add_typer(project_app, name="project")
app.add_typer(images_app, name="images")
app.add_typer(process_app, name="process")
app.add_typer(export_app, name="export")


def _emit(value: object) -> None:
    typer.echo(json.dumps(value, indent=2, default=str))


def _run[T](operation: Callable[[Session, Settings], T]) -> None:
    settings = get_settings()
    configure_logging(settings.data_dir / "logs" / "backend.jsonl", settings.log_level)
    engine = create_database_engine(settings)
    initialise_database(engine)
    factory = session_factory(engine)
    try:
        with factory() as session:
            seed_system_presets(session)
            result = operation(session, settings)
            _emit(result)
    except AppError as error:
        _emit(
            {
                "error": {
                    "code": error.code.value,
                    "title": error.title,
                    "explanation": error.explanation,
                    "recommended_action": error.recommended_action,
                }
            }
        )
        raise typer.Exit(2) from error
    finally:
        engine.dispose()


def _job_payload(job: ReconstructionJob) -> dict[str, object]:
    return {
        "id": job.id,
        "project_id": job.project_id,
        "status": job.status,
        "current_stage": job.current_stage,
        "progress_percent": job.progress_percent,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "retry_of_job_id": job.retry_of_job_id,
        "stages": [
            {
                "name": stage.stage_name,
                "status": stage.status,
                "progress_percent": stage.progress_percent,
            }
            for stage in job.stages
        ],
    }


def _execute_cli_job(
    session: Session, settings: Settings, job: ReconstructionJob
) -> dict[str, object]:
    factory = session_factory(session.get_bind())
    asyncio.run(JobExecutor(factory, settings).execute(job.id))
    session.expire_all()
    refreshed = JobService(session).get(job.id)
    if refreshed is None:
        raise RuntimeError("Job disappeared during execution")
    if refreshed.status == JobStatus.FAILED.value:
        code = ErrorCode(refreshed.error_code or ErrorCode.DATABASE_ERROR.value)
        raise AppError(
            code,
            "Reconstruction failed",
            refreshed.error_message or "The reconstruction did not complete.",
            "Open the stage log, correct the issue, and retry.",
            technical_details=refreshed.technical_error or "",
            retry_safe=True,
        )
    return _job_payload(refreshed)


@project_app.command("create")
def project_create(
    name: Annotated[str, typer.Option(prompt=True, help="Human-readable project name")],
    project_type: Annotated[
        ProjectType, typer.Option(help="Capture scope")
    ] = ProjectType.SINGLE_ROOM,
    notes: Annotated[str | None, typer.Option(help="Optional local notes")] = None,
    project_directory: Annotated[
        Path | None, typer.Option(help="Existing parent folder for the project")
    ] = None,
) -> None:
    """Create a project and its protected filesystem layout."""

    def operation(session: Session, settings: Settings) -> dict[str, str]:
        project = ProjectService(session, settings).create(
            name, project_type, notes, parent_directory=project_directory
        )
        return {"id": project.id, "name": project.name, "status": project.status}

    _run(operation)


@project_app.command("list")
def project_list() -> None:
    """List projects without exposing their full filesystem paths."""

    def operation(session: Session, settings: Settings) -> list[dict[str, str]]:
        return [
            {"id": item.id, "name": item.name, "status": item.status}
            for item in ProjectService(session, settings).list()
        ]

    _run(operation)


@images_app.command("import")
def images_import(
    project_id: Annotated[str, typer.Option(help="Target project UUID")],
    paths: Annotated[list[Path], typer.Argument(help="Photographs to import")],
    remove_gps: Annotated[
        bool, typer.Option(help="Remove metadata from derived working copies")
    ] = False,
) -> None:
    """Copy photographs into immutable local project storage."""

    def operation(session: Session, settings: Settings) -> list[dict[str, object]]:
        project = ProjectService(session, settings).get(project_id)
        if project is None:
            raise typer.BadParameter("Project not found", param_hint="--project-id")
        assets = ImageService(session).import_files(project, paths, remove_gps=remove_gps)
        return [
            {"id": item.id, "filename": item.original_filename, "included": item.included}
            for item in assets
        ]

    _run(operation)


@images_app.command("analyse")
def images_analyse(
    project_id: Annotated[str, typer.Option(help="Target project UUID")],
) -> None:
    """Calculate local capture-quality warnings."""

    def operation(session: Session, settings: Settings) -> list[dict[str, object]]:
        project = ProjectService(session, settings).get(project_id)
        if project is None:
            raise typer.BadParameter("Project not found", param_hint="--project-id")
        assets = ImageService(session).analyse(project)
        return [
            {
                "id": item.id,
                "filename": item.original_filename,
                "quality_status": item.quality_status,
                "included": item.included,
            }
            for item in assets
        ]

    _run(operation)


@process_app.command("start")
def process_start(
    project_id: Annotated[str, typer.Option(help="Target project UUID")],
    preset_id: Annotated[str, typer.Option(help="Processing preset UUID")],
) -> None:
    """Create and run a durable reconstruction in the foreground."""

    def operation(session: Session, settings: Settings) -> dict[str, object]:
        job = JobService(session, settings).create(project_id, preset_id)
        return _execute_cli_job(session, settings, job)

    _run(operation)


@process_app.command("status")
def process_status(job_id: Annotated[str, typer.Option(help="Reconstruction job UUID")]) -> None:
    """Print the last persisted reconstruction status."""

    def operation(session: Session, _: Settings) -> dict[str, object]:
        job = JobService(session).get(job_id)
        if job is None:
            raise typer.BadParameter("Reconstruction not found", param_hint="--job-id")
        return _job_payload(job)

    _run(operation)


@process_app.command("retry")
def process_retry(job_id: Annotated[str, typer.Option(help="Failed job UUID")]) -> None:
    """Retry from verified completed checkpoints."""

    def operation(session: Session, settings: Settings) -> dict[str, object]:
        job = JobService(session, settings).retry(job_id)
        return _execute_cli_job(session, settings, job)

    _run(operation)


def _export_model(
    export_format: str,
    project_id: str,
    output_directory: Path | None,
    target_face_count: int | None,
    texture_resolution: int | None,
) -> None:
    def operation(session: Session, _: Settings) -> dict[str, object]:
        model = session.scalar(
            select(ReconstructionModel)
            .where(
                ReconstructionModel.project_id == project_id,
                ReconstructionModel.is_primary.is_(True),
            )
            .order_by(ReconstructionModel.created_at.desc())
        )
        if model is None:
            raise typer.BadParameter("No primary model is available", param_hint="--project-id")
        exported = ModelService(session).export(
            model.id,
            export_format,
            texture_resolution,
            target_face_count,
            output_directory,
        )
        return {
            "id": exported.id,
            "format": exported.export_format,
            "status": exported.status,
            "output_path": exported.output_path,
            "file_size_bytes": exported.file_size_bytes,
        }

    _run(operation)


@export_app.command("glb")
def export_glb(
    project_id: Annotated[str, typer.Option(help="Project UUID")],
    output_directory: Annotated[
        Path | None, typer.Option(help="Existing destination folder")
    ] = None,
    target_face_count: Annotated[
        int | None, typer.Option(min=4, help="Optional polygon target")
    ] = None,
    texture_resolution: Annotated[
        int | None, typer.Option(min=256, max=16384, help="Texture target metadata")
    ] = None,
) -> None:
    """Export the project's primary model as GLB."""
    _export_model("glb", project_id, output_directory, target_face_count, texture_resolution)


@export_app.command("obj")
def export_obj(
    project_id: Annotated[str, typer.Option(help="Project UUID")],
    output_directory: Annotated[
        Path | None, typer.Option(help="Existing destination folder")
    ] = None,
) -> None:
    """Export the project's primary model as OBJ."""
    _export_model("obj", project_id, output_directory, None, None)


@export_app.command("ply")
def export_ply(
    project_id: Annotated[str, typer.Option(help="Project UUID")],
    output_directory: Annotated[
        Path | None, typer.Option(help="Existing destination folder")
    ] = None,
) -> None:
    """Export the project's primary model as PLY."""
    _export_model("ply", project_id, output_directory, None, None)


if __name__ == "__main__":
    app()
