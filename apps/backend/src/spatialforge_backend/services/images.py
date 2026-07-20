"""Immutable image import and local quality analysis."""

from __future__ import annotations

import hashlib
import importlib
import math
import shutil
import uuid
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, cast

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from spatialforge_backend.core.errors import AppError, ErrorCode
from spatialforge_backend.db.models import (
    CaptureDevice,
    ImageAsset,
    ImageQualityMetric,
    Project,
    ProjectStatus,
)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
MINIMUM_DIMENSION = 1600
_HASH_SIZE = 8


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rational(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _exif_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def _gps_coordinate(value: Any, reference: Any) -> float | None:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        return None
    parts = [_rational(part) for part in value]
    if any(part is None for part in parts):
        return None
    degrees, minutes, seconds = parts
    assert degrees is not None and minutes is not None and seconds is not None
    coordinate = degrees + minutes / 60 + seconds / 3600
    direction = str(reference).upper()
    if direction in {"S", "W"}:
        coordinate = -coordinate
    if direction not in {"N", "S", "E", "W"} or not math.isfinite(coordinate):
        return None
    return coordinate


def _metadata(image: Image.Image) -> dict[str, Any]:
    exif = image.getexif()
    try:
        gps = exif.get_ifd(34853)
    except (AttributeError, KeyError, TypeError, ValueError):
        gps = {}
    return {
        "captured_at": _exif_datetime(exif.get(36867) or exif.get(306)),
        "focal_length_mm": _rational(exif.get(37386)),
        "focal_length_35mm": _rational(exif.get(41989)),
        "aperture": _rational(exif.get(33437)),
        "exposure_time": _rational(exif.get(33434)),
        "iso": int(exif[34855]) if exif.get(34855) is not None else None,
        "orientation": int(exif[274]) if exif.get(274) is not None else None,
        "latitude": _gps_coordinate(gps.get(2), gps.get(1)),
        "longitude": _gps_coordinate(gps.get(4), gps.get(3)),
    }


def _device_metadata(image: Image.Image) -> dict[str, str | None]:
    exif = image.getexif()

    def text(tag: int) -> str | None:
        value = exif.get(tag)
        return str(value).strip()[:200] if value is not None and str(value).strip() else None

    model = text(272)
    return {
        "manufacturer": text(271),
        "model": model,
        "camera_model": model,
        "lens_model": text(42036),
    }


def _copy_working(source: Path, destination: Path, remove_gps: bool) -> None:
    if not remove_gps:
        shutil.copy2(source, destination)
        return
    with Image.open(source) as image:
        save_kwargs: dict[str, Any] = {}
        if image.format == "JPEG":
            save_kwargs = {"format": "JPEG", "quality": 95, "subsampling": 0}
        elif image.format:
            save_kwargs = {"format": image.format}
        image.save(destination, **save_kwargs)


def _thumbnail(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        image.thumbnail((512, 512), Image.Resampling.LANCZOS)
        image.convert("RGB").save(destination, "JPEG", quality=82, optimize=True)


def _perceptual_hash(image: Image.Image) -> int:
    resized = image.convert("L").resize((_HASH_SIZE, _HASH_SIZE), Image.Resampling.LANCZOS)
    values = list(cast(Iterable[int], resized.get_flattened_data()))
    centre = median(values)
    result = 0
    for index, value in enumerate(values):
        if value >= centre:
            result |= 1 << index
    return result


def _hash_similarity(left: int, right: int) -> float:
    distance = (left ^ right).bit_count()
    return 1.0 - distance / (_HASH_SIZE * _HASH_SIZE)


def _analyse_pixels(image: Image.Image) -> tuple[float, float, str, int]:
    grayscale = image.convert("L")
    grayscale.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    stats = ImageStat.Stat(grayscale)
    brightness = float(stats.mean[0]) / 255.0
    histogram = grayscale.histogram()
    pixels = max(1, sum(histogram))
    dark = sum(histogram[:8]) / pixels
    bright = sum(histogram[248:]) / pixels
    occupied = [index for index, count in enumerate(histogram) if count]
    dynamic_range = (occupied[-1] - occupied[0]) / 255 if occupied else 0
    if dark >= 0.5 or brightness < 0.12:
        exposure = "severe_underexposure"
    elif bright >= 0.5 or brightness > 0.92:
        exposure = "severe_overexposure"
    elif bright >= 0.08:
        exposure = "clipped_highlights"
    elif dynamic_range < 0.15:
        exposure = "low_dynamic_range"
    else:
        exposure = "good"

    opencv_metrics = _opencv_quality_metrics(grayscale)
    if opencv_metrics is not None:
        blur_score, feature_estimate = opencv_metrics
    else:
        edges = grayscale.filter(ImageFilter.FIND_EDGES)
        edge_variance = float(ImageStat.Stat(edges).var[0])
        megapixels = max(0.1, image.width * image.height / 1_000_000)
        blur_score = edge_variance * math.sqrt(megapixels)
        # Fallback proxy used only when the optional local OpenCV package is unavailable.
        feature_estimate = sum(
            count for level, count in enumerate(edges.histogram()) if level >= 32
        )
    return blur_score, brightness, exposure, feature_estimate


def _opencv_quality_metrics(grayscale: Image.Image) -> tuple[float, int] | None:
    """Return a resolution-normalised combined focus score and real ORB keypoint count."""
    try:
        cv2: Any = importlib.import_module("cv2")
        numpy: Any = importlib.import_module("numpy")
    except ImportError:
        return None
    pixels = numpy.asarray(grayscale, dtype=numpy.uint8)
    laplacian_variance = float(cv2.Laplacian(pixels, cv2.CV_64F).var())
    gradient_x = cv2.Sobel(pixels, cv2.CV_64F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(pixels, cv2.CV_64F, 0, 1, ksize=3)
    tenengrad = float(numpy.sqrt(numpy.mean(gradient_x**2 + gradient_y**2)))
    # Every image is analysed at a maximum 1600px edge, making the calibrated 100-point
    # review threshold comparable across smartphone resolutions without upscaling small inputs.
    blur_score = 0.7 * laplacian_variance + 0.3 * tenengrad
    detector = cv2.ORB_create(nfeatures=5000, fastThreshold=12)
    keypoints = detector.detect(pixels, None)
    return blur_score, len(keypoints)


class ImageService:
    """Imports and analyses photographs one at a time to bound memory use."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def import_files(
        self, project: Project, source_paths: list[Path], *, remove_gps: bool = False
    ) -> list[ImageAsset]:
        if not source_paths:
            raise AppError(
                ErrorCode.INSUFFICIENT_IMAGES,
                "No photographs selected",
                "At least one supported photograph is required for import.",
                "Select JPEG, PNG, TIFF, or WebP photographs.",
            )
        root = Path(project.root_path).resolve()
        imported: list[ImageAsset] = []
        created_paths: list[Path] = []
        project.status = ProjectStatus.IMPORTING.value
        try:
            for source_path in source_paths:
                source = source_path.expanduser().resolve(strict=True)
                if not source.is_file() or source.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    raise AppError(
                        ErrorCode.UNSUPPORTED_IMAGE_FORMAT,
                        "Unsupported photograph",
                        "One selected file is not a supported image format.",
                        "Use JPEG, PNG, TIFF, or WebP files.",
                        technical_details=source.suffix.lower(),
                    )
                try:
                    with Image.open(source) as probe:
                        probe.verify()
                    with Image.open(source) as image:
                        width, height = image.size
                        mime_type = Image.MIME.get(image.format or "", "application/octet-stream")
                        metadata = _metadata(image)
                        device_metadata = _device_metadata(image)
                except (UnidentifiedImageError, OSError) as error:
                    raise AppError(
                        ErrorCode.UNSUPPORTED_IMAGE_FORMAT,
                        "Unreadable photograph",
                        "The selected file is damaged or is not a readable photograph.",
                        "Remove the file from the selection or export it as JPEG.",
                        technical_details=type(error).__name__,
                    ) from error
                image_id = str(uuid.uuid4())
                safe_name = f"{image_id}{source.suffix.lower()}"
                original = root / "originals" / safe_name
                working = root / "working_images" / safe_name
                thumbnail = root / "thumbnails" / f"{image_id}.jpg"
                shutil.copy2(source, original)
                created_paths.append(original)
                checksum = _sha256(original)
                _copy_working(source, working, remove_gps)
                created_paths.append(working)
                _thumbnail(working, thumbnail)
                created_paths.append(thumbnail)
                asset = ImageAsset(
                    id=image_id,
                    project_id=project.id,
                    original_filename=source.name,
                    original_path=str(original),
                    working_path=str(working),
                    thumbnail_path=str(thumbnail),
                    checksum_sha256=checksum,
                    width=width,
                    height=height,
                    file_size_bytes=original.stat().st_size,
                    mime_type=mime_type,
                    quality_status="review",
                    included=True,
                    **metadata,
                )
                self.session.add(asset)
                imported.append(asset)
                if project.capture_device_id is None and any(device_metadata.values()):
                    device = self.session.scalar(
                        select(CaptureDevice).where(
                            CaptureDevice.manufacturer == device_metadata["manufacturer"],
                            CaptureDevice.model == device_metadata["model"],
                            CaptureDevice.camera_model == device_metadata["camera_model"],
                            CaptureDevice.lens_model == device_metadata["lens_model"],
                        )
                    )
                    if device is None:
                        device = CaptureDevice(**device_metadata)
                        self.session.add(device)
                        self.session.flush()
                    project.capture_device_id = device.id
            project.status = ProjectStatus.READY.value
            self.session.commit()
        except Exception:
            self.session.rollback()
            for path in created_paths:
                path.unlink(missing_ok=True)
            raise
        return imported

    def list_images(self, project_id: str) -> list[ImageAsset]:
        return list(
            self.session.scalars(
                select(ImageAsset)
                .where(ImageAsset.project_id == project_id)
                .order_by(ImageAsset.imported_at, ImageAsset.id)
            )
        )

    def analyse(self, project: Project) -> list[ImageAsset]:
        assets = self.list_images(project.id)
        if not assets:
            raise AppError(
                ErrorCode.INSUFFICIENT_IMAGES,
                "No photographs to analyse",
                "This project does not contain any imported photographs.",
                "Import photographs before starting quality analysis.",
            )
        project.status = ProjectStatus.VALIDATING.value
        hashes: dict[str, int] = {}
        exact_groups: dict[str, list[ImageAsset]] = defaultdict(list)
        focal_lengths = {
            round(asset.focal_length_35mm or asset.focal_length_mm or 0, 1)
            for asset in assets
            if asset.focal_length_35mm or asset.focal_length_mm
        }
        dimensions = {(asset.width, asset.height) for asset in assets}
        for asset in assets:
            with Image.open(asset.working_path) as image:
                blur, brightness, exposure, features = _analyse_pixels(image)
                hashes[asset.id] = _perceptual_hash(image)
            exact_groups[asset.checksum_sha256].append(asset)
            resolution = "low" if min(asset.width, asset.height) < MINIMUM_DIMENSION else "good"
            lens = "mixed_focal_lengths" if len(focal_lengths) > 1 else "consistent"
            if len(dimensions) > 1 and lens == "consistent":
                lens = "dimensions_changed"
            warnings = [
                exposure != "good",
                resolution != "good",
                blur < 100,
                features < 500,
                lens != "consistent",
            ]
            recommendation = "review" if any(warnings) else "good"
            metric = asset.quality_metric or ImageQualityMetric(
                image_id=asset.id, recommendation=recommendation
            )
            metric.blur_score = blur
            metric.brightness_score = brightness
            metric.exposure_status = exposure
            metric.feature_count_estimate = features
            metric.metadata_score = (
                sum(
                    value is not None
                    for value in (
                        asset.captured_at,
                        asset.focal_length_mm,
                        asset.exposure_time,
                        asset.iso,
                    )
                )
                / 4
            )
            metric.resolution_status = resolution
            metric.lens_consistency_status = lens
            metric.recommendation = recommendation
            asset.quality_metric = metric
            self.session.add(metric)
            asset.quality_status = recommendation

        grouped: set[str] = set()
        for members in exact_groups.values():
            if len(members) > 1:
                group_id = str(uuid.uuid4())
                for asset in members:
                    assert asset.quality_metric is not None
                    asset.quality_metric.duplicate_group_id = group_id
                    asset.quality_metric.duplicate_similarity = 1.0
                    asset.quality_metric.recommendation = "exclude_recommended"
                    asset.quality_status = "exclude_recommended"
                    grouped.add(asset.id)
        candidates = [asset for asset in assets if asset.id not in grouped]
        parents = {asset.id: asset.id for asset in candidates}
        similarities: dict[tuple[str, str], float] = {}

        def find(image_id: str) -> str:
            while parents[image_id] != image_id:
                parents[image_id] = parents[parents[image_id]]
                image_id = parents[image_id]
            return image_id

        def union(left_id: str, right_id: str) -> None:
            left_root = find(left_id)
            right_root = find(right_id)
            if left_root != right_root:
                parents[right_root] = left_root

        for index, left in enumerate(candidates):
            for right in candidates[index + 1 :]:
                similarity = _hash_similarity(hashes[left.id], hashes[right.id])
                similarities[(left.id, right.id)] = similarity
                if similarity >= 0.94:
                    union(left.id, right.id)

        near_groups: dict[str, list[ImageAsset]] = defaultdict(list)
        for asset in candidates:
            near_groups[find(asset.id)].append(asset)
        for members in near_groups.values():
            if len(members) < 2:
                continue
            group_id = str(uuid.uuid4())
            for asset in members:
                assert asset.quality_metric is not None
                member_similarities = [
                    similarity
                    for pair, similarity in similarities.items()
                    if asset.id in pair and similarity >= 0.94
                ]
                asset.quality_metric.duplicate_group_id = group_id
                asset.quality_metric.duplicate_similarity = max(member_similarities, default=0.94)
                asset.quality_metric.recommendation = "review"
                asset.quality_status = "review"
        project.status = ProjectStatus.READY.value
        self.session.commit()
        return assets

    def set_included(self, image_id: str, included: bool) -> ImageAsset | None:
        """Update review inclusion without deleting any file."""
        asset = self.session.get(ImageAsset, image_id)
        if asset is None:
            return None
        asset.included = included
        self.session.commit()
        return asset
