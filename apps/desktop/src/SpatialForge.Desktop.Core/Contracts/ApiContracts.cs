using System.Text.Json.Serialization;

namespace SpatialForge.Desktop.Contracts;

public sealed record ProjectSummary(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("project_type")] string ProjectType,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("updated_at")] DateTime UpdatedAt,
    [property: JsonPropertyName("last_opened_at")] DateTime? LastOpenedAt);

public sealed record HardwareProfile(
    [property: JsonPropertyName("operating_system")] string OperatingSystem,
    [property: JsonPropertyName("cpu_model")] string CpuModel,
    [property: JsonPropertyName("logical_core_count")] int LogicalCoreCount,
    [property: JsonPropertyName("memory_total_mb")] long MemoryTotalMb,
    [property: JsonPropertyName("memory_available_mb")] long MemoryAvailableMb,
    [property: JsonPropertyName("gpu_model")] string? GpuModel,
    [property: JsonPropertyName("gpu_memory_mb")] int? GpuMemoryMb,
    [property: JsonPropertyName("cuda_available")] bool CudaAvailable,
    [property: JsonPropertyName("recommended_preset")] string RecommendedPreset,
    [property: JsonPropertyName("opengl_version")] string? OpenGlVersion = null);

public sealed record DependencyStatus(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("available")] bool Available,
    [property: JsonPropertyName("version")] string? Version);

public sealed record ProcessingPreset(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("preset_type")] string PresetType,
    [property: JsonPropertyName("minimum_ram_gb")] double MinimumRamGb,
    [property: JsonPropertyName("requires_cuda")] bool RequiresCuda);

public sealed record ImageQuality(
    [property: JsonPropertyName("blur_score")] double? BlurScore,
    [property: JsonPropertyName("exposure_status")] string? ExposureStatus,
    [property: JsonPropertyName("feature_count_estimate")] int? FeatureCountEstimate,
    [property: JsonPropertyName("duplicate_group_id")] string? DuplicateGroupId,
    [property: JsonPropertyName("resolution_status")] string? ResolutionStatus,
    [property: JsonPropertyName("lens_consistency_status")] string? LensConsistencyStatus,
    [property: JsonPropertyName("recommendation")] string Recommendation);

public sealed record ImageAsset(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("original_filename")] string OriginalFilename,
    [property: JsonPropertyName("thumbnail_path")] string? ThumbnailPath,
    [property: JsonPropertyName("width")] int Width,
    [property: JsonPropertyName("height")] int Height,
    [property: JsonPropertyName("quality_status")] string QualityStatus,
    [property: JsonPropertyName("included")] bool Included,
    [property: JsonPropertyName("focal_length_mm")] double? FocalLengthMm,
    [property: JsonPropertyName("quality_metric")] ImageQuality? QualityMetric);

public sealed record PipelineStage(
    [property: JsonPropertyName("stage_name")] string StageName,
    [property: JsonPropertyName("sequence_number")] int SequenceNumber,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("progress_percent")] double ProgressPercent,
    [property: JsonPropertyName("error_message")] string? ErrorMessage);

public sealed record ReconstructionJob(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("project_id")] string ProjectId,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("current_stage")] string? CurrentStage,
    [property: JsonPropertyName("progress_percent")] double ProgressPercent,
    [property: JsonPropertyName("error_code")] string? ErrorCode,
    [property: JsonPropertyName("error_message")] string? ErrorMessage,
    [property: JsonPropertyName("stages")] IReadOnlyList<PipelineStage> Stages,
    [property: JsonPropertyName("started_at")] DateTime? StartedAt = null,
    [property: JsonPropertyName("completed_at")] DateTime? CompletedAt = null);

public sealed record CreateProjectRequest(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("project_type")] string ProjectType,
    [property: JsonPropertyName("notes")] string? Notes,
    [property: JsonPropertyName("project_directory")] string? ProjectDirectory = null);

public sealed record CreateJobRequest(
    [property: JsonPropertyName("preset_id")] string PresetId);

public sealed record ImportImagesRequest(
    [property: JsonPropertyName("paths")] IReadOnlyList<string> Paths,
    [property: JsonPropertyName("remove_gps_from_working_copies")] bool RemoveGpsFromWorkingCopies);

