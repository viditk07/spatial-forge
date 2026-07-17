from __future__ import annotations

from pathlib import Path

import pytest

from spatialforge_backend.core.errors import AppError, ErrorCode
from spatialforge_backend.services.paths import ensure_within


def test_contained_path_is_resolved(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    assert ensure_within(root / "safe", root) == (root / "safe").resolve()


@pytest.mark.parametrize("suffix", ["../escape", "safe/../../escape"])
def test_path_traversal_is_rejected(tmp_path: Path, suffix: str) -> None:
    with pytest.raises(AppError) as raised:
        ensure_within(tmp_path / "projects" / suffix, tmp_path / "projects")
    assert raised.value.code is ErrorCode.PATH_INVALID


def test_similar_prefix_is_not_considered_contained(tmp_path: Path) -> None:
    with pytest.raises(AppError):
        ensure_within(tmp_path / "projects-other", tmp_path / "projects")
