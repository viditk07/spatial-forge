from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from spatialforge_backend.core.errors import AppError, ErrorCode
from spatialforge_backend.engines.colmap import (
    ColmapCommands,
    ColmapWorkspace,
    run_process,
    verify_stage_artifacts,
)


def _workspace(tmp_path: Path) -> ColmapWorkspace:
    root = tmp_path / "project with spaces"
    for child in ("database", "working_images", "sparse", "dense", "mesh", "logs"):
        (root / child).mkdir(parents=True, exist_ok=True)
    return ColmapWorkspace(Path("colmap"), root)


def test_commands_preserve_paths_as_single_arguments(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    command = ColmapCommands(workspace).feature_extraction(1600, 4096)
    assert command[0:2] == ["colmap", "feature_extractor"]
    assert command[command.index("--image_path") + 1] == str(workspace.images)
    assert len([part for part in command if "project with spaces" in part]) == 2


def test_command_rejects_output_path_escape(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    with pytest.raises(AppError) as raised:
        ColmapCommands(workspace).model_converter(
            workspace.sparse / "0", tmp_path / "escaped.ply", "PLY"
        )
    assert raised.value.code is ErrorCode.PATH_INVALID


def test_zero_exit_without_artifact_is_rejected(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    with pytest.raises(AppError):
        verify_stage_artifacts("feature_extraction", workspace)
    workspace.database.write_bytes(b"sqlite")
    verify_stage_artifacts("feature_extraction", workspace)


def test_invalid_ply_artifact_is_rejected(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    output = workspace.sparse / "sparse.ply"
    output.write_bytes(b"not a point cloud")
    with pytest.raises(AppError) as raised:
        verify_stage_artifacts("sparse_export", workspace)
    assert raised.value.code is ErrorCode.EMPTY_POINT_CLOUD

    output.write_bytes(b"ply\nvalid fixture")
    verify_stage_artifacts("sparse_export", workspace)


def test_fake_engine_output_is_logged(tmp_path: Path) -> None:
    script = tmp_path / "fake-colmap"
    script.write_text("#!/bin/sh\nprintf 'fake stage complete\\n'\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    log = tmp_path / "stage.log"
    result = asyncio.run(run_process([os.fspath(script), "feature_extractor"], log, 5))
    assert result.exit_code == 0
    assert log.read_text(encoding="utf-8") == "fake stage complete\n"
