from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from spatialforge_backend.api.app import close_app_engine, create_app
from spatialforge_backend.core.config import Settings


def _fake_colmap(path: Path) -> Path:
    path.write_text(
        """#!/usr/bin/env python3
import sys
import time
from pathlib import Path

command = sys.argv[1]
arguments = sys.argv[2:]

def value(flag):
    return Path(arguments[arguments.index(flag) + 1])

if command == "feature_extractor":
    database = value("--database_path")
    root = database.parents[1]
    if (root / "temp" / "slow").exists():
        time.sleep(30)
    database.parent.mkdir(parents=True, exist_ok=True)
    database.write_bytes(b"fake sqlite data")
elif command in {"exhaustive_matcher", "sequential_matcher"}:
    database = value("--database_path")
    if (database.parents[1] / "temp" / "fail-matching").exists():
        print("matching deliberately failed")
        raise SystemExit(7)
elif command == "mapper":
    model = value("--output_path") / "0"
    model.mkdir(parents=True, exist_ok=True)
    (model / "cameras.bin").write_bytes(b"cameras")
    (model / "images.bin").write_bytes(b"images")
    (model / "points3D.bin").write_bytes(b"points")
elif command == "model_converter":
    output = value("--output_path")
    output_type = arguments[arguments.index("--output_type") + 1]
    if output_type == "TXT":
        output.mkdir(parents=True, exist_ok=True)
        (output / "images.txt").write_text(
            "# Registered images\\n"
            "1 1 0 0 0 0 0 0 1 capture-one.jpg\\n0 0 -1\\n"
            "2 1 0 0 0 -2 0 0 1 capture-two.jpg\\n0 0 -1\\n"
        )
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "ply\\nformat ascii 1.0\\nelement vertex 3\\nproperty float x\\n"
            "property float y\\nproperty float z\\nend_header\\n"
            "0 0 0\\n1 0 0\\n0 1 0\\n"
        )
elif command == "image_undistorter":
    output = value("--output_path")
    (output / "images").mkdir(parents=True, exist_ok=True)
    (output / "images" / "frame.jpg").write_bytes(b"frame")
elif command == "patch_match_stereo":
    output = value("--workspace_path") / "stereo" / "depth_maps"
    output.mkdir(parents=True, exist_ok=True)
    (output / "frame.jpg.geometric.bin").write_bytes(b"depth")
elif command == "stereo_fusion":
    output = value("--output_path")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "ply\\nformat ascii 1.0\\nelement vertex 3\\nproperty float x\\n"
        "property float y\\nproperty float z\\nend_header\\n"
        "0 0 0\\n1 0 0\\n0 1 0\\n"
    )
elif command == "poisson_mesher":
    output = value("--output_path")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "ply\\nformat ascii 1.0\\nelement vertex 4\\nproperty float x\\n"
        "property float y\\nproperty float z\\nelement face 4\\n"
        "property list uchar int vertex_indices\\nend_header\\n"
        "0 0 0\\n1 0 0\\n0 1 0\\n0 0 1\\n"
        "3 0 2 1\\n3 0 1 3\\n3 0 3 2\\n3 1 2 3\\n"
    )
else:
    raise SystemExit(3)
print(f"fake {command} complete")
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)
    return path


@pytest.fixture
def job_app(tmp_path: Path) -> Iterator[tuple[FastAPI, Settings]]:
    executable = _fake_colmap(tmp_path / "fake-colmap")
    settings = Settings(
        data_dir=tmp_path / "app",
        projects_dir=tmp_path / "projects",
        database_url=f"sqlite:///{tmp_path / 'app' / 'jobs.db'}",
        colmap_executable=executable,
        stage_timeout_seconds=60,
        resource_preflight_enabled=False,
    )
    app = create_app(settings)
    yield app, settings
    close_app_engine(app)


def _project_with_images(client: TestClient, tmp_path: Path) -> dict[str, object]:
    project_response = client.post(
        "/api/v1/projects", json={"name": "Pipeline", "project_type": "single_room"}
    )
    assert project_response.status_code == 201
    project = project_response.json()
    paths: list[str] = []
    for index in range(3):
        path = tmp_path / f"capture-{index}.jpg"
        Image.new("RGB", (64, 64), (40 + index, 70, 100)).save(path)
        paths.append(str(path))
    imported = client.post(f"/api/v1/projects/{project['id']}/images/import", json={"paths": paths})
    assert imported.status_code == 201, imported.text
    return project


def _preset(client: TestClient, preset_type: str = "balanced_room") -> str:
    presets = client.get("/api/v1/presets").json()
    return next(item["id"] for item in presets if item["preset_type"] == preset_type)


def _wait_for_status(
    client: TestClient, job_id: str, terminal: set[str], timeout: float = 5
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in terminal:
            return job
        time.sleep(0.02)
    raise AssertionError(f"Job {job_id} did not reach {terminal}")


def test_fake_engine_pipeline_completes_with_logs(
    job_app: tuple[FastAPI, Settings], tmp_path: Path
) -> None:
    app, settings = job_app
    with TestClient(app) as client:
        project = _project_with_images(client, tmp_path)
        analysed = client.post(f"/api/v1/projects/{project['id']}/images/analyse")
        assert analysed.status_code == 200, analysed.text
        assert len(analysed.json()) == 3
        created = client.post(
            f"/api/v1/projects/{project['id']}/jobs",
            json={"preset_id": _preset(client)},
        )
        assert created.status_code == 201, created.text
        job_id = created.json()["id"]
        latest = client.get(f"/api/v1/projects/{project['id']}/jobs/latest")
        assert latest.status_code == 200
        assert latest.json()["id"] == job_id

        duplicate = client.post(
            f"/api/v1/projects/{project['id']}/jobs",
            json={"preset_id": _preset(client)},
        )
        assert duplicate.status_code == 400
        assert duplicate.json()["error"]["code"] == "PROCESS_RESOURCE_LIMIT"

        completed = _wait_for_status(client, job_id, {"completed", "failed"})
        assert completed["status"] == "completed", completed
        assert completed["progress_percent"] == 100
        assert {stage["status"] for stage in completed["stages"]} == {"completed"}
        logs = client.get(f"/api/v1/jobs/{job_id}/logs")
        assert logs.status_code == 200
        assert len(logs.json()) == 9
        assert all("fake" in entry["content"] for entry in logs.json())
        events = [
            json.loads(line)
            for line in (settings.data_dir / "logs" / "backend.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        assert any(event["event"] == "job_completed" for event in events)
        assert all("timestamp" in event and "level" in event for event in events)
        assert all(str(tmp_path / "capture-0.jpg") not in line for line in map(json.dumps, events))

        models = client.get(f"/api/v1/projects/{project['id']}/models")
        assert models.status_code == 200
        assert {model["model_type"] for model in models.json()} == {
            "sparse_point_cloud",
            "dense_point_cloud",
            "surface_mesh",
        }
        primary = next(model for model in models.json() if model["is_primary"])
        assert primary["model_type"] == "surface_mesh"
        cameras = client.get(f"/api/v1/projects/{project['id']}/cameras")
        assert cameras.status_code == 200
        assert len(cameras.json()) == 2
        assert cameras.json()[1]["position"] == {"x": 2.0, "y": -0.0, "z": -0.0}
        resources = client.get(f"/api/v1/system/resources?project_id={project['id']}")
        assert resources.status_code == 200
        assert resources.json()["registered_camera_count"] == 2
        camera_artifact = Path(str(project["root_path"])) / "previews" / "cameras.json"
        assert "capture-one.jpg" not in camera_artifact.read_text(encoding="utf-8")
        model_id = primary["id"]
        scaled = client.post(
            f"/api/v1/models/{model_id}/scale",
            json={
                "point_a": {"x": 0, "y": 0, "z": 0},
                "point_b": {"x": 1, "y": 0, "z": 0},
                "actual_distance": 2,
                "unit": "m",
            },
        )
        assert scaled.status_code == 200, scaled.text
        assert scaled.json()["calculated_scale_factor"] == 2
        exported = client.post(f"/api/v1/models/{model_id}/exports", json={"export_format": "glb"})
        assert exported.status_code == 201, exported.text
        output = Path(exported.json()["output_path"])
        assert output.read_bytes()[:4] == b"glTF"


def test_cancel_terminates_active_fake_engine(
    job_app: tuple[FastAPI, Settings], tmp_path: Path
) -> None:
    app, _ = job_app
    with TestClient(app) as client:
        project = _project_with_images(client, tmp_path)
        (Path(str(project["root_path"])) / "temp" / "slow").touch()
        created = client.post(
            f"/api/v1/projects/{project['id']}/jobs",
            json={"preset_id": _preset(client)},
        )
        job_id = created.json()["id"]
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            current = client.get(f"/api/v1/jobs/{job_id}").json()
            if current["current_stage"] == "feature_extraction":
                break
            time.sleep(0.02)
        cancelled = client.post(f"/api/v1/jobs/{job_id}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"
        assert any(stage["status"] == "cancelled" for stage in cancelled.json()["stages"])


def test_shutdown_is_recovered_as_interrupted(
    job_app: tuple[FastAPI, Settings], tmp_path: Path
) -> None:
    app, settings = job_app
    with TestClient(app) as client:
        project = _project_with_images(client, tmp_path)
        (Path(str(project["root_path"])) / "temp" / "slow").touch()
        created = client.post(
            f"/api/v1/projects/{project['id']}/jobs",
            json={"preset_id": _preset(client)},
        )
        job_id = created.json()["id"]
        _wait_for_status(client, job_id, {"processing"})

    restarted = create_app(settings)
    with TestClient(restarted) as client:
        recovered = client.get(f"/api/v1/jobs/{job_id}")
        assert recovered.status_code == 200
        assert recovered.json()["status"] == "interrupted"
        assert recovered.json()["error_code"] == "PROCESS_INTERRUPTED"
    close_app_engine(restarted)


def test_retry_reuses_verified_completed_checkpoint(
    job_app: tuple[FastAPI, Settings], tmp_path: Path
) -> None:
    app, _ = job_app
    with TestClient(app) as client:
        project = _project_with_images(client, tmp_path)
        marker = Path(str(project["root_path"])) / "temp" / "fail-matching"
        marker.touch()
        created = client.post(
            f"/api/v1/projects/{project['id']}/jobs",
            json={"preset_id": _preset(client)},
        )
        failed = _wait_for_status(client, created.json()["id"], {"failed"})
        assert failed["error_code"] == "MATCHING_FAILED"
        feature_stage = next(
            stage for stage in failed["stages"] if stage["stage_name"] == "feature_extraction"
        )
        assert feature_stage["status"] == "completed"

        marker.unlink()
        retried_response = client.post(f"/api/v1/jobs/{failed['id']}/retry")
        assert retried_response.status_code == 201, retried_response.text
        retried_id = retried_response.json()["id"]
        completed = _wait_for_status(client, retried_id, {"completed", "failed"})
        assert completed["status"] == "completed", completed
        assert completed["retry_of_job_id"] == failed["id"]
        # A copied and still-valid feature checkpoint has no new job-specific tool log.
        log_stages = {
            entry["stage"] for entry in client.get(f"/api/v1/jobs/{retried_id}/logs").json()
        }
        assert "feature_extraction" not in log_stages
