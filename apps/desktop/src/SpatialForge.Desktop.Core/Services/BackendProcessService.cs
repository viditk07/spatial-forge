using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;

namespace SpatialForge.Desktop.Services;

public sealed record BackendProcessOptions(
    string ExecutablePath,
    IReadOnlyList<string> Arguments,
    string DataDirectory,
    string ProjectsDirectory,
    TimeSpan StartupTimeout);

public sealed class BackendProcessService(
    BackendProcessOptions options,
    HttpClient healthClient) : IBackendLifecycle
{
    private Process? _process;
    private BackendEndpoint? _endpoint;

    public BackendEndpoint Endpoint => _endpoint
        ?? throw new InvalidOperationException("The local backend has not started.");

    public async Task StartAsync(CancellationToken cancellationToken = default)
    {
        if (_process is { HasExited: false })
        {
            return;
        }

        if (!File.Exists(options.ExecutablePath))
        {
            throw new FileNotFoundException(
                "The packaged SpatialForge backend could not be found.",
                options.ExecutablePath);
        }

        int port = FindLoopbackPort();
        string token = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
        ProcessStartInfo startInfo = new(options.ExecutablePath)
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardError = true,
            RedirectStandardOutput = true,
        };
        foreach (string argument in options.Arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        startInfo.Environment["SPATIALFORGE_HOST"] = "127.0.0.1";
        startInfo.Environment["SPATIALFORGE_PORT"] = port.ToString(
            System.Globalization.CultureInfo.InvariantCulture);
        startInfo.Environment["SPATIALFORGE_LAUNCH_TOKEN"] = token;
        startInfo.Environment["SPATIALFORGE_DATA_DIR"] = options.DataDirectory;
        startInfo.Environment["SPATIALFORGE_PROJECTS_DIR"] = options.ProjectsDirectory;
        _process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("The local backend process did not start.");
        _endpoint = new BackendEndpoint(new Uri($"http://127.0.0.1:{port}/"), token);

        using CancellationTokenSource timeout = CancellationTokenSource.CreateLinkedTokenSource(
            cancellationToken);
        timeout.CancelAfter(options.StartupTimeout);
        while (!timeout.IsCancellationRequested)
        {
            if (_process.HasExited)
            {
                string error = await _process.StandardError.ReadToEndAsync(timeout.Token)
                    .ConfigureAwait(false);
                throw new InvalidOperationException(
                    $"The local backend exited during startup: {Redact(error)}");
            }

            try
            {
                using HttpRequestMessage request = new(
                    HttpMethod.Get,
                    new Uri(Endpoint.BaseAddress, "api/v1/health"));
                request.Headers.Add("X-SpatialForge-Token", token);
                using HttpResponseMessage response = await healthClient
                    .SendAsync(request, timeout.Token)
                    .ConfigureAwait(false);
                if (response.IsSuccessStatusCode)
                {
                    return;
                }
            }
            catch (HttpRequestException)
            {
                // The backend may not have bound the loopback socket yet.
            }

            await Task.Delay(100, timeout.Token).ConfigureAwait(false);
        }

        await StopAsync(CancellationToken.None).ConfigureAwait(false);
        throw new TimeoutException("The local backend did not become ready in time.");
    }

    public async Task StopAsync(CancellationToken cancellationToken = default)
    {
        Process? process = _process;
        _process = null;
        _endpoint = null;
        if (process is null)
        {
            return;
        }

        if (!process.HasExited)
        {
            process.Kill(entireProcessTree: true);
            await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        }

        process.Dispose();
    }

    public async ValueTask DisposeAsync()
    {
        await StopAsync(CancellationToken.None).ConfigureAwait(false);
        GC.SuppressFinalize(this);
    }

    private static int FindLoopbackPort()
    {
        TcpListener listener = new(IPAddress.Loopback, 0);
        listener.Start();
        int port = ((IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        return port;
    }

    private static string Redact(string value)
    {
        string profile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        return string.IsNullOrWhiteSpace(profile)
            ? value[..Math.Min(value.Length, 1000)]
            : value.Replace(profile, "~", StringComparison.OrdinalIgnoreCase)[
                ..Math.Min(value.Replace(profile, "~", StringComparison.OrdinalIgnoreCase).Length, 1000)
            ];
    }
}

