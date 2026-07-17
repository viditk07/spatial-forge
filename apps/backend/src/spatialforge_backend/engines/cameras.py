"""Convert COLMAP camera poses into a small privacy-safe viewer artifact."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TypedDict

from spatialforge_backend.core.errors import AppError, ErrorCode


class CameraVector(TypedDict):
    x: float
    y: float
    z: float


class CameraQuaternion(CameraVector):
    w: float


class CameraPose(TypedDict):
    id: int
    position: CameraVector
    quaternion: CameraQuaternion


def _camera_error(explanation: str, technical_details: str = "") -> AppError:
    return AppError(
        ErrorCode.TOO_FEW_REGISTERED_IMAGES,
        "Camera positions are unavailable",
        explanation,
        "Review the sparse reconstruction log and retry camera export.",
        technical_details=technical_details,
        retry_safe=True,
    )


def _pose(tokens: list[str]) -> CameraPose:
    try:
        camera_id = int(tokens[0])
        qw, qx, qy, qz, tx, ty, tz = (float(value) for value in tokens[1:8])
    except (ValueError, IndexError) as error:
        raise _camera_error("COLMAP produced an unreadable camera pose.", str(error)) from error
    norm = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    values = (qw, qx, qy, qz, tx, ty, tz)
    if norm <= 1e-12 or not all(math.isfinite(value) for value in values):
        raise _camera_error("COLMAP produced an invalid camera rotation or position.")
    qw, qx, qy, qz = (value / norm for value in (qw, qx, qy, qz))
    r00 = 1 - 2 * (qy * qy + qz * qz)
    r01 = 2 * (qx * qy - qz * qw)
    r02 = 2 * (qx * qz + qy * qw)
    r10 = 2 * (qx * qy + qz * qw)
    r11 = 1 - 2 * (qx * qx + qz * qz)
    r12 = 2 * (qy * qz - qx * qw)
    r20 = 2 * (qx * qz - qy * qw)
    r21 = 2 * (qy * qz + qx * qw)
    r22 = 1 - 2 * (qx * qx + qy * qy)
    position: CameraVector = {
        "x": -(r00 * tx + r10 * ty + r20 * tz),
        "y": -(r01 * tx + r11 * ty + r21 * tz),
        "z": -(r02 * tx + r12 * ty + r22 * tz),
    }
    return {
        "id": camera_id,
        "position": position,
        # COLMAP stores world-to-camera rotation; the conjugate is camera-to-world.
        "quaternion": {"x": -qx, "y": -qy, "z": -qz, "w": qw},
    }


def parse_colmap_images(path: Path) -> list[CameraPose]:
    """Parse registered poses without retaining source image names or observations."""
    if not path.is_file():
        raise _camera_error("COLMAP did not create its registered-image text model.")
    poses: list[CameraPose] = []
    expect_pose = True
    for raw_line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            continue
        if expect_pose:
            if not stripped:
                continue
            tokens = stripped.split()
            if len(tokens) < 10:
                raise _camera_error("COLMAP produced an incomplete camera pose line.")
            poses.append(_pose(tokens))
            expect_pose = False
        else:
            # The second line contains 2D observations and is intentionally discarded.
            expect_pose = True
    if not poses:
        raise _camera_error("The sparse model contains no registered camera positions.")
    return poses


def write_camera_artifact(images_txt: Path, output: Path) -> list[CameraPose]:
    poses = parse_colmap_images(images_txt)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"version": 1, "cameras": poses}, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(output)
    return poses


def read_camera_artifact(path: Path) -> list[CameraPose]:
    if not path.is_file() or path.stat().st_size == 0:
        raise _camera_error("The camera-position artifact is missing.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != 1 or not isinstance(payload.get("cameras"), list):
            raise ValueError("unsupported camera artifact schema")
        cameras = payload["cameras"]
        if not cameras:
            raise ValueError("camera artifact is empty")
        for camera in cameras:
            _validate_artifact_pose(camera)
    except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise _camera_error("The camera-position artifact is invalid.", str(error)) from error
    return cameras


def _validate_artifact_pose(camera: object) -> None:
    if not isinstance(camera, dict) or not isinstance(camera.get("id"), int):
        raise ValueError("invalid camera identifier")
    position = camera.get("position")
    quaternion = camera.get("quaternion")
    if not isinstance(position, dict) or not isinstance(quaternion, dict):
        raise ValueError("invalid camera transform")
    values = [position[key] for key in ("x", "y", "z")]
    values.extend(quaternion[key] for key in ("x", "y", "z", "w"))
    if not all(isinstance(value, (float, int)) and math.isfinite(value) for value in values):
        raise ValueError("non-finite camera transform")
