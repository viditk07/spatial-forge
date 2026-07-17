using System.Net.Http.Json;
using System.Text.Json;
using SpatialForge.Desktop.Contracts;

namespace SpatialForge.Desktop.Services;

public sealed class SpatialForgeApiClient(
    HttpClient httpClient,
    IBackendEndpointProvider endpointProvider) : ISpatialForgeApiClient
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public Task<IReadOnlyList<ProjectSummary>> GetProjectsAsync(
        CancellationToken cancellationToken = default) =>
        GetAsync<IReadOnlyList<ProjectSummary>>("api/v1/projects", cancellationToken);

    public Task<ProjectSummary> CreateProjectAsync(
        CreateProjectRequest request,
        CancellationToken cancellationToken = default) =>
        SendAsync<ProjectSummary>(HttpMethod.Post, "api/v1/projects", request, cancellationToken);

    public Task<ProjectSummary> MarkProjectOpenedAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        SendAsync<ProjectSummary>(
            HttpMethod.Post,
            $"api/v1/projects/{Uri.EscapeDataString(projectId)}/open",
            value: null,
            cancellationToken);

    public async Task DeleteProjectAsync(
        string projectId,
        string confirmation,
        CancellationToken cancellationToken = default)
    {
        string path = $"api/v1/projects/{Uri.EscapeDataString(projectId)}"
            + $"?confirmation={Uri.EscapeDataString(confirmation)}";
        using HttpRequestMessage request = CreateRequest(HttpMethod.Delete, path);
        using HttpResponseMessage response = await httpClient
            .SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken)
            .ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
        {
            string details = await response.Content.ReadAsStringAsync(cancellationToken)
                .ConfigureAwait(false);
            throw SpatialForgeApiException.FromResponse((int)response.StatusCode, details);
        }
    }

    public Task<HardwareProfile> GetHardwareAsync(CancellationToken cancellationToken = default) =>
        GetAsync<HardwareProfile>("api/v1/system/hardware", cancellationToken);

    public Task<IReadOnlyList<DependencyStatus>> GetDependenciesAsync(
        CancellationToken cancellationToken = default) =>
        GetAsync<IReadOnlyList<DependencyStatus>>("api/v1/system/dependencies", cancellationToken);

    public Task<IReadOnlyList<ProcessingPreset>> GetPresetsAsync(
        CancellationToken cancellationToken = default) =>
        GetAsync<IReadOnlyList<ProcessingPreset>>("api/v1/presets", cancellationToken);

    public Task<IReadOnlyList<ImageAsset>> GetImagesAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        GetAsync<IReadOnlyList<ImageAsset>>(
            $"api/v1/projects/{Uri.EscapeDataString(projectId)}/images",
            cancellationToken);

    public Task<IReadOnlyList<ImageAsset>> ImportImagesAsync(
        string projectId,
        IReadOnlyList<string> paths,
        bool removeGpsFromWorkingCopies,
        CancellationToken cancellationToken = default) =>
        SendAsync<IReadOnlyList<ImageAsset>>(
            HttpMethod.Post,
            $"api/v1/projects/{Uri.EscapeDataString(projectId)}/images/import",
            new ImportImagesRequest(paths, removeGpsFromWorkingCopies),
            cancellationToken);

    public Task<IReadOnlyList<ImageAsset>> AnalyseImagesAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        SendAsync<IReadOnlyList<ImageAsset>>(
            HttpMethod.Post,
            $"api/v1/projects/{Uri.EscapeDataString(projectId)}/images/analyse",
            value: null,
            cancellationToken);

    public Task<ImageAsset> SetImageIncludedAsync(
        string imageId,
        bool included,
        CancellationToken cancellationToken = default) =>
        SendAsync<ImageAsset>(
            HttpMethod.Patch,
            $"api/v1/images/{Uri.EscapeDataString(imageId)}",
            new { included },
            cancellationToken);

    public Task<ReconstructionJob> CreateJobAsync(
        string projectId,
        string presetId,
        CancellationToken cancellationToken = default) =>
        SendAsync<ReconstructionJob>(
            HttpMethod.Post,
            $"api/v1/projects/{Uri.EscapeDataString(projectId)}/jobs",
            new CreateJobRequest(presetId),
            cancellationToken);

    public Task<ReconstructionJob> GetJobAsync(
        string jobId,
        CancellationToken cancellationToken = default) =>
        GetAsync<ReconstructionJob>(
            $"api/v1/jobs/{Uri.EscapeDataString(jobId)}",
            cancellationToken);

    public Task<ReconstructionJob> GetLatestProjectJobAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        GetAsync<ReconstructionJob>(
            $"api/v1/projects/{Uri.EscapeDataString(projectId)}/jobs/latest",
            cancellationToken);

    public Task<ReconstructionJob> CancelJobAsync(
        string jobId,
        CancellationToken cancellationToken = default) =>
        SendAsync<ReconstructionJob>(
            HttpMethod.Post,
            $"api/v1/jobs/{Uri.EscapeDataString(jobId)}/cancel",
            value: null,
            cancellationToken);

    public Task<ReconstructionJob> RetryJobAsync(
        string jobId,
        CancellationToken cancellationToken = default) =>
        SendAsync<ReconstructionJob>(
            HttpMethod.Post,
            $"api/v1/jobs/{Uri.EscapeDataString(jobId)}/retry",
            value: null,
            cancellationToken);

    public Task<IReadOnlyList<ReconstructionModel>> GetModelsAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        GetAsync<IReadOnlyList<ReconstructionModel>>(
            $"api/v1/projects/{Uri.EscapeDataString(projectId)}/models",
            cancellationToken);

    public Task<IReadOnlyList<CameraPose>> GetCamerasAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        GetAsync<IReadOnlyList<CameraPose>>(
            $"api/v1/projects/{Uri.EscapeDataString(projectId)}/cameras",
            cancellationToken);

    public Task<ScaleReference> ScaleModelAsync(
        string modelId,
        ScaleModelRequest request,
        CancellationToken cancellationToken = default) =>
        SendAsync<ScaleReference>(
            HttpMethod.Post,
            $"api/v1/models/{Uri.EscapeDataString(modelId)}/scale",
            request,
            cancellationToken);

    public Task<ReconstructionModel> CropModelAsync(
        string modelId,
        CropModelRequest request,
        CancellationToken cancellationToken = default) =>
        SendAsync<ReconstructionModel>(
            HttpMethod.Post,
            $"api/v1/models/{Uri.EscapeDataString(modelId)}/crop",
            request,
            cancellationToken);

    public Task<ModelExport> ExportModelAsync(
        string modelId,
        ExportModelRequest request,
        CancellationToken cancellationToken = default) =>
        SendAsync<ModelExport>(
            HttpMethod.Post,
            $"api/v1/models/{Uri.EscapeDataString(modelId)}/exports",
            request,
            cancellationToken);

    public Task<StorageProfile> GetStorageAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        GetAsync<StorageProfile>(
            $"api/v1/system/storage?project_id={Uri.EscapeDataString(projectId)}",
            cancellationToken);

    public Task<CleanupResult> CompactProjectAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        SendAsync<CleanupResult>(
            HttpMethod.Post,
            $"api/v1/projects/{Uri.EscapeDataString(projectId)}/compact",
            value: null,
            cancellationToken);

    public Task<DiagnosticReport> CreateDiagnosticReportAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        SendAsync<DiagnosticReport>(
            HttpMethod.Post,
            $"api/v1/projects/{Uri.EscapeDataString(projectId)}/diagnostics",
            value: null,
            cancellationToken);

    public Task<ResourceSnapshot> GetResourcesAsync(
        string projectId,
        CancellationToken cancellationToken = default) =>
        GetAsync<ResourceSnapshot>(
            $"api/v1/system/resources?project_id={Uri.EscapeDataString(projectId)}",
            cancellationToken);

    public Task<IReadOnlyList<JobLogEntry>> GetJobLogsAsync(
        string jobId,
        CancellationToken cancellationToken = default) =>
        GetAsync<IReadOnlyList<JobLogEntry>>(
            $"api/v1/jobs/{Uri.EscapeDataString(jobId)}/logs",
            cancellationToken);

    private async Task<T> GetAsync<T>(string relativePath, CancellationToken cancellationToken)
    {
        using HttpRequestMessage request = CreateRequest(HttpMethod.Get, relativePath);
        return await SendAsync<T>(request, cancellationToken).ConfigureAwait(false);
    }

    private async Task<T> SendAsync<T>(
        HttpMethod method,
        string relativePath,
        object? value,
        CancellationToken cancellationToken)
    {
        using HttpRequestMessage request = CreateRequest(method, relativePath);
        if (value is not null)
        {
            request.Content = JsonContent.Create(value, options: JsonOptions);
        }

        return await SendAsync<T>(request, cancellationToken).ConfigureAwait(false);
    }

    private async Task<T> SendAsync<T>(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        using HttpResponseMessage response = await httpClient
            .SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken)
            .ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
        {
            string details = await response.Content.ReadAsStringAsync(cancellationToken)
                .ConfigureAwait(false);
            throw SpatialForgeApiException.FromResponse((int)response.StatusCode, details);
        }

        T? value = await response.Content.ReadFromJsonAsync<T>(JsonOptions, cancellationToken)
            .ConfigureAwait(false);
        return value ?? throw new SpatialForgeApiException(
            (int)response.StatusCode,
            "The local backend returned an empty response.");
    }

    private HttpRequestMessage CreateRequest(HttpMethod method, string relativePath)
    {
        BackendEndpoint endpoint = endpointProvider.Endpoint;
        HttpRequestMessage request = new(method, new Uri(endpoint.BaseAddress, relativePath));
        request.Headers.Add("X-SpatialForge-Token", endpoint.LaunchToken);
        return request;
    }
}

