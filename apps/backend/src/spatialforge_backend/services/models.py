"""Local model registration, scale, crop, simplification, and export services."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any

import trimesh  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from spatialforge_backend.core.errors import AppError, ErrorCode
from spatialforge_backend.db.models import (
    Export,
    Project,
    ReconstructionJob,
    ReconstructionModel,
    ScaleReference,
    new_uuid,
)
from spatialforge_backend.engines.cameras import read_camera_artifact

from .paths import ensure_within

UNITS_TO_METRES = {"mm": 0.001, "cm": 0.01, "m": 1.0, "in": 0.0254, "ft": 0.3048}
EXPORT_FORMATS = {"glb", "obj", "ply"}


def _mesh_error(explanation: str, technical: str = "") -> AppError:
    return AppError(
        ErrorCode.EXPORT_FAILED,
        "Model operation failed",
        explanation,
        "Verify that the source model is complete, then retry with a less aggressive setting.",
        technical_details=technical,
        retry_safe=True,
    )


class ModelService:
    """Perform model operations without network access or shell commands."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def register_job_output(self, job: ReconstructionJob, project: Project) -> None:
        """Register each verified reconstruction layer idempotently."""
        root = Path(project.root_path)
        artifacts = (
            ("sparse_point_cloud", root / "sparse" / "sparse.ply"),
            ("dense_point_cloud", root / "dense" / "fused.ply"),
            ("surface_mesh", root / "mesh" / "meshed-poisson.ply"),
        )
        available = [
            (model_type, path)
            for model_type, path in artifacts
            if path.is_file() and path.stat().st_size
        ]
        if not available:
            return
        primary_path = available[-1][1]
        existing_paths = {
            model.file_path
            for model in self.session.scalars(
                select(ReconstructionModel).where(ReconstructionModel.job_id == job.id)
            )
        }
        for previous in self.list_for_project(project.id):
            previous.is_primary = False
        for model_type, output in available:
            if str(output) in existing_paths:
                existing = self.session.scalar(
                    select(ReconstructionModel).where(
                        ReconstructionModel.job_id == job.id,
                        ReconstructionModel.file_path == str(output),
                    )
                )
                if existing is not None:
                    existing.is_primary = output == primary_path
                continue
            vertices, faces = self._statistics(output, strict=False)
            self.session.add(
                ReconstructionModel(
                    project_id=project.id,
                    job_id=job.id,
                    model_type=model_type,
                    file_path=str(output),
                    format="ply",
                    vertex_count=vertices,
                    face_count=faces,
                    texture_count=0,
                    file_size_bytes=output.stat().st_size,
                    is_primary=output == primary_path,
                )
            )

    def list_for_project(self, project_id: str) -> list[ReconstructionModel]:
        return list(
            self.session.scalars(
                select(ReconstructionModel)
                .where(ReconstructionModel.project_id == project_id)
                .order_by(ReconstructionModel.created_at.desc())
            )
        )

    def get(self, model_id: str) -> ReconstructionModel | None:
        return self.session.get(ReconstructionModel, model_id)

    def scale(
        self,
        model_id: str,
        point_a: tuple[float, float, float],
        point_b: tuple[float, float, float],
        actual_distance: float,
        unit: str,
    ) -> ScaleReference:
        model, project = self._model_and_project(model_id)
        reconstructed = math.dist(point_a, point_b)
        if reconstructed <= 1e-12:
            raise _mesh_error("The two scale points must be distinct.")
        if (
            unit not in UNITS_TO_METRES
            or not math.isfinite(actual_distance)
            or actual_distance <= 0
        ):
            raise _mesh_error("The known distance and unit are invalid.")
        factor = actual_distance * UNITS_TO_METRES[unit] / reconstructed
        reference = ScaleReference(
            project_id=project.id,
            model_id=model.id,
            point_a_json=json.dumps(point_a),
            point_b_json=json.dumps(point_b),
            reconstructed_distance=reconstructed,
            actual_distance=actual_distance,
            unit=unit,
            calculated_scale_factor=factor,
        )
        model.scale_factor = factor
        model.coordinate_system = "scaled_metres"
        project.known_distance_value = actual_distance
        project.known_distance_unit = unit
        self.session.add(reference)
        self.session.commit()
        return reference

    def crop(
        self,
        model_id: str,
        minimum: tuple[float, float, float],
        maximum: tuple[float, float, float],
    ) -> ReconstructionModel:
        model, project = self._model_and_project(model_id)
        lower = tuple(min(a, b) for a, b in zip(minimum, maximum, strict=True))
        upper = tuple(max(a, b) for a, b in zip(minimum, maximum, strict=True))
        mesh = self._load_mesh(self._model_path(model, project))
        if not isinstance(mesh, trimesh.Trimesh):
            raise _mesh_error("Cropping currently requires a surface mesh.")
        centres = mesh.triangles_center
        keep = ((centres >= lower) & (centres <= upper)).all(axis=1)
        if not keep.any():
            raise _mesh_error("The crop bounds do not contain any mesh faces.")
        cropped = mesh.copy()
        cropped.update_faces(keep)
        cropped.remove_unreferenced_vertices()
        output = Path(project.root_path) / "mesh" / f"cropped_{new_uuid()}.{model.format}"
        self._write_and_validate(cropped, output, model.format)
        result = self._record_derived(model, output, "cropped_mesh", cropped)
        self.session.commit()
        return result

    def simplify(self, model_id: str, target_face_count: int) -> ReconstructionModel:
        model, project = self._model_and_project(model_id)
        mesh = self._load_mesh(self._model_path(model, project))
        if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
            raise _mesh_error("Simplification requires a surface mesh.")
        if target_face_count >= len(mesh.faces):
            raise _mesh_error("The polygon target must be lower than the current face count.")
        try:
            simplified = mesh.simplify_quadric_decimation(face_count=target_face_count)
        except Exception as error:
            raise _mesh_error("Mesh simplification could not be completed.", str(error)) from error
        output = Path(project.root_path) / "mesh" / f"simplified_{new_uuid()}.{model.format}"
        self._write_and_validate(simplified, output, model.format)
        result = self._record_derived(model, output, "simplified_mesh", simplified)
        self.session.commit()
        return result

    def export(
        self,
        model_id: str,
        export_format: str,
        texture_resolution: int | None,
        target_face_count: int | None,
        output_directory: Path | None = None,
        include_point_cloud: bool = False,
        include_camera_positions: bool = False,
    ) -> Export:
        model, project = self._model_and_project(model_id)
        export_format = export_format.lower()
        if export_format not in EXPORT_FORMATS:
            raise _mesh_error("Supported exports are GLB, OBJ, and PLY.")
        source = self._model_path(model, project)
        parent = Path(project.root_path) / "exports"
        if output_directory is not None:
            try:
                parent = output_directory.expanduser().resolve(strict=True)
            except OSError as error:
                raise _mesh_error(
                    "The selected export folder is unavailable.", str(error)
                ) from error
            if not parent.is_dir():
                raise _mesh_error("The selected export location is not a folder.")
        output = ensure_within(parent / f"spatialforge_{new_uuid()}.{export_format}", parent)
        record = Export(
            project_id=project.id,
            model_id=model.id,
            export_format=export_format,
            output_path=str(output),
            texture_resolution=texture_resolution,
            target_face_count=target_face_count,
            status="processing",
        )
        self.session.add(record)
        self.session.flush()
        additional_outputs: list[Path] = []
        try:
            if source.suffix.lower() == f".{export_format}" and target_face_count is None:
                shutil.copy2(source, output)
            else:
                geometry = self._load_mesh(source)
                if (
                    target_face_count is not None
                    and isinstance(geometry, trimesh.Trimesh)
                    and 0 < target_face_count < len(geometry.faces)
                ):
                    geometry = geometry.simplify_quadric_decimation(face_count=target_face_count)
                self._write_and_validate(geometry, output, export_format)
            self._statistics(output, strict=True)
            if include_point_cloud:
                point_cloud = self._point_cloud_path(project)
                point_output = ensure_within(
                    output.with_name(f"{output.stem}_point_cloud.ply"), parent
                )
                shutil.copy2(point_cloud, point_output)
                additional_outputs.append(point_output)
                self._statistics(point_output, strict=True)
            if include_camera_positions:
                camera_source = ensure_within(
                    Path(project.root_path) / "previews" / "cameras.json",
                    Path(project.root_path),
                )
                read_camera_artifact(camera_source)
                camera_output = ensure_within(
                    output.with_name(f"{output.stem}_cameras.json"), parent
                )
                shutil.copy2(camera_source, camera_output)
                additional_outputs.append(camera_output)
            record.file_size_bytes = output.stat().st_size + sum(
                path.stat().st_size for path in additional_outputs
            )
            record.status = "completed"
            self.session.commit()
            return record
        except Exception as error:
            output.unlink(missing_ok=True)
            for additional_output in additional_outputs:
                additional_output.unlink(missing_ok=True)
            record.status = "failed"
            self.session.commit()
            if isinstance(error, AppError):
                raise
            raise _mesh_error("The exported model could not be validated.", str(error)) from error

    def _point_cloud_path(self, project: Project) -> Path:
        candidates = list(
            self.session.scalars(
                select(ReconstructionModel)
                .where(
                    ReconstructionModel.project_id == project.id,
                    ReconstructionModel.model_type.in_(("dense_point_cloud", "sparse_point_cloud")),
                )
                .order_by(
                    (ReconstructionModel.model_type == "dense_point_cloud").desc(),
                    ReconstructionModel.created_at.desc(),
                )
            )
        )
        for candidate in candidates:
            path = ensure_within(Path(candidate.file_path), Path(project.root_path))
            if path.is_file() and path.suffix.lower() == ".ply":
                return path
        raise _mesh_error("No reconstructed point cloud is available to include.")

    def get_export(self, export_id: str) -> Export | None:
        return self.session.get(Export, export_id)

    def _model_and_project(self, model_id: str) -> tuple[ReconstructionModel, Project]:
        model = self.get(model_id)
        project = self.session.get(Project, model.project_id) if model else None
        if model is None or project is None:
            raise _mesh_error("The selected model is no longer available.")
        return model, project

    @staticmethod
    def _model_path(model: ReconstructionModel, project: Project) -> Path:
        path = ensure_within(Path(model.file_path), Path(project.root_path))
        if not path.is_file() or path.stat().st_size == 0:
            raise _mesh_error("The model file is missing or empty.")
        return path

    @staticmethod
    def _load_mesh(path: Path) -> Any:
        try:
            geometry = trimesh.load(path, force=None, process=False)
            if isinstance(geometry, trimesh.Scene):
                geometries = list(geometry.geometry.values())
                if len(geometries) == 1:
                    geometry = geometries[0]
                elif geometries and all(isinstance(item, trimesh.Trimesh) for item in geometries):
                    geometry = geometry.to_mesh()
            return geometry
        except Exception as error:
            raise _mesh_error("The model file could not be loaded.", str(error)) from error

    @classmethod
    def _statistics(cls, path: Path, *, strict: bool) -> tuple[int, int]:
        try:
            geometry = cls._load_mesh(path)
            if isinstance(geometry, trimesh.Scene):
                vertices = sum(len(item.vertices) for item in geometry.geometry.values())
                faces = sum(
                    len(item.faces)
                    for item in geometry.geometry.values()
                    if isinstance(item, trimesh.Trimesh)
                )
            else:
                vertices = len(geometry.vertices)
                faces = len(geometry.faces) if isinstance(geometry, trimesh.Trimesh) else 0
            if strict and vertices == 0:
                raise ValueError("model contains no vertices")
            return vertices, faces
        except AppError:
            if strict:
                raise
            return 0, 0

    @classmethod
    def _write_and_validate(cls, geometry: Any, output: Path, export_format: str) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        geometry.export(output, file_type=export_format)
        if not output.is_file() or output.stat().st_size == 0:
            raise _mesh_error("The model operation produced no output.")
        cls._statistics(output, strict=True)

    def _record_derived(
        self,
        source: ReconstructionModel,
        output: Path,
        model_type: str,
        geometry: Any,
    ) -> ReconstructionModel:
        result = ReconstructionModel(
            project_id=source.project_id,
            job_id=source.job_id,
            model_type=model_type,
            file_path=str(output),
            format=source.format,
            vertex_count=len(geometry.vertices),
            face_count=len(geometry.faces),
            texture_count=source.texture_count,
            file_size_bytes=output.stat().st_size,
            scale_factor=source.scale_factor,
            coordinate_system=source.coordinate_system,
            is_primary=True,
        )
        for previous in self.list_for_project(source.project_id):
            previous.is_primary = False
        self.session.add(result)
        return result
