using Microsoft.Win32;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop;

public sealed class WindowsPhotoPicker : IPhotoPicker
{
    public Task<IReadOnlyList<string>> PickPhotosAsync(
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        OpenFileDialog dialog = new()
        {
            Title = "Select smartphone photographs",
            Filter = "Supported photographs|*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.webp|All files|*.*",
            Multiselect = true,
            CheckFileExists = true,
        };
        IReadOnlyList<string> paths = dialog.ShowDialog() == true ? dialog.FileNames : [];
        return Task.FromResult(paths);
    }
}
