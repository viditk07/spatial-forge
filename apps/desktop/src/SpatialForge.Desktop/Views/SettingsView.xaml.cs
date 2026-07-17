using System.Windows;
using System.Windows.Controls;
using SpatialForge.Desktop.ViewModels;

namespace SpatialForge.Desktop.Views;

public partial class SettingsView : UserControl
{
    public SettingsView() => InitializeComponent();

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (DataContext is SettingsViewModel viewModel)
        {
            await viewModel.LoadAsync();
        }
    }
}