public sealed record ReconstructionModel(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("project_id")] string ProjectId,
    [property: JsonPropertyName("job_id")] string JobId,
    [property: JsonPropertyName("model_type")] string ModelType,
    [property: JsonPropertyName("file_path")] string FilePath,
    [property: JsonPropertyName("format")] string Format,
    [property: JsonPropertyName("vertex_count")] int? VertexCount,
    [property: JsonPropertyName("face_count")] int? FaceCount,
    [property: JsonPropertyName("file_size_bytes")] long FileSizeBytes,
    [property: JsonPropertyName("scale_factor")] double ScaleFactor,
    [property: JsonPropertyName("coordinate_system")] string CoordinateSystem,
    [property: JsonPropertyName("is_primary")] bool IsPrimary);

public sealed record Point3(
    [property: JsonPropertyName("x")] double X,
    [property: JsonPropertyName("y")] double Y,
    [property: JsonPropertyName("z")] double Z);

public sealed record Quaternion(
    [property: JsonPropertyName("x")] double X,
    [property: JsonPropertyName("y")] double Y,
    [property: JsonPropertyName("z")] double Z,
    [property: JsonPropertyName("w")] double W);

public sealed record CameraPose(
    [property: JsonPropertyName("id")] int Id,
    [property: JsonPropertyName("position")] Point3 Position,
    [property: JsonPropertyName("quaternion")] Quaternion Quaternion);

public sealed record ScaleModelRequest(
    [property: JsonPropertyName("point_a")] Point3 PointA,
    [property: JsonPropertyName("point_b")] Point3 PointB,
    [property: JsonPropertyName("actual_distance")] double ActualDistance,
    [property: JsonPropertyName("unit")] string Unit);

public sealed record ScaleReference(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("calculated_scale_factor")] double CalculatedScaleFactor);

public sealed record CropModelRequest(
    [property: JsonPropertyName("minimum")] Point3 Minimum,
    [property: JsonPropertyName("maximum")] Point3 Maximum);

public sealed record ExportModelRequest(
    [property: JsonPropertyName("export_format")] string ExportFormat,
    [property: JsonPropertyName("texture_resolution")] int? TextureResolution,
    [property: JsonPropertyName("target_face_count")] int? TargetFaceCount,
    [property: JsonPropertyName("output_directory")] string? OutputDirectory = null,
    [property: JsonPropertyName("include_point_cloud")] bool IncludePointCloud = false,
    [property: JsonPropertyName("include_camera_positions")] bool IncludeCameraPositions = false);

public sealed record ModelExport(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("export_format")] string ExportFormat,
    [property: JsonPropertyName("output_path")] string OutputPath,
    [property: JsonPropertyName("file_size_bytes")] long? FileSizeBytes,
    [property: JsonPropertyName("status")] string Status);

public sealed record StorageProfile(
    [property: JsonPropertyName("disk_free_bytes")] long DiskFreeBytes,
    [property: JsonPropertyName("project_size_bytes")] long ProjectSizeBytes,
    [property: JsonPropertyName("estimated_processing_bytes")] long EstimatedProcessingBytes,
    [property: JsonPropertyName("reserve_bytes")] long ReserveBytes);

public sealed record CleanupResult(
    [property: JsonPropertyName("bytes_before")] long BytesBefore,
    [property: JsonPropertyName("bytes_after")] long BytesAfter,
    [property: JsonPropertyName("bytes_reclaimed")] long BytesReclaimed);

public sealed record DiagnosticReport(
    [property: JsonPropertyName("output_path")] string OutputPath,
    [property: JsonPropertyName("contains_user_content")] bool ContainsUserContent);

public sealed record ResourceSnapshot(
    [property: JsonPropertyName("system_cpu_percent")] double SystemCpuPercent,
    [property: JsonPropertyName("memory_used_mb")] long MemoryUsedMb,
    [property: JsonPropertyName("memory_available_mb")] long MemoryAvailableMb,
    [property: JsonPropertyName("disk_free_bytes")] long DiskFreeBytes,
    [property: JsonPropertyName("process_cpu_percent")] double? ProcessCpuPercent,
    [property: JsonPropertyName("process_memory_mb")] double? ProcessMemoryMb,
    [property: JsonPropertyName("process_id")] int? ProcessId,
    [property: JsonPropertyName("gpu_percent")] double? GpuPercent = null,
    [property: JsonPropertyName("gpu_memory_used_mb")] long? GpuMemoryUsedMb = null,
    [property: JsonPropertyName("registered_camera_count")] int? RegisteredCameraCount = null);

public sealed record JobLogEntry(
    [property: JsonPropertyName("stage")] string Stage,
    [property: JsonPropertyName("content")] string Content);
