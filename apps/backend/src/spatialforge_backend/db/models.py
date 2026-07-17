"""Durable SpatialForge data model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, utc_now


def new_uuid() -> str:
    return str(uuid.uuid4())


class ProjectType(StrEnum):
    SINGLE_ROOM = "single_room"
    CONNECTED_ROOMS = "connected_rooms"
    BUILDING_INTERIOR = "building_interior"
    BUILDING_EXTERIOR = "building_exterior"
    EXPERIMENTAL = "experimental"


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    IMPORTING = "importing"
    READY = "ready"
    VALIDATING = "validating"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class CaptureDevice(Base):
    __tablename__ = "capture_devices"
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    manufacturer: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    camera_model: Mapped[str | None] = mapped_column(Text)
    lens_model: Mapped[str | None] = mapped_column(Text)
    calibration_profile_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class ProcessingPreset(Base):
    __tablename__ = "processing_presets"
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    preset_type: Mapped[str] = mapped_column(Text, nullable=False)
    configuration_json: Mapped[str] = mapped_column(Text, nullable=False)
    minimum_ram_gb: Mapped[float] = mapped_column(Float, nullable=False)
    requires_cuda: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_system_preset: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_status_updated", "status", "updated_at"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    project_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default=ProjectStatus.DRAFT, nullable=False)
    root_path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    capture_device_id: Mapped[str | None] = mapped_column(
        ForeignKey("capture_devices.id", ondelete="SET NULL")
    )
    selected_preset_id: Mapped[str | None] = mapped_column(
        ForeignKey("processing_presets.id", ondelete="SET NULL")
    )
    known_distance_value: Mapped[float | None] = mapped_column(Float)
    known_distance_unit: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime)
    images: Mapped[list[ImageAsset]] = relationship(cascade="all, delete-orphan")
    jobs: Mapped[list[ReconstructionJob]] = relationship(cascade="all, delete-orphan")
    models: Mapped[list[ReconstructionModel]] = relationship(cascade="all, delete-orphan")


class ImageAsset(Base):
    __tablename__ = "image_assets"
    __table_args__ = (
        Index("ix_images_project_included", "project_id", "included"),
        Index("ix_images_checksum", "checksum_sha256"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    working_path: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(Text)
    checksum_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime)
    focal_length_mm: Mapped[float | None] = mapped_column(Float)
    focal_length_35mm: Mapped[float | None] = mapped_column(Float)
    aperture: Mapped[float | None] = mapped_column(Float)
    exposure_time: Mapped[float | None] = mapped_column(Float)
    iso: Mapped[int | None] = mapped_column(Integer)
    orientation: Mapped[int | None] = mapped_column(Integer)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    quality_status: Mapped[str] = mapped_column(Text, default="review", nullable=False)
    included: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    quality_metric: Mapped[ImageQualityMetric | None] = relationship(
        cascade="all, delete-orphan", uselist=False
    )


class ImageQualityMetric(Base):
    __tablename__ = "image_quality_metrics"
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    image_id: Mapped[str] = mapped_column(
        ForeignKey("image_assets.id", ondelete="CASCADE"), unique=True
    )
    blur_score: Mapped[float | None] = mapped_column(Float)
    brightness_score: Mapped[float | None] = mapped_column(Float)
    exposure_status: Mapped[str | None] = mapped_column(Text)
    feature_count_estimate: Mapped[int | None] = mapped_column(Integer)
    duplicate_group_id: Mapped[str | None] = mapped_column(Text)
    duplicate_similarity: Mapped[float | None] = mapped_column(Float)
    metadata_score: Mapped[float | None] = mapped_column(Float)
    resolution_status: Mapped[str | None] = mapped_column(Text)
    lens_consistency_status: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    analysed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class ReconstructionJob(Base):
    __tablename__ = "reconstruction_jobs"
    __table_args__ = (
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100"),
        Index("ix_jobs_project_status", "project_id", "status"),
        Index(
            "uq_jobs_one_active_per_project",
            "project_id",
            unique=True,
            sqlite_where=text("status IN ('queued', 'processing')"),
        ),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    preset_id: Mapped[str] = mapped_column(ForeignKey("processing_presets.id"))
    status: Mapped[str] = mapped_column(Text, default=JobStatus.QUEUED, nullable=False)
    current_stage: Mapped[str | None] = mapped_column(Text)
    progress_percent: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    process_id: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    technical_error: Mapped[str | None] = mapped_column(Text)
    retry_of_job_id: Mapped[str | None] = mapped_column(ForeignKey("reconstruction_jobs.id"))
    peak_memory_mb: Mapped[float | None] = mapped_column(Float)
    processing_seconds: Mapped[float | None] = mapped_column(Float)
    stages: Mapped[list[PipelineStage]] = relationship(cascade="all, delete-orphan")


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"
    __table_args__ = (
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100"),
        Index("ix_stages_job_sequence", "job_id", "sequence_number", unique=True),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("reconstruction_jobs.id", ondelete="CASCADE"))
    stage_name: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, default=StageStatus.PENDING, nullable=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    command: Mapped[str | None] = mapped_column(Text)
    log_path: Mapped[str | None] = mapped_column(Text)
    output_path: Mapped[str | None] = mapped_column(Text)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)


class ReconstructionModel(Base):
    __tablename__ = "reconstruction_models"
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    job_id: Mapped[str] = mapped_column(ForeignKey("reconstruction_jobs.id", ondelete="CASCADE"))
    model_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    vertex_count: Mapped[int | None] = mapped_column(Integer)
    face_count: Mapped[int | None] = mapped_column(Integer)
    texture_count: Mapped[int | None] = mapped_column(Integer)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    scale_factor: Mapped[float] = mapped_column(Float, default=1, nullable=False)
    coordinate_system: Mapped[str] = mapped_column(Text, default="arbitrary", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class ScaleReference(Base):
    __tablename__ = "scale_references"
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    model_id: Mapped[str] = mapped_column(
        ForeignKey("reconstruction_models.id", ondelete="CASCADE")
    )
    point_a_json: Mapped[str] = mapped_column(Text, nullable=False)
    point_b_json: Mapped[str] = mapped_column(Text, nullable=False)
    reconstructed_distance: Mapped[float] = mapped_column(Float, nullable=False)
    actual_distance: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    calculated_scale_factor: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class Export(Base):
    __tablename__ = "exports"
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    model_id: Mapped[str] = mapped_column(
        ForeignKey("reconstruction_models.id", ondelete="CASCADE")
    )
    export_format: Mapped[str] = mapped_column(Text, nullable=False)
    output_path: Mapped[str] = mapped_column(Text, nullable=False)
    texture_resolution: Mapped[int | None] = mapped_column(Integer)
    target_face_count: Mapped[int | None] = mapped_column(Integer)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class HardwareProfile(Base):
    __tablename__ = "hardware_profiles"
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_uuid)
    cpu_model: Mapped[str] = mapped_column(Text, nullable=False)
    logical_core_count: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_total_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    gpu_model: Mapped[str | None] = mapped_column(Text)
    gpu_memory_mb: Mapped[int | None] = mapped_column(Integer)
    cuda_available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    opengl_version: Mapped[str | None] = mapped_column(Text)
    operating_system: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_preset: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
