from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from pytest import MonkeyPatch
from typer.testing import CliRunner

from spatialforge_backend.cli import app
from spatialforge_backend.core.config import get_settings
from spatialforge_backend.services.presets import preset_id


def _set_cli_environment(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SPATIALFORGE_DATA_DIR", str(tmp_path / "app"))
    monkeypatch.setenv("SPATIALFORGE_PROJECTS_DIR", str(tmp_path / "projects"))
    monkeypatch.setenv("SPATIALFORGE_DATABASE_URL", f"sqlite:///{tmp_path / 'app' / 'cli.db'}")
    monkeypatch.setenv("SPATIALFORGE_RESOURCE_PREFLIGHT_ENABLED", "false")
    get_settings.cache_clear()


def _fake_sparse_colmap(path: Path) -> Path:
    path.write_text(
        """#!/usr/bin/env python3
import sys
from pathlib import Path
command = sys.argv[1]
arguments = sys.argv[2:]
def value(flag):
    return Path(arguments[arguments.index(flag) + 1])
if command == "feature_extractor":
    output = value("--database_path")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"database")
elif command in {"exhaustive_matcher", "sequential_matcher"}:
    pass
elif command == "mapper":
    output = value("--output_path") / "0"
    output.mkdir(parents=True, exist_ok=True)
    (output / "cameras.bin").write_bytes(b"cameras")
elif command == "model_converter":
    output = value("--output_path")
    output_type = arguments[arguments.index("--output_type") + 1]
    if output_type == "TXT":
        output.mkdir(parents=True, exist_ok=True)
        (output / "images.txt").write_text(
            "1 1 0 0 0 0 0 0 1 cli.jpg\\n0 0 -1\\n"
        )
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "ply\\nformat ascii 1.0\\nelement vertex 3\\nproperty float x\\n"
            "property float y\\nproperty float z\\nend_header\\n"
            "0 0 0\\n1 0 0\\n0 1 0\\n"
        )
print(command)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)
    return path


def test_cli_project_create_and_list(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    _set_cli_environment(monkeypatch, tmp_path)
    runner = CliRunner()
    created = runner.invoke(
        app,
        ["project", "create", "--name", "CLI Room", "--project-type", "single_room"],
    )
    assert created.exit_code == 0, created.output
    assert json.loads(created.output)["status"] == "draft"

    listed = runner.invoke(app, ["project", "list"])
    assert listed.exit_code == 0, listed.output
    assert json.loads(listed.output)[0]["name"] == "CLI Room"
    get_settings.cache_clear()


def test_cli_process_start_status_and_cpu_pipeline(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    _set_cli_environment(monkeypatch, tmp_path)
    executable = _fake_sparse_colmap(tmp_path / "fake-colmap")
    monkeypatch.setenv("SPATIALFORGE_COLMAP_EXECUTABLE", str(executable))
    get_settings.cache_clear()
    runner = CliRunner()
    created = runner.invoke(
        app,
        ["project", "create", "--name", "CLI Pipeline", "--project-type", "single_room"],
    )
    assert created.exit_code == 0, created.output
    project_id = json.loads(created.output)["id"]
    project_root = next((tmp_path / "projects").iterdir())
    paths: list[str] = []
    for index in range(3):
        path = tmp_path / f"cli-{index}.jpg"
        Image.new("RGB", (64, 64), (index + 10, 20, 30)).save(path)
        paths.append(str(path))
    imported = runner.invoke(app, ["images", "import", "--project-id", project_id, *paths])
    assert imported.exit_code == 0, imported.output

    started = runner.invoke(
        app,
        [
            "process",
            "start",
            "--project-id",
            project_id,
            "--preset-id",
            preset_id("cpu_compatible"),
        ],
    )
    assert started.exit_code == 0, started.output
    job = json.loads(started.output)
    assert job["status"] == "completed"
    assert [stage["status"] for stage in job["stages"]] == [
        "completed",
        "completed",
        "completed",
        "completed",
        "completed",
        "completed",
        "skipped",
        "skipped",
        "skipped",
        "skipped",
    ]
    assert (project_root / "sparse" / "sparse.ply").is_file()

    destination = tmp_path / "cli-exports"
    destination.mkdir()
    exported = runner.invoke(
        app,
        [
            "export",
            "glb",
            "--project-id",
            project_id,
            "--output-directory",
            str(destination),
        ],
    )
    assert exported.exit_code == 0, exported.output
    output = Path(json.loads(exported.output)["output_path"])
    assert output.parent == destination.resolve()
    assert output.read_bytes()[:4] == b"glTF"

    status = runner.invoke(app, ["process", "status", "--job-id", job["id"]])
    assert status.exit_code == 0, status.output
    assert json.loads(status.output)["status"] == "completed"
    get_settings.cache_clear()
