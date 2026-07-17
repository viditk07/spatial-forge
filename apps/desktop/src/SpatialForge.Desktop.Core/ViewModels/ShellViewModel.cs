using SpatialForge.Desktop.Infrastructure;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop.ViewModels;

public sealed class ShellViewModel : ViewModelBase
{
    private readonly INavigationService _navigation;

    public ShellViewModel(INavigationService navigation)
    {
        _navigation = navigation;
        _navigation.CurrentViewModelChanged += (_, _) => OnPropertyChanged(nameof(CurrentViewModel));
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

    public void Initialize() => _navigation.Navigate(AppPage.Dashboard);
}
