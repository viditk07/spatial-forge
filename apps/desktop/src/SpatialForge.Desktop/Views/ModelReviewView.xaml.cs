using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Web.WebView2.Core;
using Microsoft.Win32;
using SpatialForge.Desktop.Contracts;
using SpatialForge.Desktop.ViewModels;

namespace SpatialForge.Desktop.Views;

public partial class ModelReviewView : UserControl
{
    private bool _initialized;

    public ModelReviewView() => InitializeComponent();

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (DataContext is not ModelReviewViewModel viewModel)
        {
            return;
        }

        if (!_initialized)
        {
            await InitializeViewerAsync();
        }

        await viewModel.LoadLatestAsync();
        LoadModelLayers(viewModel.Models);
    }

    private async Task InitializeViewerAsync()
    {
        await Viewer.EnsureCoreWebView2Async();
        CoreWebView2 core = Viewer.CoreWebView2;
        core.Settings.AreDevToolsEnabled = false;
        core.Settings.AreDefaultContextMenusEnabled = false;
        core.Settings.IsStatusBarEnabled = false;
        core.Settings.IsPasswordAutosaveEnabled = false;
        core.Settings.IsGeneralAutofillEnabled = false;
        core.WebMessageReceived += OnWebMessageReceived;
        core.NavigationStarting += (_, args) =>
        {
            if (!Uri.TryCreate(args.Uri, UriKind.Absolute, out Uri? uri)
                || !string.Equals(uri.Scheme, Uri.UriSchemeHttps, StringComparison.Ordinal)
                || !string.Equals(uri.Host, "spatialforge.viewer", StringComparison.OrdinalIgnoreCase)
                || !uri.IsDefaultPort)
            {
                args.Cancel = true;
            }
        };
        core.NewWindowRequested += (_, args) => args.Handled = true;
        core.PermissionRequested += (_, args) => args.State = CoreWebView2PermissionState.Deny;
        string viewerRoot = Path.Combine(AppContext.BaseDirectory, "viewer");
        core.SetVirtualHostNameToFolderMapping(
            "spatialforge.viewer",
            viewerRoot,
            CoreWebView2HostResourceAccessKind.DenyCors);
        Viewer.Source = new Uri("https://spatialforge.viewer/index.html");
        _initialized = true;
    }

    private void OnModelSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_initialized && DataContext is ModelReviewViewModel viewModel)
        {
            SetSelectedLayerVisible(viewModel.SelectedModel);
        }
    }

    private void LoadModelLayers(IEnumerable<ReconstructionModel> models)
    {
        if (!_initialized)
        {
            return;
        }

        Viewer.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { type = "clearLayers" }));
        int index = 0;
        foreach (ReconstructionModel model in models)
        {
            if (!File.Exists(model.FilePath))
            {
                continue;
            }

            string? directory = Path.GetDirectoryName(model.FilePath);
            if (directory is null)
            {
                continue;
            }

            string host = $"model{index}.spatialforge";
            // Three.js loaders use Fetch to read these isolated virtual hosts. Allow is required
            // for that CORS-checked request; the viewer validates the exact modelN host pattern,
            // CSP blocks real network origins, and WebView navigation remains viewer-origin only.
            Viewer.CoreWebView2.SetVirtualHostNameToFolderMapping(
                host,
                directory,
                CoreWebView2HostResourceAccessKind.Allow);
            string url = $"https://{host}/{Uri.EscapeDataString(Path.GetFileName(model.FilePath))}";
            Viewer.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new
            {
                type = "loadLayerUrl",
                layerId = model.Id,
                label = model.ModelType.Replace('_', ' '),
                format = model.Format,
                url,
                visible = model.IsPrimary,
            }));
            index++;
        }

        if (DataContext is ModelReviewViewModel viewModel && viewModel.Cameras.Count > 0)
        {
            Viewer.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new
            {
                type = "loadCameras",
                cameras = viewModel.Cameras,
                visible = false,
            }));
        }
    }

    private void SetSelectedLayerVisible(ReconstructionModel? model)
    {
        if (!_initialized || model is null)
        {
            return;
        }
        Viewer.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new
        {
            type = "setLayerVisibility",
            layerId = model.Id,
            label = model.ModelType.Replace('_', ' '),
            visible = true,
        }));
    }

    private async void OnWebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        if (DataContext is not ModelReviewViewModel viewModel)
        {
            return;
        }

        using JsonDocument document = JsonDocument.Parse(e.WebMessageAsJson);
        JsonElement root = document.RootElement;
        if (!root.TryGetProperty("type", out JsonElement typeElement))
        {
            return;
        }

        switch (typeElement.GetString())
        {
            case "ready":
                LoadModelLayers(viewModel.Models);
                break;
            case "scale":
                JsonElement points = root.GetProperty("points");
                await viewModel.ApplyScaleAsync(
                    Point(points[0]),
                    Point(points[1]),
                    root.GetProperty("actualDistance").GetDouble(),
                    root.GetProperty("unit").GetString() ?? "m");
                break;
            case "crop":
                await viewModel.CropAsync(Point(root.GetProperty("min")), Point(root.GetProperty("max")));
                LoadModelLayers(viewModel.Models);
                break;
            case "export":
                OpenFolderDialog dialog = new()
                {
                    Title = "Choose the SpatialForge export folder",
                    Multiselect = false,
                };
                if (dialog.ShowDialog() != true)
                {
                    break;
                }
                await viewModel.ExportAsync(
                    root.GetProperty("format").GetString() ?? "glb",
                    OptionalInt(root, "textureResolution"),
                    OptionalInt(root, "targetFaceCount"),
                    dialog.FolderName,
                    OptionalBool(root, "includePointCloud"),
                    OptionalBool(root, "includeCameraPositions"));
                break;
        }
    }

    private static Point3 Point(JsonElement value) => new(
        value.GetProperty("x").GetDouble(),
        value.GetProperty("y").GetDouble(),
        value.GetProperty("z").GetDouble());

    private static int? OptionalInt(JsonElement value, string name) =>
        value.TryGetProperty(name, out JsonElement property) && property.ValueKind == JsonValueKind.Number
            ? property.GetInt32()
            : null;

    private static bool OptionalBool(JsonElement value, string name) =>
        value.TryGetProperty(name, out JsonElement property)
        && property.ValueKind is JsonValueKind.True or JsonValueKind.False
        && property.GetBoolean();
}
