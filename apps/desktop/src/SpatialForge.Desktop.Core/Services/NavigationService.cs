using SpatialForge.Desktop.Infrastructure;
using SpatialForge.Desktop.ViewModels;

namespace SpatialForge.Desktop.Services;

public enum AppPage
{
    Dashboard,
    NewProject,
    ImageReview,
    Processing,
    ModelReview,
    Hardware,
    Settings,
    Error,
}

public interface INavigationService
{
    event EventHandler? CurrentViewModelChanged;
    ObservableObject CurrentViewModel { get; }
    AppPage CurrentPage { get; }
    void Navigate(AppPage page);
}

public sealed class NavigationService(
    Func<AppPage, ObservableObject> viewModelFactory) : INavigationService
{
    private ObservableObject? _currentViewModel;

    public event EventHandler? CurrentViewModelChanged;

    public ObservableObject CurrentViewModel => _currentViewModel
        ?? throw new InvalidOperationException("Navigation has not been initialized.");
    public AppPage CurrentPage { get; private set; }

    public void Navigate(AppPage page)
    {
        CurrentPage = page;
        _currentViewModel = viewModelFactory(page);
        CurrentViewModelChanged?.Invoke(this, EventArgs.Empty);
    }
}
