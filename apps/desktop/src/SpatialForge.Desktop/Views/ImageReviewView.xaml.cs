using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using SpatialForge.Desktop.ViewModels;

namespace SpatialForge.Desktop.Views;

public partial class ImageReviewView : UserControl
{
    public ImageReviewView() => InitializeComponent();

    private void OpenPreview_Click(object sender, RoutedEventArgs e)
    {
        if (DataContext is not ImageReviewViewModel { SelectedImage.ThumbnailPath: { } path })
        {
            return;
        }

        Image preview = new()
        {
            Source = new BitmapImage(new Uri(path, UriKind.Absolute)),
            Stretch = Stretch.Uniform,
            Margin = new Thickness(24),
        };
        Button close = new()
        {
            Content = "Close preview",
            HorizontalAlignment = HorizontalAlignment.Right,
            VerticalAlignment = VerticalAlignment.Top,
            Margin = new Thickness(20),
            Padding = new Thickness(18, 8, 18, 8),
        };
        Grid content = new();
        content.Children.Add(preview);
        content.Children.Add(close);
        Window window = new()
        {
            Owner = Window.GetWindow(this),
            Title = "SpatialForge photograph preview",
            WindowState = WindowState.Maximized,
            Background = new SolidColorBrush(Color.FromRgb(15, 21, 29)),
            Content = content,
        };
        close.Click += (_, _) => window.Close();
        window.ShowDialog();
    }
}
