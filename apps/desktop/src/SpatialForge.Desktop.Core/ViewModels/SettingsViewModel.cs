using System.Collections.ObjectModel;
using SpatialForge.Desktop.Contracts;
using SpatialForge.Desktop.Infrastructure;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop.ViewModels;

public sealed class SettingsViewModel : ViewModelBase
{
    private readonly ISpatialForgeApiClient? _apiClient;
    private readonly IConfirmationService? _confirmation;
    private readonly IFolderLauncher? _folderLauncher;
    private bool _expertMode;
    private bool _removeGpsFromWorkingCopies = true;
    private ProjectSummary? _selectedProject;
    private StorageProfile? _storage;
    private string? _operationStatus;
    private string? _diagnosticPath;

    public SettingsViewModel(
        ISpatialForgeApiClient? apiClient = null,
        IConfirmationService? confirmation = null,
        IFolderLauncher? folderLauncher = null)
    {
        _apiClient = apiClient;
        _confirmation = confirmation;
        _folderLauncher = folderLauncher;
        RefreshCommand = new AsyncRelayCommand(LoadAsync, () => _apiClient is not null);
        CompactCommand = new AsyncRelayCommand(CompactAsync, HasProject);
        DiagnosticCommand = new AsyncRelayCommand(CreateDiagnosticAsync, HasProject);
        OpenLogsCommand = new AsyncRelayCommand(OpenLogsAsync, CanOpenLogs);
    }

    public ObservableCollection<ProjectSummary> Projects { get; } = [];

    public bool ExpertMode
    {
        get => _expertMode;
        set => SetProperty(ref _expertMode, value);
    }

    public bool RemoveGpsFromWorkingCopies
    {
        get => _removeGpsFromWorkingCopies;
        set => SetProperty(ref _removeGpsFromWorkingCopies, value);
    }

    public ProjectSummary? SelectedProject
    {
        get => _selectedProject;
        set
        {
            if (SetProperty(ref _selectedProject, value))
            {
                CompactCommand.NotifyCanExecuteChanged();
                DiagnosticCommand.NotifyCanExecuteChanged();
                _ = LoadStorageAsync();
            }
        }
    }

    public StorageProfile? Storage
    {
        get => _storage;
        private set
        {
            if (SetProperty(ref _storage, value))
            {
                OnPropertyChanged(nameof(StorageSummary));
            }
        }
    }

    public string StorageSummary => Storage is null
        ? "Select a project to inspect local storage."
        : $"Project {FormatBytes(Storage.ProjectSizeBytes)} · "
          + $"estimated processing {FormatBytes(Storage.EstimatedProcessingBytes)} · "
          + $"free {FormatBytes(Storage.DiskFreeBytes)}";

    public string? OperationStatus
    {
        get => _operationStatus;
        private set => SetProperty(ref _operationStatus, value);
    }

    public string PrivacySummary =>
        "SpatialForge processes photographs locally. Telemetry and uploads are disabled.";

    public AsyncRelayCommand RefreshCommand { get; }
    public AsyncRelayCommand CompactCommand { get; }
    public AsyncRelayCommand DiagnosticCommand { get; }
    public AsyncRelayCommand OpenLogsCommand { get; }

    public async Task LoadAsync()
    {
        if (_apiClient is null)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            IReadOnlyList<ProjectSummary> projects = await _apiClient.GetProjectsAsync();
            Projects.Clear();
            foreach (ProjectSummary project in projects)
            {
                Projects.Add(project);
            }

            SelectedProject ??= Projects.FirstOrDefault();
        });
    }

    public async Task LoadStorageAsync()
    {
        if (_apiClient is null || SelectedProject is null)
        {
            Storage = null;
            return;
        }

        await RunGuardedAsync(async () => Storage = await _apiClient.GetStorageAsync(SelectedProject.Id));
    }

    public async Task CompactAsync()
    {
        if (_apiClient is null || _confirmation is null || SelectedProject is null)
        {
            return;
        }

        bool confirmed = await _confirmation.ConfirmAsync(
            "Compact this project?",
            "SpatialForge will remove reproducible working files while preserving originals, metadata, the primary model, textures, and exports.");
        if (!confirmed)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            CleanupResult result = await _apiClient.CompactProjectAsync(SelectedProject.Id);
            OperationStatus = $"Compaction reclaimed {FormatBytes(result.BytesReclaimed)}.";
            await LoadStorageAsync();
        });
    }

    public async Task CreateDiagnosticAsync()
    {
        if (_apiClient is null || SelectedProject is null)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            DiagnosticReport report = await _apiClient.CreateDiagnosticReportAsync(SelectedProject.Id);
            _diagnosticPath = report.OutputPath;
            OpenLogsCommand.NotifyCanExecuteChanged();
            OperationStatus = report.ContainsUserContent
                ? "Diagnostic generation was rejected because it contained user content."
                : $"Privacy-safe diagnostic saved locally: {report.OutputPath}";
        });
    }

    public async Task OpenLogsAsync()
    {
        string? folder = _diagnosticPath is null ? null : Path.GetDirectoryName(_diagnosticPath);
        if (_folderLauncher is null || folder is null)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            await _folderLauncher.OpenAsync(folder);
            OperationStatus = "Opened the local project logs folder.";
        });
    }

    private bool HasProject() => _apiClient is not null && SelectedProject is not null;

    private bool CanOpenLogs() => _folderLauncher is not null && _diagnosticPath is not null;

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
