from __future__ import annotations

import json
from pathlib import Path

import pytest

from spatialforge_backend.core.errors import AppError
from spatialforge_backend.engines.cameras import (
    parse_colmap_images,
    read_camera_artifact,
    write_camera_artifact,
)


def test_colmap_camera_pose_is_converted_without_image_metadata(tmp_path: Path) -> None:
    images = tmp_path / "images.txt"
    images.write_text(
        "# IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME\n"
        "7 1 0 0 0 -2 -3 -4 1 private-room.jpg\n"
        "10 20 -1 30 40 -1\n",
        encoding="utf-8",
    )

    poses = parse_colmap_images(images)
    assert poses == [
        {
            "id": 7,
            "position": {"x": 2.0, "y": 3.0, "z": 4.0},
            "quaternion": {"x": -0.0, "y": -0.0, "z": -0.0, "w": 1.0},
        }
    ]
    artifact = tmp_path / "previews" / "cameras.json"
    write_camera_artifact(images, artifact)
    assert read_camera_artifact(artifact) == poses
    assert "private-room.jpg" not in artifact.read_text(encoding="utf-8")


def test_invalid_camera_artifact_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "cameras.json"
    artifact.write_text(json.dumps({"version": 1, "cameras": []}), encoding="utf-8")
    with pytest.raises(AppError):
        read_camera_artifact(artifact)
