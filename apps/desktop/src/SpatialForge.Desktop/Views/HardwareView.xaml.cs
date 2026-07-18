using System.Windows;
using System.Windows.Controls;
using SpatialForge.Desktop.ViewModels;
namespace SpatialForge.Desktop.Views;

public partial class HardwareView : UserControl
{
    public HardwareView() => InitializeComponent();

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (DataContext is HardwareViewModel viewModel)
        {
            await viewModel.LoadAsync();
        }
    }
}
