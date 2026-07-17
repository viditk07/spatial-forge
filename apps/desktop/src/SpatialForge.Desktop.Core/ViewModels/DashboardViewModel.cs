using System.Collections.ObjectModel;
using SpatialForge.Desktop.Contracts;
using SpatialForge.Desktop.Infrastructure;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop.ViewModels;

public sealed class DashboardViewModel : ViewModelBase
{
    private readonly ISpatialForgeApiClient _apiClient;
    private readonly INavigationService _navigation;
    private readonly ImageReviewViewModel _imageReview;
    private readonly IConfirmationService _confirmation;
    private readonly ProcessingViewModel _processing;
    private HardwareProfile? _hardware;
    private ProjectSummary? _selectedProject;
    private string _dependencySummary = "Checking local reconstruction tools…";
    private string _selectedStorageSummary = "Select a project to inspect disk usage.";
    private string? _selectedThumbnailPath;

    public DashboardViewModel(
        ISpatialForgeApiClient apiClient,
        INavigationService navigation,
        ImageReviewViewModel imageReview,
        IConfirmationService confirmation,
        ProcessingViewModel processing)
    {
        _apiClient = apiClient;
        _navigation = navigation;
        _imageReview = imageReview;
        _confirmation = confirmation;
        _processing = processing;
        RefreshCommand = new AsyncRelayCommand(LoadAsync);
        OpenProjectCommand = new AsyncRelayCommand(OpenSelectedProjectAsync, () => SelectedProject is not null);
        DeleteProjectCommand = new AsyncRelayCommand(DeleteSelectedProjectAsync, () => SelectedProject is not null);
        NewProjectCommand = new RelayCommand(() => navigation.Navigate(AppPage.NewProject));
    }

    public ObservableCollection<ProjectSummary> RecentProjects { get; } = [];
    public HardwareProfile? Hardware
    {
        get => _hardware;
        private set => SetProperty(ref _hardware, value);
    }

    public string LocalProcessingLabel => "Local processing • No uploads";
    public string DependencySummary
    {
        get => _dependencySummary;
        private set => SetProperty(ref _dependencySummary, value);
    }
    public string SelectedStorageSummary
    {
        get => _selectedStorageSummary;
        private set => SetProperty(ref _selectedStorageSummary, value);
    }
    public string? SelectedThumbnailPath
    {
        get => _selectedThumbnailPath;
        private set => SetProperty(ref _selectedThumbnailPath, value);
    }
    public ProjectSummary? SelectedProject
    {
        get => _selectedProject;
        set
        {
            if (SetProperty(ref _selectedProject, value))
            {
                OpenProjectCommand.NotifyCanExecuteChanged();
                DeleteProjectCommand.NotifyCanExecuteChanged();
                _ = LoadSelectedProjectDetailsAsync();
            }
        }
    }

    public AsyncRelayCommand RefreshCommand { get; }
    public AsyncRelayCommand OpenProjectCommand { get; }
    public AsyncRelayCommand DeleteProjectCommand { get; }
    public RelayCommand NewProjectCommand { get; }

    public async Task LoadAsync() => await RunGuardedAsync(async () =>
    {
        IReadOnlyList<ProjectSummary> projects = await _apiClient.GetProjectsAsync();
        HardwareProfile hardware = await _apiClient.GetHardwareAsync();
        IReadOnlyList<DependencyStatus> dependencies = await _apiClient.GetDependenciesAsync();
        RecentProjects.Clear();
        foreach (ProjectSummary project in projects)
        {
            RecentProjects.Add(project);
        }

        Hardware = hardware;
        DependencyStatus? colmap = dependencies.FirstOrDefault(item => item.Name == "colmap");
        DependencySummary = colmap?.Available == true
            ? $"COLMAP ready · {colmap.Version ?? "version unavailable"}"
            : "COLMAP is not installed · project review remains available";
    });

    public async Task OpenSelectedProjectAsync()
    {
        if (SelectedProject is null)
        {
            return;
        }

        ProjectSummary opened = await _apiClient.MarkProjectOpenedAsync(SelectedProject.Id);
        int projectIndex = RecentProjects.ToList().FindIndex(project => project.Id == opened.Id);
        if (projectIndex >= 0)
        {
            RecentProjects[projectIndex] = opened;
        }
        SelectedProject = opened;

        if (SelectedProject.Status == "completed")
        {
            _navigation.Navigate(AppPage.ModelReview);
            return;
        }
        if (SelectedProject.Status is "queued" or "processing" or "failed" or "cancelled")
        {
            ReconstructionJob job = await _apiClient.GetLatestProjectJobAsync(SelectedProject.Id);
            _processing.Begin(job);
            _navigation.Navigate(AppPage.Processing);
            return;
        }
        await _imageReview.LoadAsync(SelectedProject.Id);
        _navigation.Navigate(AppPage.ImageReview);
    }

    public async Task LoadSelectedProjectDetailsAsync()
    {
        ProjectSummary? selected = SelectedProject;
        if (selected is null)
        {
            SelectedStorageSummary = "Select a project to inspect disk usage.";
            SelectedThumbnailPath = null;
            return;
        }

        await RunGuardedAsync(async () =>
        {
            StorageProfile storage = await _apiClient.GetStorageAsync(selected.Id);
            IReadOnlyList<ImageAsset> images = await _apiClient.GetImagesAsync(selected.Id);
            if (SelectedProject?.Id != selected.Id)
            {
                return;
            }
            SelectedStorageSummary = $"Project uses {FormatBytes(storage.ProjectSizeBytes)} · "
                + $"{FormatBytes(storage.DiskFreeBytes)} free";
            SelectedThumbnailPath = images.FirstOrDefault()?.ThumbnailPath;
        });
    }

    public async Task DeleteSelectedProjectAsync()
    {
        if (SelectedProject is null)
        {
            return;
        }

        ProjectSummary project = SelectedProject;
        bool confirmed = await _confirmation.ConfirmAsync(
            $"Delete {project.Name}?",
            "This permanently deletes the project, including original photographs and exports. This cannot be undone.");
        if (!confirmed)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            await _apiClient.DeleteProjectAsync(project.Id, project.Name);
            RecentProjects.Remove(project);
            SelectedProject = null;
        });
    }

    private static string FormatBytes(long bytes)
    {
        string[] units = ["B", "KiB", "MiB", "GiB", "TiB"];
        double value = bytes;
        int unit = 0;
        while (value >= 1024 && unit < units.Length - 1)
        {
            value /= 1024;
            unit++;
        }
        return $"{value:0.##} {units[unit]}";
    }
}
