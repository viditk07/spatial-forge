using System.IO;
using System.Net.Http;
using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using SpatialForge.Desktop.Infrastructure;
using SpatialForge.Desktop.Services;
using SpatialForge.Desktop.ViewModels;

namespace SpatialForge.Desktop;

public partial class App : Application
{
    private ServiceProvider? _services;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        if (!EnsurePrivacyAccepted())
        {
            Shutdown();
            return;
        }

        _services = ConfigureServices();
        ShellViewModel shell = _services.GetRequiredService<ShellViewModel>();
        shell.Initialize();
        MainWindow window = _services.GetRequiredService<MainWindow>();
        window.DataContext = shell;
        window.Show();

        try
        {
            await _services.GetRequiredService<IBackendLifecycle>().StartAsync();
            await _services.GetRequiredService<DashboardViewModel>().LoadAsync();
        }
        catch (Exception error)
        {
            ErrorViewModel errorViewModel = _services.GetRequiredService<ErrorViewModel>();
            errorViewModel.Title = "The local processing service could not start";
            errorViewModel.Explanation = error.Message;
            errorViewModel.RecommendedAction =
                "Repair the SpatialForge installation or open the local diagnostic logs.";
            _services.GetRequiredService<INavigationService>().Navigate(AppPage.Error);
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        if (_services is not null)
        {
            _services.GetRequiredService<IBackendLifecycle>()
                .StopAsync(CancellationToken.None)
                .GetAwaiter()
                .GetResult();
            _services.Dispose();
        }

        base.OnExit(e);
    }

    private static ServiceProvider ConfigureServices()
    {
        string localData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        string applicationDirectory = AppContext.BaseDirectory;
        BackendProcessOptions backendOptions = new(
            Path.Combine(applicationDirectory, "backend", "spatialforge-backend.exe"),
            [],
            Path.Combine(localData, "SpatialForge"),
            Path.Combine(documents, "SpatialForgeProjects"),
            TimeSpan.FromSeconds(20));

        ServiceCollection services = new();
        services.AddSingleton(backendOptions);
        services.AddSingleton(new HttpClient { Timeout = TimeSpan.FromSeconds(30) });
        services.AddSingleton<BackendProcessService>();
        services.AddSingleton<IBackendLifecycle>(provider =>
            provider.GetRequiredService<BackendProcessService>());
        services.AddSingleton<IBackendEndpointProvider>(provider =>
            provider.GetRequiredService<BackendProcessService>());
        services.AddSingleton<SpatialForgeApiClient>();
        services.AddSingleton<ISpatialForgeApiClient>(provider =>
            provider.GetRequiredService<SpatialForgeApiClient>());
        services.AddSingleton<IPhotoPicker, WindowsPhotoPicker>();
        services.AddSingleton<IProjectFolderPicker, WindowsProjectFolderPicker>();
        services.AddSingleton<IConfirmationService, WindowsConfirmationService>();
        services.AddSingleton<IFolderLauncher, WindowsFolderLauncher>();
        services.AddSingleton<DashboardViewModel>();
        services.AddSingleton<NewProjectViewModel>();
        services.AddSingleton<ImageReviewViewModel>();
        services.AddSingleton<ProcessingViewModel>();
        services.AddSingleton<ModelReviewViewModel>();
        services.AddSingleton<HardwareViewModel>();
        services.AddSingleton<SettingsViewModel>();
        services.AddSingleton<ErrorViewModel>();
        services.AddSingleton<INavigationService>(provider => new NavigationService(page =>
            page switch
            {
                AppPage.Dashboard => provider.GetRequiredService<DashboardViewModel>(),
                AppPage.NewProject => provider.GetRequiredService<NewProjectViewModel>(),
                AppPage.ImageReview => provider.GetRequiredService<ImageReviewViewModel>(),
                AppPage.Processing => provider.GetRequiredService<ProcessingViewModel>(),
                AppPage.ModelReview => provider.GetRequiredService<ModelReviewViewModel>(),
                AppPage.Hardware => provider.GetRequiredService<HardwareViewModel>(),
                AppPage.Settings => provider.GetRequiredService<SettingsViewModel>(),
                AppPage.Error => provider.GetRequiredService<ErrorViewModel>(),
                _ => throw new ArgumentOutOfRangeException(nameof(page), page, null),
            }));
        services.AddSingleton<ShellViewModel>();
        services.AddSingleton<MainWindow>();
        return services.BuildServiceProvider(validateScopes: true);
    }

    private static bool EnsurePrivacyAccepted()
    {
        string localData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string settingsDirectory = Path.Combine(localData, "SpatialForge");
        string marker = Path.Combine(settingsDirectory, "privacy-v1.accepted");
        if (File.Exists(marker))
        {
            return true;
        }

        MessageBoxResult result = MessageBox.Show(
            "SpatialForge processes photographs, models, metadata, and logs only on this computer. "
            + "Uploads, telemetry, crash reporting, and automatic update checks are disabled.\n\n"
            + "Choose Continue to accept this local-processing privacy policy.",
            "SpatialForge privacy",
            MessageBoxButton.OKCancel,
            MessageBoxImage.Information,
            MessageBoxResult.OK);
        if (result != MessageBoxResult.OK)
        {
            return false;
        }

        Directory.CreateDirectory(settingsDirectory);
        File.WriteAllText(marker, "SpatialForge local privacy notice version 1 accepted.\n");
        return true;
    }
}
