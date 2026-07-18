using SpatialForge.Desktop.Infrastructure;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop.ViewModels;

public sealed class ShellViewModel : ViewModelBase
{
    private readonly INavigationService _navigation;

    public ShellViewModel(INavigationService navigation)
    {
        _navigation = navigation;
        _navigation.CurrentViewModelChanged += (_, _) =>
        {
            OnPropertyChanged(nameof(CurrentViewModel));
            OnPropertyChanged(nameof(IsDashboardActive));
            OnPropertyChanged(nameof(IsNewProjectActive));
            OnPropertyChanged(nameof(IsHardwareActive));
            OnPropertyChanged(nameof(IsModelReviewActive));
            OnPropertyChanged(nameof(IsSettingsActive));
            OnPropertyChanged(nameof(CurrentPageName));
        };
        DashboardCommand = new RelayCommand(() => _navigation.Navigate(AppPage.Dashboard));
        NewProjectCommand = new RelayCommand(() => _navigation.Navigate(AppPage.NewProject));
        HardwareCommand = new RelayCommand(() => _navigation.Navigate(AppPage.Hardware));
        ModelReviewCommand = new RelayCommand(() => _navigation.Navigate(AppPage.ModelReview));
        SettingsCommand = new RelayCommand(() => _navigation.Navigate(AppPage.Settings));
    }

    public ObservableObject CurrentViewModel => _navigation.CurrentViewModel;
    public RelayCommand DashboardCommand { get; }
    public RelayCommand NewProjectCommand { get; }
    public RelayCommand HardwareCommand { get; }
    public RelayCommand ModelReviewCommand { get; }
    public RelayCommand SettingsCommand { get; }
    public bool IsDashboardActive => _navigation.CurrentPage == AppPage.Dashboard;
    public bool IsNewProjectActive => _navigation.CurrentPage == AppPage.NewProject;
    public bool IsHardwareActive => _navigation.CurrentPage == AppPage.Hardware;
    public bool IsModelReviewActive => _navigation.CurrentPage == AppPage.ModelReview;
    public bool IsSettingsActive => _navigation.CurrentPage == AppPage.Settings;
    public string CurrentPageName => _navigation.CurrentPage switch
    {
        AppPage.NewProject => "New project",
        AppPage.ImageReview => "Photo review",
        AppPage.Processing => "Processing",
        AppPage.ModelReview => "Model review",
        AppPage.Hardware => "Hardware",
        AppPage.Settings => "Settings",
        AppPage.Error => "Attention required",
        _ => "Dashboard",
    };

    public void Initialize() => _navigation.Navigate(AppPage.Dashboard);
}
