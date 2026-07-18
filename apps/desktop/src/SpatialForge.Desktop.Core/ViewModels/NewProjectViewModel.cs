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

public sealed record ProjectTypeOption(string Id, string Name, string Description, string Icon);

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
                OnPropertyChanged(nameof(CurrentStepTitle));
                OnPropertyChanged(nameof(CurrentStepDescription));
                OnPropertyChanged(nameof(NextButtonLabel));
                NotifyCommands();
            }
        }
    }

    public string StepLabel => $"Step {(int)Step} of 5";
    public string CurrentStepTitle => Step switch
    {
        WizardStep.ProjectType => "Choose the spatial scope",
        WizardStep.Details => "Name and locate your project",
        WizardStep.PhotoImport => "Add your source photographs",
        WizardStep.QualityReview => "Review capture quality",
        _ => "Choose processing quality",
    };
    public string CurrentStepDescription => Step switch
    {
        WizardStep.ProjectType => "Select the scene type so SpatialForge can guide reconstruction settings.",
        WizardStep.Details => "Project files stay in the folder you choose and are never uploaded.",
        WizardStep.PhotoImport => "Choose overlapping smartphone photos transferred to this computer.",
        WizardStep.QualityReview => "Warnings are advisory. You stay in control of every included photograph.",
        _ => "Review the project summary and start local reconstruction when ready.",
    };
    public string NextButtonLabel => Step == WizardStep.ProcessingPreset
        ? "Start reconstruction"
        : "Continue";
    public IReadOnlyList<ProjectTypeOption> ProjectTypeOptions { get; } =
    [
        new("single_room", "Single room", "One enclosed room captured from its perimeter.", "\uE809"),
        new("connected_rooms", "Connected rooms", "A continuous capture through adjacent spaces.", "\uE8A9"),
        new("building_interior", "Building interior", "A larger interior with corridors or multiple areas.", "\uE80F"),
        new("building_exterior", "Building exterior", "Façades and outdoor architectural geometry.", "\uE707"),
        new("experimental", "Experimental", "Unusual scenes using conservative, flexible defaults.", "\uE9CA"),
    ];

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
