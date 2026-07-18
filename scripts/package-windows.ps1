[CmdletBinding()]
param(
    [string]$Configuration = "Release",
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSNativeCommandUseErrorActionPreference = $true
}
$root = Split-Path -Parent $PSScriptRoot
$artifacts = Join-Path $root "artifacts"
$publish = Join-Path $artifacts "publish"
$backendDist = Join-Path $artifacts "backend"
$notices = Join-Path $artifacts "third-party-notices"
$backendSmokeOut = Join-Path $artifacts "backend-smoke.stdout.log"
$backendSmokeErr = Join-Path $artifacts "backend-smoke.stderr.log"

New-Item -ItemType Directory -Force $artifacts | Out-Null
Remove-Item -Recurse -Force $publish, $backendDist, $notices -ErrorAction SilentlyContinue
Remove-Item -Force $backendSmokeOut, $backendSmokeErr -ErrorAction SilentlyContinue

Push-Location (Join-Path $root "apps/viewer")
try {
    npm ci --ignore-scripts --no-audit --no-fund
    npm run build
} finally { Pop-Location }

python -m pip install -e "$root/apps/backend[packaging,vision]"
dotnet restore (Join-Path $root "apps/desktop/SpatialForge.sln")
$nugetRoot = if ($env:NUGET_PACKAGES) {
    $env:NUGET_PACKAGES
} else {
    Join-Path $HOME ".nuget/packages"
}
python (Join-Path $root "scripts/collect_release_notices.py") `
    --output (Join-Path $artifacts "third-party-notices") `
    --nuget-root $nugetRoot
$pythonRoot = (& python -c "import sys; print(sys.base_prefix)").Trim()
$pythonLicense = @(
    (Join-Path $pythonRoot "LICENSE.txt"),
    (Join-Path $pythonRoot "LICENSE")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $pythonLicense) { throw "The embedded Python runtime licence file was not found." }
Copy-Item $pythonLicense (Join-Path $notices "python-runtime-LICENSE.txt")

$dotnetRoot = Split-Path -Parent (Get-Command dotnet).Source
foreach ($filename in @("LICENSE.txt", "ThirdPartyNotices.txt")) {
    $source = Join-Path $dotnetRoot $filename
    if (-not (Test-Path $source)) { throw "The .NET runtime notice $filename was not found." }
    Copy-Item $source (Join-Path $notices "dotnet-runtime-$filename")
}
python -m PyInstaller --noconfirm --clean `
    --distpath $backendDist `
    --workpath (Join-Path $artifacts "pyinstaller-work") `
    (Join-Path $root "apps/backend/packaging/spatialforge-backend.spec")

dotnet publish (Join-Path $root "apps/desktop/src/SpatialForge.Desktop/SpatialForge.Desktop.csproj") `
    -c $Configuration -r win-x64 --self-contained true `
    -p:PublishSingleFile=false -p:DebugType=None -p:DebugSymbols=false `
    -o $publish

Copy-Item -Recurse -Force (Join-Path $backendDist "spatialforge-backend") `
    (Join-Path $publish "backend")
Copy-Item -Recurse -Force (Join-Path $artifacts "third-party-notices") `
    (Join-Path $publish "third-party-notices")

$backendExe = Join-Path $publish "backend/spatialforge-backend.exe"
if (-not (Test-Path $backendExe)) { throw "Frozen backend executable was not produced." }
if (-not (Test-Path (Join-Path $publish "SpatialForge.exe"))) { throw "Desktop executable was not produced." }
if (-not (Test-Path (Join-Path $publish "viewer/index.html"))) { throw "Bundled viewer was not produced." }

$env:SPATIALFORGE_PORT = "18765"
$env:SPATIALFORGE_LAUNCH_TOKEN = "packaging-smoke-token"
$env:SPATIALFORGE_DATA_DIR = Join-Path $artifacts "smoke-data"
$env:SPATIALFORGE_PROJECTS_DIR = Join-Path $artifacts "smoke-projects"
$process = Start-Process $backendExe -PassThru `
    -RedirectStandardOutput $backendSmokeOut `
    -RedirectStandardError $backendSmokeErr
try {
    $healthy = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if ($process.HasExited) { break }
        Start-Sleep -Milliseconds 250
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:18765/api/v1/health" `
                -Headers @{ "X-SpatialForge-Token" = "packaging-smoke-token" }
            if ($health.local_only -eq $true) { $healthy = $true; break }
        } catch { }
    }
    if (-not $healthy) {
        if (Test-Path $backendSmokeOut) {
            Write-Host "Frozen backend stdout:"
            Get-Content $backendSmokeOut -Tail 120
        }
        if (Test-Path $backendSmokeErr) {
            Write-Host "Frozen backend stderr:"
            Get-Content $backendSmokeErr -Tail 120
        }
        if ($process.HasExited) {
            throw "Frozen backend health check failed; process exited with code $($process.ExitCode)."
        }
        throw "Frozen backend health check failed."
    }
} finally {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
}

Get-ChildItem $publish -Recurse -File | Get-FileHash -Algorithm SHA256 |
    Select-Object Hash, Path | ConvertTo-Json | Set-Content `
    (Join-Path $artifacts "publish-sha256.json") -Encoding utf8

if (-not $SkipInstaller) {
    $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path $iscc)) { throw "Inno Setup 6 is required to build the installer." }
    & $iscc (Join-Path $root "packaging/windows/SpatialForge.iss")
}
