using System.Windows;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop;

public sealed class WindowsConfirmationService : IConfirmationService
{
    public Task<bool> ConfirmAsync(
        string title,
        string message,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        SpatialForgeDialog dialog = new(title, message, "Confirm", "Cancel", isWarning: true);
        return Task.FromResult(dialog.ShowDialog() == true);
    }
}
