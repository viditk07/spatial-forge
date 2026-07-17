# Processing Guide

Fast Preview checks coverage with reduced resolution. Balanced Room is the default for
100–250 indoor images. High Quality increases time, memory, and storage. Exterior Building
uses ordered-scene matching. CPU-Compatible keeps resolution and concurrency conservative
and skips unsupported CUDA dense stages.

Before starting, SpatialForge checks installed and available RAM plus project-drive space.
The Processing screen reports stages and current CPU, RAM, and disk conditions; it does not
show a fake precise completion time. After sparse camera export it distinguishes photographs
included for processing from cameras actually registered by COLMAP. Cancel preserves verified
checkpoints. Retry is offered
for failed, cancelled, or restart-interrupted jobs and revalidates every reused artifact.

Project compaction removes reproducible working images, thumbnails, sparse/dense scratch
data, non-primary models, logs, and temporary files. It preserves originals, COLMAP database
metadata, the primary model, textures, and exports. Never compact during an active job.

The Export panel offers Shareable, Balanced, and Full Quality presets, GLB/OBJ/PLY formats, and
optional point-cloud and camera-position sidecars. The displayed size is a rough local estimate;
SpatialForge validates every generated file and records the actual combined size after completion.
