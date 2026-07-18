# Windows Packaging

Run `./scripts/package-windows.ps1` from PowerShell on Windows. It builds the viewer,
freezes the Python backend as a one-folder executable, self-contained-publishes WPF for
`win-x64`, copies the backend under the desktop output, performs an authenticated loopback
health check, writes SHA-256 hashes, and invokes Inno Setup 6.
Before freezing, it restores the desktop solution so NuGet package notices are present, resolves
the full installed Python runtime dependency closure, validates its licence metadata, and also
validates Three.js and direct NuGet runtime packages. It copies all available licence/notice files
into the published application; missing required metadata or declared notices fail the package
build.
The script additionally requires and copies the exact Python runtime licence plus the .NET SDK
licence and third-party notices used for the self-contained publish.
Native command failures are treated as packaging failures. If the frozen-backend health smoke fails,
the script prints the captured backend stdout and stderr before exiting.

The release job must inspect PyInstaller warnings, scan outputs, start the installed app,
verify the privacy prompt, create a synthetic project, open the embedded viewer, and
uninstall cleanly. COLMAP, OpenMVS, and Blender binaries are not included until the exact
binary distribution and transitive licences are approved.
