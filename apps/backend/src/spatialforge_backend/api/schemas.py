"""Versioned API request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from spatialforge_backend.db.models import ProjectType


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    project_type: ProjectType
    notes: str | None = Field(default=None, max_length=4000)
    project_directory: str | None = Field(default=None, min_length=1, max_length=4096)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    project_type: str
    status: str
    root_path: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    last_opened_at: datetime | None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=4000)
    archived: bool | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    local_only: bool


class ImageImportRequest(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=2000)
    remove_gps_from_working_copies: bool = False


class ImageQualityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    blur_score: float | None
    brightness_score: float | None
    exposure_status: str | None
    feature_count_estimate: int | None
    duplicate_group_id: str | None
    duplicate_similarity: float | None
    metadata_score: float | None
    resolution_status: str | None
    lens_consistency_status: str | None
    recommendation: str


class ImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    original_filename: str
    thumbnail_path: str | None
    width: int
    height: int
    file_size_bytes: int
    mime_type: str
    captured_at: datetime | None
    focal_length_mm: float | None
    focal_length_35mm: float | None
    aperture: float | None
    exposure_time: float | None
    iso: int | None
    orientation: int | None
    quality_status: str
    included: bool
    imported_at: datetime
    quality_metric: ImageQualityResponse | None


class ImageUpdate(BaseModel):
    included: bool


class JobCreate(BaseModel):
    preset_id: str


class StageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    stage_name: str
    sequence_number: int
    status: str
    progress_percent: float
    started_at: datetime | None
    completed_at: datetime | None
    exit_code: int | None
    error_message: str | None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    preset_id: str
    status: str
    current_stage: str | None
    progress_percent: float
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    error_code: str | None
    error_message: str | None
    retry_of_job_id: str | None
    stages: list[StageResponse]


class PresetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    preset_type: str
    minimum_ram_gb: float
    requires_cuda: bool
    is_system_preset: bool


class JobLogEntry(BaseModel):
    stage: str
    content: str


class Point3(BaseModel):
    x: float
    y: float
    z: float


class Quaternion(BaseModel):
    x: float
    y: float
    z: float
    w: float


class CameraPoseResponse(BaseModel):
    id: int
    position: Point3
    quaternion: Quaternion


class CropRequest(BaseModel):
    minimum: Point3
    maximum: Point3


class ScaleRequest(BaseModel):
    point_a: Point3
    point_b: Point3
    actual_distance: float = Field(gt=0)
    unit: str = Field(pattern="^(mm|cm|m|in|ft)$")


class SimplifyRequest(BaseModel):
    target_face_count: int = Field(gt=3)


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    job_id: str
    model_type: str
    file_path: str
    format: str
    vertex_count: int | None
    face_count: int | None
    texture_count: int | None
    file_size_bytes: int
    scale_factor: float
    coordinate_system: str
    is_primary: bool
    created_at: datetime


class ScaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    model_id: str
    reconstructed_distance: float
    actual_distance: float
    unit: str
    calculated_scale_factor: float
    created_at: datetime


class ExportCreate(BaseModel):
    export_format: str = Field(pattern="^(glb|obj|ply)$")
    texture_resolution: int | None = Field(default=None, ge=256, le=16384)
    target_face_count: int | None = Field(default=None, gt=3)
    output_directory: str | None = Field(default=None, min_length=1, max_length=4096)
    include_point_cloud: bool = False
    include_camera_positions: bool = False


class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    model_id: str
    export_format: str
    output_path: str
    texture_resolution: int | None
    target_face_count: int | None
    file_size_bytes: int | None
    status: str
    created_at: datetime


class StorageResponse(BaseModel):
    disk_total_bytes: int
    disk_free_bytes: int
    project_size_bytes: int
    estimated_processing_bytes: int
    reserve_bytes: int


class CleanupResponse(BaseModel):
    bytes_before: int
    bytes_after: int
    bytes_reclaimed: int


class DiagnosticResponse(BaseModel):
    output_path: str
    contains_user_content: bool = False


class ResourceResponse(BaseModel):
    system_cpu_percent: float
    memory_used_mb: int
    memory_available_mb: int
    disk_free_bytes: int
    process_cpu_percent: float | None
    process_memory_mb: float | None
    process_id: int | None
    gpu_percent: float | None
    gpu_memory_used_mb: int | None
    registered_camera_count: int | None
