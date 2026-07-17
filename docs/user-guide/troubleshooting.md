# Troubleshooting

## Too few registered images

Add sharper images with stronger overlap, especially around blank walls and corners. Remove
mixed-lens frames and retry from the sparse stage.

## Blur, blank walls, or low feature density

Exclude severely blurred frames. Recapture featureless surfaces with temporary markers and
soft, consistent lighting. Feature warnings are advisory; inspect the photographs yourself.

## Multiple focal lengths

Keep only the main-camera sequence when possible. Mixing ultrawide and digitally zoomed
frames can split camera groups or weaken calibration.

## Dense processing unavailable

Confirm that the installed COLMAP build supports CUDA, the NVIDIA driver is compatible, and
the GPU has enough memory. Otherwise select CPU-Compatible and use the sparse result.

## Insufficient storage or memory

Close other applications, free SSD space, compact old projects, or choose a lower preset.
SpatialForge intentionally refuses unsafe starts.

## Empty mesh or texture failure

Inspect the dense point cloud first. Improve overlap and surface texture, then retry. Texture
generation is engine-dependent and may be unavailable in the current COLMAP-only beta.

Use Settings → Create diagnostic report when requesting help. The JSON report excludes
photographs, models, GPS, and imported source paths by default.
