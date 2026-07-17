"""Project application service."""

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from spatialforge_backend.core.config import Settings
from spatialforge_backend.core.errors import AppError, ErrorCode
from spatialforge_backend.db.models import (
    JobStatus,
    Project,
    ProjectStatus,
    ProjectType,
    ReconstructionJob,
)

from .paths import create_project_layout, ensure_within

_SAFE_NAME = re.compile(r"[^A-Za-z0-9_-]+")


def _slug(name: str) -> str:
    value = _SAFE_NAME.sub("_", name.strip()).strip("_")
    return value[:48] or "project"


class ProjectService:
    """Creates and queries projects while enforcing filesystem invariants."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def create(
        self,
        name: str,
        project_type: ProjectType,
        notes: str | None = None,
        *,
        parent_directory: Path | None = None,
    ) -> Project:
        project_id = str(uuid.uuid4())
        parent = self._project_parent(parent_directory)
        root = ensure_within(
            parent / f"{_slug(name)}_{project_id}",
            parent,
        )
        try:
            create_project_layout(root)
        except OSError as error:
            raise AppError(
                ErrorCode.PERMISSION_DENIED,
                "Project folder could not be created",
                "SpatialForge cannot write to the selected project directory.",
                "Choose a writable local folder and try again.",
                technical_details=type(error).__name__,
                retry_safe=True,
            ) from error
        project = Project(
            id=project_id,
            name=name.strip(),
            project_type=project_type.value,
            status=ProjectStatus.DRAFT.value,
            root_path=str(root),
            notes=notes,
        )
        try:
            self.session.add(project)
            self.session.flush()
            manifest = {
                "schema_version": 1,
                "id": project.id,
                "name": project.name,
                "project_type": project.project_type,
                "status": project.status,
            }
            (root / "project.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            shutil.rmtree(root, ignore_errors=True)
            raise
        return project

    def list(self) -> list[Project]:
        statement = select(Project).order_by(Project.updated_at.desc())
        return list(self.session.scalars(statement))

    def get(self, project_id: str) -> Project | None:
        return self.session.get(Project, project_id)

    def mark_opened(self, project: Project) -> Project:
        project.last_opened_at = datetime.now(UTC).replace(tzinfo=None)
        self.session.commit()
        return project

    def update(
        self,
        project: Project,
        *,
        name: str | None = None,
        notes: str | None = None,
        archived: bool | None = None,
    ) -> Project:
        if name is not None:
            project.name = name.strip()
        if notes is not None:
            project.notes = notes
        if archived is not None:
            project.status = (
                ProjectStatus.ARCHIVED.value
                if archived
                else ProjectStatus.DRAFT.value
                if project.status == ProjectStatus.ARCHIVED.value
                else project.status
            )
        self._write_manifest(project)
        self.session.commit()
        return project

    def delete(self, project: Project, confirmation: str) -> None:
        if confirmation != project.name:
            raise AppError(
                ErrorCode.PERMISSION_DENIED,
                "Project deletion was not confirmed",
                "The confirmation text did not match the project name.",
                "Enter the exact project name to permanently delete it.",
            )
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
                "An active reconstruction must be stopped before project deletion.",
                "Cancel the active job, then delete the project.",
            )
        root = Path(project.root_path).expanduser().resolve()
        parent = root.parent
        ensure_within(root, parent)
        if not root.name.endswith(project.id):
            raise self._corrupted_path_error()
        try:
            manifest = json.loads((root / "project.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise self._corrupted_path_error() from error
        if manifest.get("id") != project.id:
            raise self._corrupted_path_error()
        quarantine = ensure_within(parent / f".deleting_{project.id}", parent)
        root.rename(quarantine)
        try:
            self.session.delete(project)
            self.session.commit()
        except Exception:
            self.session.rollback()
            quarantine.rename(root)
            raise
        shutil.rmtree(quarantine)

    def _project_parent(self, selected: Path | None) -> Path:
        candidate = selected or self.settings.projects_dir
        if selected is None:
            try:
                candidate.expanduser().mkdir(parents=True, exist_ok=True)
            except OSError as error:
                raise AppError(
                    ErrorCode.PERMISSION_DENIED,
                    "Default project directory could not be created",
                    "SpatialForge cannot prepare its default project folder.",
                    "Choose a writable project directory in the new-project wizard.",
                    technical_details=type(error).__name__,
                ) from error
        try:
            parent = candidate.expanduser().resolve(strict=True)
        except OSError as error:
            raise AppError(
                ErrorCode.PATH_INVALID,
                "Project directory was not found",
                "The selected project directory does not exist or cannot be accessed.",
                "Choose an existing local folder.",
                technical_details=type(error).__name__,
            ) from error
        if not parent.is_dir():
            raise AppError(
                ErrorCode.PATH_INVALID,
                "Project directory is not a folder",
                "The selected project location is not a directory.",
                "Choose an existing local folder.",
            )
        return parent

    @staticmethod
    def _corrupted_path_error() -> AppError:
        return AppError(
            ErrorCode.PROJECT_CORRUPTED,
            "Project folder identity could not be verified",
            "The project folder or manifest no longer matches its database record.",
            "Restore project.json or move the project back before deleting it.",
        )

    @staticmethod
    def _write_manifest(project: Project) -> None:
        root = Path(project.root_path)
        manifest = {
            "schema_version": 1,
            "id": project.id,
            "name": project.name,
            "project_type": project.project_type,
            "status": project.status,
        }
        (root / "project.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
