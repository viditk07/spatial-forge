"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from spatialforge_backend import __version__
from spatialforge_backend.core.config import Settings, get_settings
from spatialforge_backend.core.errors import AppError
from spatialforge_backend.core.logging import configure_logging, get_logger
from spatialforge_backend.db.models import JobStatus, ReconstructionJob
from spatialforge_backend.db.session import (
    create_database_engine,
    initialise_database,
    session_factory,
)
from spatialforge_backend.engines.cameras import read_camera_artifact
from spatialforge_backend.services.hardware import (
    capture_hardware,
    dependency_report,
    persist_hardware,
)
from spatialforge_backend.services.images import ImageService
from spatialforge_backend.services.jobs import JobExecutor, JobManager, JobService
from spatialforge_backend.services.models import ModelService
from spatialforge_backend.services.paths import ensure_within
from spatialforge_backend.services.presets import list_presets, seed_system_presets
from spatialforge_backend.services.projects import ProjectService
from spatialforge_backend.services.reliability import ReliabilityService

from .schemas import (
    CameraPoseResponse,
    CleanupResponse,
    CropRequest,
    DiagnosticResponse,
    ExportCreate,
    ExportResponse,
    HealthResponse,
    ImageImportRequest,
    ImageResponse,
    ImageUpdate,
    JobCreate,
    JobLogEntry,
    JobResponse,
    ModelResponse,
    PresetResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ResourceResponse,
    ScaleRequest,
    ScaleResponse,
    SimplifyRequest,
    StorageResponse,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an isolated app instance for production or tests."""
    resolved = settings or get_settings()
    configure_logging(resolved.data_dir / "logs" / "backend.jsonl", resolved.log_level)
    logger = get_logger("backend")
    engine = create_database_engine(resolved)
    initialise_database(engine)
    factory = session_factory(engine)
    with factory() as startup_session:
        seed_system_presets(startup_session)
        persist_hardware(startup_session, capture_hardware())
    executor = JobExecutor(factory, resolved)
    manager = JobManager(executor, resolved.max_concurrent_jobs)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        with factory() as startup_session:
            JobService(startup_session).recover_interrupted()
            queued = list(
                startup_session.scalars(
                    select(ReconstructionJob.id).where(
                        ReconstructionJob.status == JobStatus.QUEUED.value
                    )
                )
            )
        application.state.job_manager = manager
        logger.info(
            "backend_started",
            host=resolved.host,
            queued_jobs=len(queued),
            local_only=True,
        )
        for job_id in queued:
            manager.start(job_id)
        yield
        await manager.shutdown()
        logger.info("backend_stopped")

    app = FastAPI(title="SpatialForge Local API", version=__version__, lifespan=lifespan)
    app.state.settings = resolved
    app.state.engine = engine
    app.state.session_factory = factory

    @app.middleware("http")
    async def require_launch_token(request: Request, call_next: object) -> object:
        if (
            resolved.launch_token
            and request.headers.get("X-SpatialForge-Token") != resolved.launch_token
        ):
            return JSONResponse(status_code=401, content={"detail": "Invalid launch token"})
        return await call_next(request)  # type: ignore[operator,no-any-return]

    def get_session() -> Generator[Session]:
        with factory() as session:
            yield session

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": error.code.value,
                    "title": error.title,
                    "explanation": error.explanation,
                    "recommended_action": error.recommended_action,
                    "technical_details": error.technical_details,
                    "log_file": error.log_file,
                    "retry_safe": error.retry_safe,
                }
            },
        )

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__, local_only=True)

    @app.get("/api/v1/system/hardware")
    def hardware() -> dict[str, str | int | bool | None]:
        return capture_hardware().to_dict()

    @app.get("/api/v1/system/dependencies")
    def dependencies() -> list[dict[str, str | bool | None]]:
        return dependency_report()

    @app.get("/api/v1/system/storage", response_model=StorageResponse)
    def storage(
        project_id: str = Query(min_length=1), session: Session = Depends(get_session)
    ) -> object:
        project = ProjectService(session, resolved).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return ReliabilityService(session).storage(project)

    @app.get("/api/v1/system/resources", response_model=ResourceResponse)
    def resources(
        project_id: str = Query(min_length=1), session: Session = Depends(get_session)
    ) -> object:
        project = ProjectService(session, resolved).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return ReliabilityService(session).resources(project)

    @app.get("/api/v1/presets", response_model=list[PresetResponse])
    def presets(session: Session = Depends(get_session)) -> object:
        return list_presets(session)

    @app.post("/api/v1/projects", response_model=ProjectResponse, status_code=201)
    def create_project(payload: ProjectCreate, session: Session = Depends(get_session)) -> object:
        return ProjectService(session, resolved).create(
            payload.name,
            payload.project_type,
            payload.notes,
            parent_directory=(
                Path(payload.project_directory) if payload.project_directory else None
            ),
        )

    @app.get("/api/v1/projects", response_model=list[ProjectResponse])
    def list_projects(session: Session = Depends(get_session)) -> object:
        return ProjectService(session, resolved).list()

    @app.get("/api/v1/projects/{project_id}", response_model=ProjectResponse)
    def get_project(project_id: str, session: Session = Depends(get_session)) -> object:
        project = ProjectService(session, resolved).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    @app.patch("/api/v1/projects/{project_id}", response_model=ProjectResponse)
    def update_project(
        project_id: str, payload: ProjectUpdate, session: Session = Depends(get_session)
    ) -> object:
        service = ProjectService(session, resolved)
        project = service.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return service.update(
            project, name=payload.name, notes=payload.notes, archived=payload.archived
        )

    @app.post("/api/v1/projects/{project_id}/open", response_model=ProjectResponse)
    def open_project(project_id: str, session: Session = Depends(get_session)) -> object:
        service = ProjectService(session, resolved)
        project = service.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return service.mark_opened(project)

    @app.delete("/api/v1/projects/{project_id}", status_code=204)
    def delete_project(
        project_id: str,
        confirmation: str = Query(min_length=1, max_length=120),
        session: Session = Depends(get_session),
    ) -> None:
        service = ProjectService(session, resolved)
        project = service.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        service.delete(project, confirmation)

    @app.post("/api/v1/projects/{project_id}/compact", response_model=CleanupResponse)
    def compact_project(project_id: str, session: Session = Depends(get_session)) -> object:
        project = ProjectService(session, resolved).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return ReliabilityService(session).compact(project)

    @app.post("/api/v1/projects/{project_id}/diagnostics", response_model=DiagnosticResponse)
    def diagnostic_report(project_id: str, session: Session = Depends(get_session)) -> object:
        project = ProjectService(session, resolved).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        output = ReliabilityService(session).diagnostic_report(project)
        return {"output_path": str(output), "contains_user_content": False}

    @app.post(
        "/api/v1/projects/{project_id}/images/import",
        response_model=list[ImageResponse],
        status_code=201,
    )
    def import_images(
        project_id: str,
        payload: ImageImportRequest,
        session: Session = Depends(get_session),
    ) -> object:
        project = ProjectService(session, resolved).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return ImageService(session).import_files(
            project,
            [Path(path) for path in payload.paths],
            remove_gps=payload.remove_gps_from_working_copies,
        )

    @app.get("/api/v1/projects/{project_id}/images", response_model=list[ImageResponse])
    def list_images(project_id: str, session: Session = Depends(get_session)) -> object:
        if ProjectService(session, resolved).get(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return ImageService(session).list_images(project_id)

    @app.post("/api/v1/projects/{project_id}/images/analyse", response_model=list[ImageResponse])
    def analyse_images(project_id: str, session: Session = Depends(get_session)) -> object:
        project = ProjectService(session, resolved).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return ImageService(session).analyse(project)

    @app.patch("/api/v1/images/{image_id}", response_model=ImageResponse)
    def update_image(
        image_id: str, payload: ImageUpdate, session: Session = Depends(get_session)
    ) -> object:
        image = ImageService(session).set_included(image_id, payload.included)
        if image is None:
            raise HTTPException(status_code=404, detail="Image not found")
        return image

    @app.post("/api/v1/projects/{project_id}/jobs", response_model=JobResponse, status_code=201)
    async def create_job(
        project_id: str, payload: JobCreate, session: Session = Depends(get_session)
    ) -> object:
        job = JobService(session, resolved).create(project_id, payload.preset_id)
        manager.start(job.id)
        return job

    @app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
    def get_job(job_id: str, session: Session = Depends(get_session)) -> object:
        job = JobService(session).get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Reconstruction not found")
        return job

    @app.get("/api/v1/projects/{project_id}/jobs/latest", response_model=JobResponse)
    def latest_project_job(project_id: str, session: Session = Depends(get_session)) -> object:
        if ProjectService(session, resolved).get(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        job = JobService(session).latest_for_project(project_id)
        if job is None:
            raise HTTPException(status_code=404, detail="No reconstruction found")
        return job

    @app.post("/api/v1/jobs/{job_id}/cancel", response_model=JobResponse)
    async def cancel_job(job_id: str, session: Session = Depends(get_session)) -> object:
        job = JobService(session).get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Reconstruction not found")
        cancelled = await manager.cancel(job_id)
        if not cancelled and job.status == JobStatus.QUEUED.value:
            executor.mark_cancelled(job_id)
        session.expire_all()
        refreshed = JobService(session).get(job_id)
        return refreshed

    @app.post("/api/v1/jobs/{job_id}/retry", response_model=JobResponse, status_code=201)
    async def retry_job(job_id: str, session: Session = Depends(get_session)) -> object:
        retried = JobService(session, resolved).retry(job_id)
        manager.start(retried.id)
        return retried

    @app.get("/api/v1/jobs/{job_id}/logs", response_model=list[JobLogEntry])
    def job_logs(job_id: str, session: Session = Depends(get_session)) -> object:
        job = JobService(session).get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Reconstruction not found")
        project = ProjectService(session, resolved).get(job.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        log_root = Path(project.root_path) / "logs"
        entries: list[dict[str, str]] = []
        for stage in job.stages:
            if not stage.log_path:
                continue
            path = ensure_within(Path(stage.log_path), log_root)
            if not path.is_file():
                continue
            with path.open("rb") as log_file:
                log_file.seek(max(0, path.stat().st_size - 200_000))
                content = log_file.read().decode("utf-8", errors="replace")
            entries.append({"stage": stage.stage_name, "content": content})
        return entries

    @app.get("/api/v1/projects/{project_id}/models", response_model=list[ModelResponse])
    def list_models(project_id: str, session: Session = Depends(get_session)) -> object:
        if ProjectService(session, resolved).get(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return ModelService(session).list_for_project(project_id)

    @app.get(
        "/api/v1/projects/{project_id}/cameras",
        response_model=list[CameraPoseResponse],
    )
    def list_cameras(project_id: str, session: Session = Depends(get_session)) -> object:
        project = ProjectService(session, resolved).get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        artifact = Path(project.root_path) / "previews" / "cameras.json"
        return read_camera_artifact(artifact) if artifact.is_file() else []

    @app.get("/api/v1/models/{model_id}", response_model=ModelResponse)
    def get_model(model_id: str, session: Session = Depends(get_session)) -> object:
        model = ModelService(session).get(model_id)
        if model is None:
            raise HTTPException(status_code=404, detail="Model not found")
        return model

    @app.post("/api/v1/models/{model_id}/scale", response_model=ScaleResponse)
    def scale_model(
        model_id: str, payload: ScaleRequest, session: Session = Depends(get_session)
    ) -> object:
        return ModelService(session).scale(
            model_id,
            (payload.point_a.x, payload.point_a.y, payload.point_a.z),
            (payload.point_b.x, payload.point_b.y, payload.point_b.z),
            payload.actual_distance,
            payload.unit,
        )

    @app.post("/api/v1/models/{model_id}/crop", response_model=ModelResponse, status_code=201)
    def crop_model(
        model_id: str, payload: CropRequest, session: Session = Depends(get_session)
    ) -> object:
        return ModelService(session).crop(
            model_id,
            (payload.minimum.x, payload.minimum.y, payload.minimum.z),
            (payload.maximum.x, payload.maximum.y, payload.maximum.z),
        )

    @app.post("/api/v1/models/{model_id}/simplify", response_model=ModelResponse, status_code=201)
    def simplify_model(
        model_id: str, payload: SimplifyRequest, session: Session = Depends(get_session)
    ) -> object:
        return ModelService(session).simplify(model_id, payload.target_face_count)

    @app.post("/api/v1/models/{model_id}/exports", response_model=ExportResponse, status_code=201)
    def export_model(
        model_id: str, payload: ExportCreate, session: Session = Depends(get_session)
    ) -> object:
        return ModelService(session).export(
            model_id,
            payload.export_format,
            payload.texture_resolution,
            payload.target_face_count,
            Path(payload.output_directory) if payload.output_directory else None,
            payload.include_point_cloud,
            payload.include_camera_positions,
        )

    @app.get("/api/v1/exports/{export_id}", response_model=ExportResponse)
    def get_export(export_id: str, session: Session = Depends(get_session)) -> object:
        export = ModelService(session).get_export(export_id)
        if export is None:
            raise HTTPException(status_code=404, detail="Export not found")
        return export

    return app


def close_app_engine(app: FastAPI) -> None:
    """Dispose an application engine in tests and embedded lifecycle handling."""
    engine: Engine = app.state.engine
    engine.dispose()
