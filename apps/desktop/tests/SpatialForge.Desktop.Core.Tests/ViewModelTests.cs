using SpatialForge.Desktop.Contracts;
using SpatialForge.Desktop.Core.Tests.Fakes;
using SpatialForge.Desktop.Infrastructure;
using SpatialForge.Desktop.Services;
using SpatialForge.Desktop.ViewModels;
using Xunit;

namespace SpatialForge.Desktop.Core.Tests;

public sealed class ViewModelTests
{
    [Fact]
    public async Task DashboardLoadsProjectsAndHardware()
    {
        FakeApiClient api = new();
        api.Projects.Add(new ProjectSummary(
            "project-1", "Kitchen", "single_room", "ready", DateTime.UtcNow, null));
        ImageReviewViewModel review = new(api);
        NavigationService navigation = new(page =>
            page == AppPage.ImageReview ? review : new SettingsViewModel());
        ProcessingViewModel processing = new(api, new FakeConfirmationService());
        DashboardViewModel viewModel = new(
            api, navigation, review, new FakeConfirmationService(), processing);

        await viewModel.LoadAsync();

        Assert.Single(viewModel.RecentProjects);
        Assert.Equal("Kitchen", viewModel.RecentProjects[0].Name);
        Assert.Equal("balanced_room", viewModel.Hardware?.RecommendedPreset);
        Assert.Contains("COLMAP ready", viewModel.DependencySummary, StringComparison.Ordinal);
        Assert.Null(viewModel.ErrorMessage);
        viewModel.SelectedProject = viewModel.RecentProjects[0];
        await viewModel.LoadSelectedProjectDetailsAsync();
        Assert.Contains("1 KiB", viewModel.SelectedStorageSummary, StringComparison.Ordinal);
        await viewModel.OpenSelectedProjectAsync();
        Assert.Same(review, navigation.CurrentViewModel);
        await viewModel.DeleteSelectedProjectAsync();
        Assert.True(api.DeleteCalled);
        Assert.Empty(viewModel.RecentProjects);
    }

    [Fact]
    public async Task DashboardReopensActiveProjectOnPersistedProcessingJob()
    {
        FakeApiClient api = new();
        api.Projects.Add(new ProjectSummary(
            "project-1", "Kitchen", "single_room", "processing", DateTime.UtcNow, null));
        api.Job = new ReconstructionJob(
            "job-1", "project-1", "processing", "matching", 25, null, null, []);
        ProcessingViewModel processing = new(api, new FakeConfirmationService());
        ImageReviewViewModel review = new(api);
        SettingsViewModel fallback = new();
        NavigationService navigation = new(page =>
            page == AppPage.Processing ? processing : fallback);
        DashboardViewModel viewModel = new(
            api, navigation, review, new FakeConfirmationService(), processing);
        await viewModel.LoadAsync();
        viewModel.SelectedProject = viewModel.RecentProjects[0];

        await viewModel.OpenSelectedProjectAsync();

        Assert.Same(processing, navigation.CurrentViewModel);
        Assert.Equal("job-1", processing.JobId);
    }

    [Fact]
    public async Task WizardRejectsBlankNameAndCreatesValidProject()
    {
        FakeApiClient api = new();
        api.Presets.Add(new ProcessingPreset(
            "preset-1", "Balanced Room", "balanced_room", 16, true));
        SettingsViewModel settings = new();
        ProcessingViewModel processing = new(api, new FakeConfirmationService());
        ImageReviewViewModel imageReview = new(api);
        NavigationService navigation = new(_ => settings);
        NewProjectViewModel viewModel = new(
            api,
            new FakePhotoPicker([]),
            navigation,
            processing,
            imageReview,
            settings,
            new FakeProjectFolderPicker("D:\\SpatialForgeProjects"));

        await viewModel.NextAsync();
        Assert.Equal(WizardStep.Details, viewModel.Step);
        Assert.False(viewModel.CanMoveNext());

        viewModel.Name = "Living Room";
        await viewModel.ChooseProjectDirectoryAsync();
        Assert.True(viewModel.CanMoveNext());
        await viewModel.NextAsync();

        Assert.Equal(WizardStep.PhotoImport, viewModel.Step);
        Assert.Equal("Living Room", viewModel.CreatedProject?.Name);
        Assert.Equal("D:\\SpatialForgeProjects", api.LastCreateRequest?.ProjectDirectory);
        Assert.Single(api.Projects);
    }

