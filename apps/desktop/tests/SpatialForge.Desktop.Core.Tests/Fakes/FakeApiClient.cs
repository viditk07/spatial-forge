using SpatialForge.Desktop.Contracts;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop.Core.Tests.Fakes;

internal sealed class FakeApiClient : ISpatialForgeApiClient
{
    public List<ProjectSummary> Projects { get; } = [];
    public List<ProcessingPreset> Presets { get; } = [];
    public List<ImageAsset> Images { get; } = [];
    public List<ReconstructionModel> Models { get; } = [];
    public List<CameraPose> Cameras { get; } = [];
    public ReconstructionJob? Job { get; set; }
    public bool CancelCalled { get; private set; }
    public bool RetryCalled { get; private set; }
    public bool DeleteCalled { get; private set; }
    public CreateProjectRequest? LastCreateRequest { get; private set; }
    public ExportModelRequest? LastExportRequest { get; private set; }
    public HardwareProfile Hardware { get; set; } = new(
        "Windows 11",
        "Test CPU",
        16,
        32768,
        24000,
        "Test GPU",
        8192,
        true,
        "balanced_room");
    public List<DependencyStatus> Dependencies { get; } =
        [new DependencyStatus("colmap", true, "COLMAP 3.13")];

    public Task<IReadOnlyList<ProjectSummary>> GetProjectsAsync(
        CancellationToken cancellationToken = default) =>
        Task.FromResult<IReadOnlyList<ProjectSummary>>(Projects);

    public Task<ProjectSummary> CreateProjectAsync(
        CreateProjectRequest request,
        CancellationToken cancellationToken = default)
    {
        LastCreateRequest = request;
        ProjectSummary project = new(
            Guid.NewGuid().ToString(),
            request.Name,
            request.ProjectType,
            "draft",
            DateTime.UtcNow,
            null);
        Projects.Add(project);
        return Task.FromResult(project);
    }

    public Task<ProjectSummary> MarkProjectOpenedAsync(
        string projectId,
        CancellationToken cancellationToken = default)
    {
        int index = Projects.FindIndex(project => project.Id == projectId);
        ProjectSummary updated = Projects[index] with { LastOpenedAt = DateTime.UtcNow };
        Projects[index] = updated;
        return Task.FromResult(updated);
    }

    public Task DeleteProjectAsync(
        string projectId,
        string confirmation,
        CancellationToken cancellationToken = default)
    {
        DeleteCalled = true;
        Projects.RemoveAll(project => project.Id == projectId);
        return Task.CompletedTask;
    }

    public Task<HardwareProfile> GetHardwareAsync(CancellationToken cancellationToken = default) =>
        Task.FromResult(Hardware);

    public Task<IReadOnlyList<DependencyStatus>> GetDependenciesAsync(
        CancellationToken cancellationToken = default) =>
        Task.FromResult<IReadOnlyList<DependencyStatus>>(Dependencies);

    public Task<IReadOnlyList<ProcessingPreset>> GetPresetsAsync(
        CancellationToken cancellationToken = default) =>
        Task.FromResult<IReadOnlyList<ProcessingPreset>>(Presets);

    public Task<IReadOnlyList<ImageAsset>> GetImagesAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult<IReadOnlyList<ImageAsset>>(Images);

    public Task<IReadOnlyList<ImageAsset>> ImportImagesAsync(
        string projectId,
        IReadOnlyList<string> paths,
        bool removeGpsFromWorkingCopies,
        CancellationToken cancellationToken = default) =>
        Task.FromResult<IReadOnlyList<ImageAsset>>(Images);

    public Task<IReadOnlyList<ImageAsset>> AnalyseImagesAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult<IReadOnlyList<ImageAsset>>(Images);

    public Task<ImageAsset> SetImageIncludedAsync(
        string imageId,
        bool included,
        CancellationToken cancellationToken = default)
    {
        int index = Images.FindIndex(image => image.Id == imageId);
        ImageAsset updated = Images[index] with { Included = included };
        Images[index] = updated;
        return Task.FromResult(updated);
    }

