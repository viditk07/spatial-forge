# Installation

SpatialForge targets 64-bit Windows 11. Use 16 GB RAM as the practical minimum,
32 GB for Balanced or High Quality work, an SSD, and enough free space for roughly
18 times the imported JPEG size plus a 2 GiB safety reserve.

1. Run the signed `SpatialForge-<version>-win-x64.exe` installer.
2. Keep the default per-user installation folder unless local policy requires another.
3. On first launch, read and accept the local-processing privacy notice.
4. Open Hardware to review CPU, RAM, GPU, CUDA, and dependency detection.
5. Install or select a compatible COLMAP executable before reconstruction. COLMAP is
   not bundled until its complete binary redistribution terms have been verified.

The application and backend need no internet connection. WebView2 Evergreen Runtime is
normally part of Windows 11; repair that runtime if Model Review is blank. NVIDIA CUDA is
recommended for COLMAP dense stereo. CPU-only systems can use sparse reconstruction and
the conservative CPU-Compatible preset; the UI must not claim CUDA-only stages will work.

Uninstalling SpatialForge does not delete projects under Documents. Delete those projects
explicitly from the application or remove them manually after verifying backups.
