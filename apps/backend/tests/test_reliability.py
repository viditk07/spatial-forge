from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from spatialforge_backend.db.models import (
    ProcessingPreset,
    ReconstructionJob,
    ReconstructionModel,
)
from spatialforge_backend.services import reliability
from spatialforge_backend.services.hardware import HardwareSnapshot


def _project(client: TestClient, name: str = "Reliability") -> dict[str, object]:
    response = client.post("/api/v1/projects", json={"name": name, "project_type": "single_room"})
    assert response.status_code == 201
    return response.json()


def test_storage_compaction_diagnostics_and_confirmed_deletion(client: TestClient) -> None:
    project = _project(client)
    root = Path(str(project["root_path"]))
    preserved = [
        root / "originals" / "capture.jpg",
        root / "database" / "colmap.db",
        root / "exports" / "room.glb",
        root / "previews" / "cameras.json",
    ]
    temporary = [
        root / "working_images" / "capture.jpg",
        root / "dense" / "fused.ply",
        root / "temp" / "scratch.bin",
    ]
    for path in [*preserved, *temporary]:
        path.write_bytes(b"local fixture")

    storage = client.get(f"/api/v1/system/storage?project_id={project['id']}")
    assert storage.status_code == 200
    assert storage.json()["disk_free_bytes"] > 0
    assert storage.json()["project_size_bytes"] >= sum(path.stat().st_size for path in preserved)
    resources = client.get(f"/api/v1/system/resources?project_id={project['id']}")
    assert resources.status_code == 200
    assert resources.json()["memory_available_mb"] > 0
    assert resources.json()["disk_free_bytes"] > 0

    compacted = client.post(f"/api/v1/projects/{project['id']}/compact")
    assert compacted.status_code == 200, compacted.text
    assert compacted.json()["bytes_reclaimed"] > 0
    assert all(path.is_file() for path in preserved)
    assert all(not path.exists() for path in temporary)

    diagnostic = client.post(f"/api/v1/projects/{project['id']}/diagnostics")
    assert diagnostic.status_code == 200, diagnostic.text
    report_path = Path(diagnostic.json()["output_path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert all(value is False for value in report["privacy"].values())
    serialized = json.dumps(report)
    assert "capture.jpg" not in serialized
    assert str(root) not in serialized

    rejected = client.delete(f"/api/v1/projects/{project['id']}?confirmation=wrong-name")
    assert rejected.status_code == 400
    assert root.is_dir()
    deleted = client.delete(f"/api/v1/projects/{project['id']}?confirmation=Reliability")
    assert deleted.status_code == 204, deleted.text
    assert not root.exists()
    assert client.get(f"/api/v1/projects/{project['id']}").status_code == 404


def test_project_archive_updates_manifest(client: TestClient) -> None:
    project = _project(client, "Archive me")
    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"name": "Archived room", "notes": "kept locally", "archived": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "archived"
    root = Path(str(project["root_path"]))
    manifest = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "Archived room"
    assert manifest["status"] == "archived"


def test_compaction_preserves_sparse_primary_model(client: TestClient) -> None:
    project = _project(client, "Sparse primary")
    root = Path(str(project["root_path"]))
    primary_path = root / "sparse" / "primary.ply"
    disposable_path = root / "sparse" / "intermediate.bin"
    primary_path.write_bytes(b"ply\nprimary")
    disposable_path.write_bytes(b"temporary")
    factory = client.app.state.session_factory
    with factory() as session:
        preset = session.scalar(select(ProcessingPreset))
        assert preset is not None
        job = ReconstructionJob(
            project_id=str(project["id"]), preset_id=preset.id, status="completed"
        )
        session.add(job)
        session.flush()
        session.add(
            ReconstructionModel(
                project_id=str(project["id"]),
                job_id=job.id,
                model_type="sparse_point_cloud",
                file_path=str(primary_path),
                format="ply",
                vertex_count=1,
                face_count=0,
                texture_count=0,
                file_size_bytes=primary_path.stat().st_size,
                is_primary=True,
            )
        )
        session.commit()

    compacted = client.post(f"/api/v1/projects/{project['id']}/compact")

    assert compacted.status_code == 200, compacted.text
    assert primary_path.is_file()
    assert not disposable_path.exists()


def test_job_preflight_rejects_insufficient_storage(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _project(client, "No disk")
    paths = []
    for index in range(3):
        path = tmp_path / f"preflight-{index}.jpg"
        Image.new("RGB", (32, 32), (20 + index, 40, 60)).save(path)
        paths.append(str(path))
    imported = client.post(f"/api/v1/projects/{project['id']}/images/import", json={"paths": paths})
    assert imported.status_code == 201
    preset = next(
        item
        for item in client.get("/api/v1/presets").json()
        if item["preset_type"] == "fast_preview"
    )
    monkeypatch.setattr(
        reliability.shutil,
        "disk_usage",
        lambda _: SimpleNamespace(total=10 * 1024**3, used=10 * 1024**3 - 1, free=1),
    )

    response = client.post(
        f"/api/v1/projects/{project['id']}/jobs", json={"preset_id": preset["id"]}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INSUFFICIENT_STORAGE"


def test_job_preflight_rejects_cuda_preset_without_cuda(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _project(client, "No CUDA")
    preset = next(
        item
        for item in client.get("/api/v1/presets").json()
        if item["preset_type"] == "balanced_room"
    )
    monkeypatch.setattr(
        reliability,
        "capture_hardware",
        lambda: HardwareSnapshot(
            operating_system="Windows 11",
            cpu_model="Fixture CPU",
            logical_core_count=8,
            memory_total_mb=32768,
            memory_available_mb=24576,
            gpu_model=None,
            gpu_memory_mb=None,
            cuda_available=False,
            opengl_version=None,
            recommended_preset="cpu_compatible",
        ),
    )

    response = client.post(
        f"/api/v1/projects/{project['id']}/jobs", json={"preset_id": preset["id"]}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CUDA_UNAVAILABLE"