    public Task<ReconstructionJob> CreateJobAsync(
        string projectId,
        string presetId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult(Job ?? throw new InvalidOperationException("No fake job configured."));

    public Task<ReconstructionJob> GetJobAsync(
        string jobId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult(Job ?? throw new InvalidOperationException("No fake job configured."));

    public Task<ReconstructionJob> GetLatestProjectJobAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult(Job ?? throw new InvalidOperationException("No fake job configured."));

    public Task<ReconstructionJob> CancelJobAsync(
        string jobId,
        CancellationToken cancellationToken = default)
    {
        CancelCalled = true;
        Job = (Job ?? throw new InvalidOperationException("No fake job configured.")) with
        {
            Status = "cancelled",
        };
        return Task.FromResult(Job);
    }

    public Task<ReconstructionJob> RetryJobAsync(
        string jobId,
        CancellationToken cancellationToken = default)
    {
        RetryCalled = true;
        Job = (Job ?? throw new InvalidOperationException("No fake job configured.")) with
        {
            Id = "retried-job",
            Status = "queued",
        };
        return Task.FromResult(Job);
    }

    public Task<IReadOnlyList<ReconstructionModel>> GetModelsAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult<IReadOnlyList<ReconstructionModel>>(
            Models.Where(model => model.ProjectId == projectId).ToList());

    public Task<IReadOnlyList<CameraPose>> GetCamerasAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult<IReadOnlyList<CameraPose>>(Cameras);

    public Task<ScaleReference> ScaleModelAsync(
        string modelId,
        ScaleModelRequest request,
        CancellationToken cancellationToken = default) =>
        Task.FromResult(new ScaleReference("scale-1", request.ActualDistance / 2));

    public Task<ReconstructionModel> CropModelAsync(
        string modelId,
        CropModelRequest request,
        CancellationToken cancellationToken = default)
    {
        ReconstructionModel source = Models.Single(model => model.Id == modelId);
        ReconstructionModel cropped = source with { Id = "cropped-1", ModelType = "cropped_mesh" };
        Models.Add(cropped);
        return Task.FromResult(cropped);
    }

    public Task<ModelExport> ExportModelAsync(
        string modelId,
        ExportModelRequest request,
        CancellationToken cancellationToken = default)
    {
        LastExportRequest = request;
        return Task.FromResult(
            new ModelExport("export-1", request.ExportFormat, "export.glb", 1024, "completed"));
    }

    public Task<StorageProfile> GetStorageAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult(new StorageProfile(20L * 1024 * 1024 * 1024, 1024, 4096, 2048));

    public Task<CleanupResult> CompactProjectAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult(new CleanupResult(4096, 1024, 3072));

    public Task<DiagnosticReport> CreateDiagnosticReportAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult(new DiagnosticReport(Path.Combine("logs", "diagnostic.json"), false));

    public Task<ResourceSnapshot> GetResourcesAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult(new ResourceSnapshot(
            25, 8192, 24576, 50L * 1024 * 1024 * 1024, 12, 512, 42, null, null, 2));

    public Task<IReadOnlyList<JobLogEntry>> GetJobLogsAsync(
        string jobId,
        CancellationToken cancellationToken = default) =>
        Task.FromResult<IReadOnlyList<JobLogEntry>>(
            [new JobLogEntry("matching", "fake matching complete")]);
}

internal sealed class FakePhotoPicker(IReadOnlyList<string> paths) : IPhotoPicker
{
    public Task<IReadOnlyList<string>> PickPhotosAsync(
        CancellationToken cancellationToken = default) => Task.FromResult(paths);
}

internal sealed class FakeProjectFolderPicker(string? path) : IProjectFolderPicker
{
    public Task<string?> PickFolderAsync(CancellationToken cancellationToken = default) =>
        Task.FromResult(path);
}

internal sealed class FakeConfirmationService(bool result = true) : IConfirmationService
{
    public int Calls { get; private set; }

    public Task<bool> ConfirmAsync(
        string title,
        string message,
        CancellationToken cancellationToken = default)
    {
        Calls++;
        return Task.FromResult(result);
    }
}

internal sealed class FakeFolderLauncher : IFolderLauncher
{
    public string? OpenedPath { get; private set; }

    public Task OpenAsync(string folderPath, CancellationToken cancellationToken = default)
    {
        OpenedPath = folderPath;
        return Task.CompletedTask;
    }
}