public sealed class SpatialForgeApiException : Exception
{
    public SpatialForgeApiException(
        int statusCode,
        string responseBody,
        string? errorCode = null,
        string? title = null,
        string? explanation = null,
        string? recommendedAction = null)
        : base(explanation ?? title ?? $"SpatialForge local API returned HTTP {statusCode}.")
    {
        StatusCode = statusCode;
        ResponseBody = responseBody;
        ErrorCode = errorCode;
        Title = title;
        Explanation = explanation;
        RecommendedAction = recommendedAction;
    }

    public int StatusCode { get; }
    public string ResponseBody { get; }
    public string? ErrorCode { get; }
    public string? Title { get; }
    public string? Explanation { get; }
    public string? RecommendedAction { get; }

    public static SpatialForgeApiException FromResponse(int statusCode, string responseBody)
    {
        try
        {
            using JsonDocument document = JsonDocument.Parse(responseBody);
            if (!document.RootElement.TryGetProperty("error", out JsonElement error))
            {
                return new SpatialForgeApiException(statusCode, responseBody);
            }

            return new SpatialForgeApiException(
                statusCode,
                responseBody,
                Text(error, "code"),
                Text(error, "title"),
                Text(error, "explanation"),
                Text(error, "recommended_action"));
        }
        catch (JsonException)
        {
            return new SpatialForgeApiException(statusCode, responseBody);
        }
    }

    private static string? Text(JsonElement value, string name) =>
        value.TryGetProperty(name, out JsonElement property) && property.ValueKind == JsonValueKind.String
            ? property.GetString()
            : null;
}
