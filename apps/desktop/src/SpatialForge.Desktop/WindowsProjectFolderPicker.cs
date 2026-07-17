using Microsoft.Win32;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop;

public sealed class WindowsProjectFolderPicker : IProjectFolderPicker
{
    public Task<string?> PickFolderAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        OpenFolderDialog dialog = new()
        {
            Title = "Choose where SpatialForge should create the project folder",
            Multiselect = false,
        };
        return Task.FromResult(dialog.ShowDialog() == true ? dialog.FolderName : null);
    }
}
