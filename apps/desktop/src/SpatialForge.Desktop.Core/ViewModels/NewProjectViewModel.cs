using System.Collections.ObjectModel;
using SpatialForge.Desktop.Contracts;
using SpatialForge.Desktop.Infrastructure;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop.ViewModels;

public enum WizardStep
{
    ProjectType = 1,
    Details = 2,
    PhotoImport = 3,
    QualityReview = 4,
    ProcessingPreset = 5,
}

public sealed class NewProjectViewModel : ViewModelBase
{
    private readonly ISpatialForgeApiClient _apiClient;
    private readonly IPhotoPicker _photoPicker;
    private readonly INavigationService _navigation;
    private readonly ProcessingViewModel _processing;
    private readonly ImageReviewViewModel _imageReview;
    private readonly SettingsViewModel _settings;
    private readonly IProjectFolderPicker? _projectFolderPicker;
    private WizardStep _step = WizardStep.ProjectType;
    private string _projectType = "single_room";
    private string _name = string.Empty;
    private string? _notes;
    private ProcessingPreset? _selectedPreset;
    private ProjectSummary? _createdProject;
    private int _importedImageCount;
    private string? _projectDirectory;

    public NewProjectViewModel(
        ISpatialForgeApiClient apiClient,
        IPhotoPicker photoPicker,
        INavigationService navigation,
        ProcessingViewModel processing,
        ImageReviewViewModel imageReview,
        SettingsViewModel settings,
        IProjectFolderPicker? projectFolderPicker = null)
    {
        _apiClient = apiClient;
        _photoPicker = photoPicker;
        _navigation = navigation;
        _processing = processing;
        _imageReview = imageReview;
        _settings = settings;
        _projectFolderPicker = projectFolderPicker;
        NextCommand = new AsyncRelayCommand(NextAsync, CanMoveNext);
        ImportPhotosCommand = new AsyncRelayCommand(
            ImportPhotosAsync,
            () => CreatedProject is not null && Step == WizardStep.PhotoImport);
        ReviewImagesCommand = new AsyncRelayCommand(
            ReviewImagesAsync,
            () => CreatedProject is not null && ImportedImageCount > 0);
        BackCommand = new RelayCommand(MoveBack, () => Step > WizardStep.ProjectType);
        ChooseProjectDirectoryCommand = new AsyncRelayCommand(
            ChooseProjectDirectoryAsync,
            () => _projectFolderPicker is not null);
    }

    public WizardStep Step
    {
        get => _step;
        private set
        {
            if (SetProperty(ref _step, value))
            {
                OnPropertyChanged(nameof(StepLabel));
                NotifyCommands();
            }
        }
    }

    public string StepLabel => $"Step {(int)Step} of 5";
    public IReadOnlyList<string> ProjectTypes { get; } =
        ["single_room", "connected_rooms", "building_interior", "building_exterior", "experimental"];

    public string ProjectType
    {
        get => _projectType;
        set
        {
            if (SetProperty(ref _projectType, value))
            {
                NotifyCommands();
            }
        }
    }

    public string Name
    {
        get => _name;
        set
        {
            if (SetProperty(ref _name, value))
            {
                NotifyCommands();
            }
        }
    }

    public string? Notes
    {
        get => _notes;
        set => SetProperty(ref _notes, value);
    }

    public string? ProjectDirectory
    {
        get => _projectDirectory;
        private set => SetProperty(ref _projectDirectory, value);
    }

    public int ImportedImageCount
    {
        get => _importedImageCount;
        set
        {
            if (SetProperty(ref _importedImageCount, value))
            {
                NotifyCommands();
            }
        }
    }

    public ObservableCollection<ProcessingPreset> Presets { get; } = [];
    public ProcessingPreset? SelectedPreset
    {
        get => _selectedPreset;
        set
        {
            if (SetProperty(ref _selectedPreset, value))
            {
                NotifyCommands();
            }
        }
    }

    public ProjectSummary? CreatedProject
    {
        get => _createdProject;
        private set
        {
            if (SetProperty(ref _createdProject, value))
            {
                NotifyCommands();
            }
        }
    }

