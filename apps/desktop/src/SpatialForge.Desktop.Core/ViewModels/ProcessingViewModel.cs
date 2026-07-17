using System.Collections.ObjectModel;
using SpatialForge.Desktop.Contracts;
using SpatialForge.Desktop.Infrastructure;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop.ViewModels;

public sealed class ProcessingViewModel : ViewModelBase
{
    private readonly ISpatialForgeApiClient _apiClient;
    private readonly IConfirmationService _confirmation;
    private ReconstructionJob? _job;
    private string? _jobId;
    private ResourceSnapshot? _resources;
    private string _technicalLogs = "Logs are hidden by default.";
    private int? _includedImageCount;

    public ProcessingViewModel(
        ISpatialForgeApiClient apiClient,
        IConfirmationService confirmation)
    {
        _apiClient = apiClient;
        _confirmation = confirmation;
        CancelCommand = new AsyncRelayCommand(CancelAsync, CanCancel);
        RetryCommand = new AsyncRelayCommand(RetryAsync, CanRetry);
        RefreshCommand = new AsyncRelayCommand(RefreshAsync, () => JobId is not null);
        LoadLogsCommand = new AsyncRelayCommand(LoadLogsAsync, () => JobId is not null);
    }

    public string? JobId
    {
        get => _jobId;
        set
        {
            if (SetProperty(ref _jobId, value))
            {
                _includedImageCount = null;
                RefreshCommand.NotifyCanExecuteChanged();
                LoadLogsCommand.NotifyCanExecuteChanged();
            }
        }
    }

    public ReconstructionJob? Job
    {
        get => _job;
        private set
        {
            if (SetProperty(ref _job, value))
            {
                OnPropertyChanged(nameof(StatusMessage));
                OnPropertyChanged(nameof(ProcessingDetails));
                CancelCommand.NotifyCanExecuteChanged();
                RetryCommand.NotifyCanExecuteChanged();
            }
        }
    }

    public ObservableCollection<PipelineStage> Stages { get; } = [];
    public ResourceSnapshot? Resources
    {
        get => _resources;
        private set
        {
            if (SetProperty(ref _resources, value))
            {
                OnPropertyChanged(nameof(ResourceSummary));
            }
        }
    }

    public string ResourceSummary
    {
        get
        {
            if (Resources is null)
            {
                return "Collecting local resource use…";
            }
            string gpu = Resources.GpuPercent is { } percent
                ? $" · GPU {percent:0}% ({Resources.GpuMemoryUsedMb ?? 0:N0} MiB)"
                : string.Empty;
            return $"CPU {Resources.SystemCpuPercent:0}% · "
                + $"RAM {Resources.MemoryUsedMb / 1024.0:0.0} GiB{gpu} · "
                + $"free disk {Resources.DiskFreeBytes / 1024.0 / 1024 / 1024:0.0} GiB";
        }
    }
    public string ProcessingDetails
    {
        get
        {
            string images = _includedImageCount is null
                ? "Counting included photographs…"
                : $"{_includedImageCount:N0} included photographs";
            if (Resources?.RegisteredCameraCount is { } registered)
            {
                images += $" · {registered:N0} registered";
            }
            if (Job?.StartedAt is not { } started)
            {
                return images;
            }
            TimeSpan elapsed = (Job.CompletedAt ?? DateTime.UtcNow) - started.ToUniversalTime();
            elapsed = elapsed < TimeSpan.Zero ? TimeSpan.Zero : elapsed;
            return $"{images} · elapsed {elapsed:hh\\:mm\\:ss}";
        }
    }
    public string TechnicalLogs
    {
        get => _technicalLogs;
        private set => SetProperty(ref _technicalLogs, value);
    }
    public string StatusMessage => Job?.Status switch
    {
        "queued" => "Waiting for local processing resources",
        "processing" => $"Working on {Job.CurrentStage?.Replace('_', ' ') ?? "reconstruction"}",
        "completed" => "Reconstruction complete",
        "cancelled" => "Reconstruction cancelled",
        "failed" => Job.ErrorMessage ?? "Reconstruction failed",
        "interrupted" => "Processing was interrupted and can be retried",
        _ => "No active reconstruction",
    };

    public AsyncRelayCommand CancelCommand { get; }
    public AsyncRelayCommand RetryCommand { get; }
    public AsyncRelayCommand RefreshCommand { get; }
    public AsyncRelayCommand LoadLogsCommand { get; }

    public async Task RefreshAsync()
    {
        if (JobId is null)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            ReconstructionJob job = await _apiClient.GetJobAsync(JobId);
            UpdateJob(job);
            if (_includedImageCount is null)
            {
                _includedImageCount = (await _apiClient.GetImagesAsync(job.ProjectId))
                    .Count(image => image.Included);
            }
            Resources = await _apiClient.GetResourcesAsync(job.ProjectId);
            OnPropertyChanged(nameof(ProcessingDetails));
        });
    }

    public bool CanCancel() => Job is { Status: "queued" or "processing" };
    public bool CanRetry() => Job is { Status: "failed" or "cancelled" or "interrupted" };

    public async Task CancelAsync()
    {
        if (JobId is null || !CanCancel())
        {
            return;
        }

        bool confirmed = await _confirmation.ConfirmAsync(
            "Cancel reconstruction?",
            "SpatialForge will preserve completed stages so this project can be retried.");
        if (!confirmed)
        {
            return;
        }

        await RunGuardedAsync(async () => UpdateJob(await _apiClient.CancelJobAsync(JobId)));
    }

    public void Begin(ReconstructionJob job)
    {
        JobId = job.Id;
        UpdateJob(job);
    }

    public async Task RetryAsync()
    {
        if (JobId is null || !CanRetry())
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            ReconstructionJob retried = await _apiClient.RetryJobAsync(JobId);
            JobId = retried.Id;
            UpdateJob(retried);
        });
    }

    public async Task LoadLogsAsync()
    {
        if (JobId is null)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            IReadOnlyList<JobLogEntry> entries = await _apiClient.GetJobLogsAsync(JobId);
            TechnicalLogs = entries.Count == 0
                ? "No tool logs are available yet."
                : string.Join(
                    Environment.NewLine + Environment.NewLine,
                    entries.Select(entry => $"[{entry.Stage}]{Environment.NewLine}{entry.Content}"));
        });
    }

    private void UpdateJob(ReconstructionJob job)
    {
        Job = job;
        Stages.Clear();
        foreach (PipelineStage stage in job.Stages.OrderBy(stage => stage.SequenceNumber))
        {
            Stages.Add(stage);
        }
    }
}