    [Fact]
    public async Task WizardImportsAnalysesAndStartsSelectedPreset()
    {
        FakeApiClient api = new();
        api.Images.AddRange(
        [
            Image("one", "good", true),
            Image("two", "good", true),
            Image("three", "review", true),
        ]);
        api.Presets.Add(new ProcessingPreset(
            "preset-1", "Balanced Room", "balanced_room", 16, true));
        api.Job = new ReconstructionJob(
            "job-1", "project-1", "queued", null, 0, null, null, []);
        SettingsViewModel settings = new();
        ProcessingViewModel processing = new(api, new FakeConfirmationService());
        ImageReviewViewModel imageReview = new(api);
        NavigationService navigation = new(page => page switch
        {
            AppPage.Processing => processing,
            AppPage.ImageReview => imageReview,
            _ => settings,
        });
        NewProjectViewModel viewModel = new(
            api,
            new FakePhotoPicker(["one.jpg", "two.jpg", "three.jpg"]),
            navigation,
            processing,
            imageReview,
            settings);
        await viewModel.NextAsync();
        viewModel.Name = "Office";
        await viewModel.NextAsync();

        await viewModel.ImportPhotosAsync();
        Assert.Equal(WizardStep.QualityReview, viewModel.Step);
        Assert.Equal(3, viewModel.ImportedImageCount);
        await viewModel.ReviewImagesAsync();
        Assert.Same(imageReview, navigation.CurrentViewModel);
        await viewModel.NextAsync();
        Assert.Equal(WizardStep.ProcessingPreset, viewModel.Step);
        await viewModel.NextAsync();

        Assert.Equal("job-1", processing.JobId);
        Assert.Same(processing, navigation.CurrentViewModel);
    }

    [Fact]
    public async Task ImageReviewFiltersGoodReviewAndExcludedImages()
    {
        FakeApiClient api = new();
        api.Images.AddRange(
        [
            Image("good", "good", true),
            Image("review", "review", true),
            Image("excluded", "review", false),
        ]);
        ImageReviewViewModel viewModel = new(api);
        await viewModel.LoadAsync("project-1");

        viewModel.Filter = ImageReviewFilter.Good;
        Assert.Equal(["good"], viewModel.VisibleImages.Select(image => image.Id));
        viewModel.Filter = ImageReviewFilter.Review;
        Assert.Equal(["review"], viewModel.VisibleImages.Select(image => image.Id));
        viewModel.Filter = ImageReviewFilter.Excluded;
        Assert.Equal(["excluded"], viewModel.VisibleImages.Select(image => image.Id));
    }

    [Fact]
    public async Task ProcessingRendersStagesAndCancelsOnlyActiveJob()
    {
        FakeApiClient api = new()
        {
            Job = new ReconstructionJob(
                "job-1",
                "project-1",
                "processing",
                "matching",
                25,
                null,
                null,
                [new PipelineStage("matching", 2, "running", 0, null)]),
        };
        FakeConfirmationService confirmation = new();
        ProcessingViewModel viewModel = new(api, confirmation) { JobId = "job-1" };

        await viewModel.RefreshAsync();
        Assert.True(viewModel.CanCancel());
        Assert.Contains("matching", viewModel.StatusMessage, StringComparison.Ordinal);
        Assert.Single(viewModel.Stages);
        Assert.Contains("CPU 25%", viewModel.ResourceSummary, StringComparison.Ordinal);
        Assert.Contains("2 registered", viewModel.ProcessingDetails, StringComparison.Ordinal);
        await viewModel.LoadLogsAsync();
        Assert.Contains("fake matching complete", viewModel.TechnicalLogs, StringComparison.Ordinal);

        await viewModel.CancelAsync();
        Assert.Equal(1, confirmation.Calls);
        Assert.True(api.CancelCalled);
        Assert.Equal("cancelled", viewModel.Job?.Status);
        Assert.False(viewModel.CanCancel());

        await viewModel.RetryAsync();
        Assert.True(api.RetryCalled);
        Assert.Equal("retried-job", viewModel.JobId);
        Assert.Equal("queued", viewModel.Job?.Status);
    }