    public AsyncRelayCommand NextCommand { get; }
    public AsyncRelayCommand ImportPhotosCommand { get; }
    public AsyncRelayCommand ReviewImagesCommand { get; }
    public RelayCommand BackCommand { get; }
    public AsyncRelayCommand ChooseProjectDirectoryCommand { get; }

    public async Task ChooseProjectDirectoryAsync()
    {
        if (_projectFolderPicker is null)
        {
            return;
        }

        string? selected = await _projectFolderPicker.PickFolderAsync();
        if (!string.IsNullOrWhiteSpace(selected))
        {
            ProjectDirectory = selected;
        }
    }

    public async Task LoadPresetsAsync()
    {
        IReadOnlyList<ProcessingPreset> presets = await _apiClient.GetPresetsAsync();
        Presets.Clear();
        foreach (ProcessingPreset preset in presets)
        {
            Presets.Add(preset);
        }

        SelectedPreset ??= Presets.FirstOrDefault(preset => preset.PresetType == "balanced_room")
            ?? Presets.FirstOrDefault();
    }

    public bool CanMoveNext() => Step switch
    {
        WizardStep.ProjectType => !string.IsNullOrWhiteSpace(ProjectType),
        WizardStep.Details => !string.IsNullOrWhiteSpace(Name) && Name.Trim().Length <= 120,
        WizardStep.PhotoImport => ImportedImageCount > 0,
        WizardStep.QualityReview => ImportedImageCount >= 3,
        WizardStep.ProcessingPreset => SelectedPreset is not null,
        _ => false,
    };

    public async Task NextAsync()
    {
        if (!CanMoveNext())
        {
            return;
        }

        if (Step == WizardStep.Details && CreatedProject is null)
        {
            await RunGuardedAsync(async () =>
            {
                CreatedProject = await _apiClient.CreateProjectAsync(
                    new CreateProjectRequest(Name.Trim(), ProjectType, Notes, ProjectDirectory));
                Step = WizardStep.PhotoImport;
            });
            return;
        }

        if (Step == WizardStep.ProcessingPreset && CreatedProject is not null && SelectedPreset is not null)
        {
            await RunGuardedAsync(async () =>
            {
                ReconstructionJob job = await _apiClient.CreateJobAsync(
                    CreatedProject.Id,
                    SelectedPreset.Id);
                _processing.Begin(job);
                _navigation.Navigate(AppPage.Processing);
            });
            return;
        }

        if (Step < WizardStep.ProcessingPreset)
        {
            Step++;
            if (Step == WizardStep.ProcessingPreset && Presets.Count == 0)
            {
                await LoadPresetsAsync();
            }
        }
    }

    public async Task ImportPhotosAsync()
    {
        if (CreatedProject is null)
        {
            return;
        }

        IReadOnlyList<string> paths = await _photoPicker.PickPhotosAsync();
        if (paths.Count == 0)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            await _apiClient.ImportImagesAsync(
                CreatedProject.Id,
                paths,
                _settings.RemoveGpsFromWorkingCopies);
            IReadOnlyList<ImageAsset> analysed = await _apiClient.AnalyseImagesAsync(
                CreatedProject.Id);
            ImportedImageCount = analysed.Count;
            Step = WizardStep.QualityReview;
        });
    }

    public async Task ReviewImagesAsync()
    {
        if (CreatedProject is null || ImportedImageCount == 0)
        {
            return;
        }

        await _imageReview.LoadAsync(CreatedProject.Id);
        _navigation.Navigate(AppPage.ImageReview);
    }

    private void MoveBack()
    {
        if (Step > WizardStep.ProjectType)
        {
            Step--;
        }
    }

    private void NotifyCommands()
    {
        NextCommand.NotifyCanExecuteChanged();
        ImportPhotosCommand.NotifyCanExecuteChanged();
        ReviewImagesCommand.NotifyCanExecuteChanged();
        BackCommand.NotifyCanExecuteChanged();
    }
}
