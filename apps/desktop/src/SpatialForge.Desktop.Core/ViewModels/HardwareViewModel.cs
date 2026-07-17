using System.Collections.ObjectModel;
using SpatialForge.Desktop.Contracts;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop.ViewModels;

public sealed class HardwareViewModel : ViewModelBase
{
    private readonly ISpatialForgeApiClient _apiClient;
    private HardwareProfile? _profile;

    public HardwareViewModel(ISpatialForgeApiClient apiClient)
    {
        _apiClient = apiClient;
        RefreshCommand = new Infrastructure.AsyncRelayCommand(LoadAsync);
    }

    public HardwareProfile? Profile
    {
        get => _profile;
        private set => SetProperty(ref _profile, value);
    }

    public Infrastructure.AsyncRelayCommand RefreshCommand { get; }
    public ObservableCollection<DependencyStatus> Dependencies { get; } = [];

    public async Task LoadAsync() => await RunGuardedAsync(async () =>
    {
        Profile = await _apiClient.GetHardwareAsync();
        Dependencies.Clear();
        foreach (DependencyStatus dependency in await _apiClient.GetDependenciesAsync())
        {
            Dependencies.Add(dependency);
        }
    });
}
