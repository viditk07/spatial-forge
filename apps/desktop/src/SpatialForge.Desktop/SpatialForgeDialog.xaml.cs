using System.Windows;

namespace SpatialForge.Desktop;

public partial class SpatialForgeDialog : Window
{
    public SpatialForgeDialog(
        string title,
        string message,
        string confirmText = "Continue",
        string cancelText = "Cancel",
        bool isWarning = false)
    {
        InitializeComponent();
        Title = title;
        DialogTitle.Text = title;
        DialogMessage.Text = message;
        ConfirmButton.Content = confirmText;
        CancelButton.Content = cancelText;
        DialogKicker.Text = isWarning ? "CONFIRM LOCAL ACTION" : "LOCAL PROCESSING";
        DialogIcon.Text = isWarning ? "\uE7BA" : "\uE72E";
        DialogIcon.Foreground = (System.Windows.Media.Brush)FindResource(
            isWarning ? "StatusWarning" : "AccentPrimary");
        Owner = Application.Current?.MainWindow;
    }

    private void Confirm_Click(object sender, RoutedEventArgs e) => DialogResult = true;

    private void Cancel_Click(object sender, RoutedEventArgs e) => DialogResult = false;
}