    [Fact]
    public async Task ProcessingCancellationCanBeDeclined()
    {
        FakeApiClient api = new()
        {
            Job = new ReconstructionJob(
                "job-1", "project-1", "processing", "matching", 25, null, null, []),
        };
        ProcessingViewModel viewModel = new(api, new FakeConfirmationService(false))
        {
            JobId = "job-1",
        };
        await viewModel.RefreshAsync();

        await viewModel.CancelAsync();

        Assert.False(api.CancelCalled);
        Assert.Equal("processing", viewModel.Job?.Status);
    }

    [Fact]
    public async Task SettingsCreatesPrivacySafeDiagnosticAndOpensItsFolder()
    {
        FakeApiClient api = new();
        api.Projects.Add(new ProjectSummary(
            "project-1", "Room", "single_room", "ready", DateTime.UtcNow, null));
        FakeFolderLauncher launcher = new();
        SettingsViewModel viewModel = new(api, new FakeConfirmationService(), launcher);
        await viewModel.LoadAsync();

        await viewModel.CreateDiagnosticAsync();
        await viewModel.OpenLogsAsync();

        Assert.Equal("logs", launcher.OpenedPath);
        Assert.Contains("Opened", viewModel.OperationStatus, StringComparison.Ordinal);
    }

    [Fact]
    public void NavigationUpdatesShellCurrentViewModel()
    {
        SettingsViewModel dashboard = new();
        ErrorViewModel error = new();
        NavigationService navigation = new(page => page == AppPage.Error ? error : dashboard);
        ShellViewModel shell = new(navigation);
        shell.Initialize();
        Assert.Same(dashboard, shell.CurrentViewModel);
        Assert.True(shell.IsDashboardActive);
        Assert.Equal("Dashboard", shell.CurrentPageName);

        navigation.Navigate(AppPage.Error);
        Assert.Same(error, shell.CurrentViewModel);
        Assert.False(shell.IsDashboardActive);
        Assert.Equal("Attention required", shell.CurrentPageName);
    }

    [Fact]
    public void WizardExposesReadableProjectCardsAndContextualActions()
    {
        FakeApiClient api = new();
        SettingsViewModel settings = new();
        NavigationService navigation = new(_ => settings);
        NewProjectViewModel viewModel = new(
            api,
            new FakePhotoPicker([]),
            navigation,
            new ProcessingViewModel(api, new FakeConfirmationService()),
            new ImageReviewViewModel(api),
            settings);

        Assert.Equal(5, viewModel.ProjectTypeOptions.Count);
        Assert.Contains(viewModel.ProjectTypeOptions, option => option.Name == "Single room");
        Assert.Equal("Choose the spatial scope", viewModel.CurrentStepTitle);
        Assert.Equal("Continue", viewModel.NextButtonLabel);
    }

    [Fact]
    public void PresentationContractsNeverExposeBlankHardwareOrEngineValues()
    {
        HardwareProfile hardware = new("", "", 8, 16384, 8192, null, null, false, "", null);
        DependencyStatus dependency = new("colmap", false, null);

        Assert.Equal("Not detected", hardware.DisplayOperatingSystem);
        Assert.Equal("Not detected", hardware.DisplayGpuModel);
        Assert.Equal("Unavailable", hardware.DisplayGpuMemory);
        Assert.Equal("COLMAP", dependency.DisplayName);
        Assert.Equal("Not installed", dependency.AvailabilityLabel);
        Assert.Equal("Version unavailable", dependency.VersionLabel);
    }

