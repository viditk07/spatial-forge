namespace SpatialForge.Desktop.Services;

public sealed record BackendEndpoint(Uri BaseAddress, string LaunchToken);

public interface IBackendEndpointProvider
{
    BackendEndpoint Endpoint { get; }
}

public interface IBackendLifecycle : IBackendEndpointProvider, IAsyncDisposable
{
    Task StartAsync(CancellationToken cancellationToken = default);
    Task StopAsync(CancellationToken cancellationToken = default);
}

