using System.Collections.ObjectModel;
using SpatialForge.Desktop.Contracts;
using SpatialForge.Desktop.Services;

namespace SpatialForge.Desktop.ViewModels;

public sealed class ModelReviewViewModel(ISpatialForgeApiClient apiClient) : ViewModelBase
{
    private ReconstructionModel? _selectedModel;
    private string _statusMessage = "Select a completed project model.";

    public ObservableCollection<ReconstructionModel> Models { get; } = [];
    public ObservableCollection<CameraPose> Cameras { get; } = [];

    public ReconstructionModel? SelectedModel
    {
        get => _selectedModel;
        set => SetProperty(ref _selectedModel, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public async Task LoadLatestAsync()
    {
        await RunGuardedAsync(async () =>
        {
            IReadOnlyList<ProjectSummary> projects = await apiClient.GetProjectsAsync();
            Models.Clear();
            Cameras.Clear();
            foreach (ProjectSummary project in projects.OrderByDescending(project => project.UpdatedAt))
            {
                IReadOnlyList<ReconstructionModel> models = await apiClient.GetModelsAsync(project.Id);
                if (models.Count == 0)
                {
                    continue;
                }

                foreach (ReconstructionModel model in models
                    .OrderByDescending(model => model.IsPrimary)
                    .ThenBy(model => LayerOrder(model.ModelType)))
                {
                    Models.Add(model);
                }
                foreach (CameraPose camera in await apiClient.GetCamerasAsync(project.Id))
                {
                    Cameras.Add(camera);
                }
                break;
            }

            SelectedModel = Models.FirstOrDefault(model => model.IsPrimary) ?? Models.FirstOrDefault();
            StatusMessage = SelectedModel is null
                ? "No completed model is available yet."
                : $"{SelectedModel.ModelType.Replace('_', ' ')} · {SelectedModel.VertexCount ?? 0:N0} vertices";
        });
    }

    private static int LayerOrder(string modelType) => modelType switch
    {
        "textured_mesh" => 0,
        "surface_mesh" => 1,
        "dense_point_cloud" => 2,
        "sparse_point_cloud" => 3,
        _ => 4,
    };

    public async Task ApplyScaleAsync(Point3 pointA, Point3 pointB, double distance, string unit)
    {
        if (SelectedModel is null)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            ScaleReference reference = await apiClient.ScaleModelAsync(
                SelectedModel.Id,
                new ScaleModelRequest(pointA, pointB, distance, unit));
            SelectedModel = SelectedModel with
            {
                ScaleFactor = reference.CalculatedScaleFactor,
                CoordinateSystem = "scaled_metres",
            };
            StatusMessage = $"Scale calibrated · factor {reference.CalculatedScaleFactor:G6}";
        });
    }

    public async Task CropAsync(Point3 minimum, Point3 maximum)
    {
        if (SelectedModel is null)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            ReconstructionModel cropped = await apiClient.CropModelAsync(
                SelectedModel.Id,
                new CropModelRequest(minimum, maximum));
            Models.Insert(0, cropped);
            SelectedModel = cropped;
            StatusMessage = "Crop applied to a new derived model; the source is preserved.";
        });
    }

    public async Task ExportAsync(
        string format,
        int? textureResolution,
        int? targetFaceCount,
        string? outputDirectory = null,
        bool includePointCloud = false,
        bool includeCameraPositions = false)
    {
        if (SelectedModel is null)
        {
            return;
        }

        await RunGuardedAsync(async () =>
        {
            ModelExport export = await apiClient.ExportModelAsync(
                SelectedModel.Id,
                new ExportModelRequest(
                    format,
                    textureResolution,
                    targetFaceCount,
                    outputDirectory,
                    includePointCloud,
                    includeCameraPositions));
            StatusMessage = export.Status == "completed"
                ? $"{format.ToUpperInvariant()} exported locally · {export.FileSizeBytes ?? 0:N0} bytes"
                : "Export failed. Open the local technical log for details.";
        });
    }
}