    [Fact]
    public async Task ModelReviewLoadsScalesCropsAndExportsDerivedModel()
    {
        FakeApiClient api = new();
        api.Projects.Add(new ProjectSummary(
            "project-1", "Room", "single_room", "completed", DateTime.UtcNow, null));
        api.Models.Add(new ReconstructionModel(
            "model-1", "project-1", "job-1", "textured_mesh", "model.ply", "ply",
            4, 4, 512, 1, "arbitrary", true));
        ModelReviewViewModel viewModel = new(api);

        await viewModel.LoadLatestAsync();
        Assert.Equal("model-1", viewModel.SelectedModel?.Id);

        await viewModel.ApplyScaleAsync(new Point3(0, 0, 0), new Point3(2, 0, 0), 1, "m");
        Assert.Equal(0.5, viewModel.SelectedModel?.ScaleFactor);

        await viewModel.CropAsync(new Point3(0, 0, 0), new Point3(1, 1, 1));
        Assert.Equal("cropped-1", viewModel.SelectedModel?.Id);

        await viewModel.ExportAsync("glb", 2048, null, "D:\\Exports", true, true);
        Assert.Contains("GLB exported", viewModel.StatusMessage, StringComparison.Ordinal);
        Assert.True(api.LastExportRequest?.IncludePointCloud);
        Assert.True(api.LastExportRequest?.IncludeCameraPositions);
        Assert.Null(viewModel.ErrorMessage);
    }

    [Fact]
    public async Task ModelReviewLoadsOnlyLatestProjectAndOrdersPrimaryLayerFirst()
    {
        FakeApiClient api = new();
        DateTime now = DateTime.UtcNow;
        api.Projects.Add(new ProjectSummary(
            "older", "Older", "single_room", "completed", now.AddDays(-1), null));
        api.Projects.Add(new ProjectSummary(
            "latest", "Latest", "single_room", "completed", now, null));
        api.Models.Add(new ReconstructionModel(
            "old-model", "older", "old-job", "surface_mesh", "old.ply", "ply",
            3, 1, 100, 1, "arbitrary", true));
        api.Models.Add(new ReconstructionModel(
            "sparse", "latest", "job", "sparse_point_cloud", "sparse.ply", "ply",
            20, null, 100, 1, "arbitrary", false));
        api.Models.Add(new ReconstructionModel(
            "mesh", "latest", "job", "surface_mesh", "mesh.ply", "ply",
            10, 4, 100, 1, "arbitrary", true));
        api.Cameras.Add(new CameraPose(
            1, new Point3(1, 2, 3), new Quaternion(0, 0, 0, 1)));

        ModelReviewViewModel viewModel = new(api);
        await viewModel.LoadLatestAsync();

        Assert.Equal(["mesh", "sparse"], viewModel.Models.Select(model => model.Id));
        Assert.Equal("mesh", viewModel.SelectedModel?.Id);
        Assert.Single(viewModel.Cameras);
    }

    [Fact]
    public async Task SettingsLoadsStorageAndConfirmsPrivacySafeMaintenance()
    {
        FakeApiClient api = new();
        api.Projects.Add(new ProjectSummary(
            "project-1", "Room", "single_room", "completed", DateTime.UtcNow, null));
        FakeConfirmationService confirmation = new();
        SettingsViewModel viewModel = new(api, confirmation);

        await viewModel.LoadAsync();
        await viewModel.LoadStorageAsync();
        Assert.Contains("20 GiB", viewModel.StorageSummary, StringComparison.Ordinal);

        await viewModel.CompactAsync();
        Assert.Equal(1, confirmation.Calls);
        Assert.Contains("3 KiB", viewModel.OperationStatus, StringComparison.Ordinal);

        await viewModel.CreateDiagnosticAsync();
        Assert.Contains("diagnostic.json", viewModel.OperationStatus, StringComparison.Ordinal);
        Assert.Null(viewModel.ErrorMessage);
    }

    [Fact]
    public void ApiErrorsExposeStablePlainLanguageContract()
    {
        const string response = """
            {"error":{"code":"INSUFFICIENT_STORAGE","title":"Not enough storage",
            "explanation":"The project drive is too full.","recommended_action":"Free space."}}
            """;

        SpatialForgeApiException error = SpatialForgeApiException.FromResponse(400, response);

        Assert.Equal("INSUFFICIENT_STORAGE", error.ErrorCode);
        Assert.Equal("The project drive is too full.", error.Message);
        Assert.Equal("Free space.", error.RecommendedAction);
    }

    private static ImageAsset Image(string id, string quality, bool included) => new(
        id,
        $"{id}.jpg",
        $"thumbnails/{id}.jpg",
        2000,
        1500,
        quality,
        included,
        24,
        new ImageQuality(200, "good", 1500, null, "good", "consistent", quality));
}
