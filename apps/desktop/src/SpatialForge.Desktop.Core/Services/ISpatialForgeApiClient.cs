using SpatialForge.Desktop.Contracts;

namespace SpatialForge.Desktop.Services;

public interface ISpatialForgeApiClient
{
    Task<IReadOnlyList<ProjectSummary>> GetProjectsAsync(CancellationToken cancellationToken = default);
    Task<ProjectSummary> CreateProjectAsync(
        CreateProjectRequest request,
        CancellationToken cancellationToken = default);
    Task<ProjectSummary> MarkProjectOpenedAsync(
        string projectId,
        CancellationToken cancellationToken = default);
    Task DeleteProjectAsync(
        string projectId,
        string confirmation,
        CancellationToken cancellationToken = default);
    Task<HardwareProfile> GetHardwareAsync(CancellationToken cancellationToken = default);
    Task<IReadOnlyList<DependencyStatus>> GetDependenciesAsync(
        CancellationToken cancellationToken = default);
    Task<IReadOnlyList<ProcessingPreset>> GetPresetsAsync(
        CancellationToken cancellationToken = default);
    Task<IReadOnlyList<ImageAsset>> GetImagesAsync(
        string projectId,
        CancellationToken cancellationToken = default);
    Task<IReadOnlyList<ImageAsset>> ImportImagesAsync(
        string projectId,
        IReadOnlyList<string> paths,
        bool removeGpsFromWorkingCopies,
        CancellationToken cancellationToken = default);
    Task<IReadOnlyList<ImageAsset>> AnalyseImagesAsync(
        string projectId,
        CancellationToken cancellationToken = default);
    Task<ImageAsset> SetImageIncludedAsync(
        string imageId,
        bool included,
        CancellationToken cancellationToken = default);
    Task<ReconstructionJob> CreateJobAsync(
        string projectId,
        string presetId,
        CancellationToken cancellationToken = default);
    Task<ReconstructionJob> GetJobAsync(string jobId, CancellationToken cancellationToken = default);
    Task<ReconstructionJob> GetLatestProjectJobAsync(
        string projectId,
        CancellationToken cancellationToken = default);
    Task<ReconstructionJob> CancelJobAsync(
        string jobId,
        CancellationToken cancellationToken = default);
    Task<ReconstructionJob> RetryJobAsync(
        string jobId,
        CancellationToken cancellationToken = default);
    Task<IReadOnlyList<ReconstructionModel>> GetModelsAsync(
        string projectId,
        CancellationToken cancellationToken = default);
    Task<IReadOnlyList<CameraPose>> GetCamerasAsync(
        string projectId,
        CancellationToken cancellationToken = default);
    Task<ScaleReference> ScaleModelAsync(
        string modelId,
        ScaleModelRequest request,
        CancellationToken cancellationToken = default);
    Task<ReconstructionModel> CropModelAsync(
        string modelId,
        CropModelRequest request,
        CancellationToken cancellationToken = default);
    Task<ModelExport> ExportModelAsync(
        string modelId,
        ExportModelRequest request,
        CancellationToken cancellationToken = default);
    Task<StorageProfile> GetStorageAsync(
        string projectId,
        CancellationToken cancellationToken = default);
    Task<CleanupResult> CompactProjectAsync(
        string projectId,
        CancellationToken cancellationToken = default);
    Task<DiagnosticReport> CreateDiagnosticReportAsync(
        string projectId,
        CancellationToken cancellationToken = default);
    Task<ResourceSnapshot> GetResourcesAsync(
        string projectId,
        CancellationToken cancellationToken = default);
    Task<IReadOnlyList<JobLogEntry>> GetJobLogsAsync(
        string jobId,
        CancellationToken cancellationToken = default);
}

public interface IPhotoPicker
{
    Task<IReadOnlyList<string>> PickPhotosAsync(CancellationToken cancellationToken = default);
}

public interface IProjectFolderPicker
{
    Task<string?> PickFolderAsync(CancellationToken cancellationToken = default);
}

public interface IConfirmationService
{
    Task<bool> ConfirmAsync(
        string title,
        string message,
        CancellationToken cancellationToken = default);
}

public interface IFolderLauncher
{
    Task OpenAsync(string folderPath, CancellationToken cancellationToken = default);
}
