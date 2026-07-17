using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using SpatialForge.Desktop.ViewModels;

namespace SpatialForge.Desktop.Views;

public partial class ProcessingView : UserControl
{
    private readonly DispatcherTimer _pollTimer = new() { Interval = TimeSpan.FromSeconds(1) };

    public ProcessingView()
    {
        InitializeComponent();
        _pollTimer.Tick += PollTimerTick;
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        _pollTimer.Start();
        await RefreshAsync();
    }

    private void OnUnloaded(object sender, RoutedEventArgs e) => _pollTimer.Stop();

    private async void PollTimerTick(object? sender, EventArgs e) => await RefreshAsync();

    private async Task RefreshAsync()
    {
        if (DataContext is ProcessingViewModel { IsBusy: false } viewModel)
        {
            await viewModel.RefreshAsync();
        }
    }
}
