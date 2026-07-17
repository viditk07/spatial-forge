using System.Diagnostics;
using System.IO;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop;

public sealed class WindowsFolderLauncher : IFolderLauncher
{
    public Task OpenAsync(string folderPath, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        string fullPath = Path.GetFullPath(folderPath);
        if (!Directory.Exists(fullPath))
        {
            throw new DirectoryNotFoundException("The local log folder no longer exists.");
        }

        ProcessStartInfo startInfo = new("explorer.exe") { UseShellExecute = false };
        startInfo.ArgumentList.Add(fullPath);
        _ = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Windows Explorer could not be started.");
        return Task.CompletedTask;
    }
}
