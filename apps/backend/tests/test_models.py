from __future__ import annotations

from pathlib import Path

import trimesh  # type: ignore[import-untyped]
from fastapi.testclient import TestClient
from sqlalchemy import select

from spatialforge_backend.db.models import (
    ProcessingPreset,
    ReconstructionJob,
    ReconstructionModel,
)

TETRAHEDRON_PLY = """ply
format ascii 1.0
element vertex 4
property float x
property float y
property float z
element face 4
property list uchar int vertex_indices
end_header
0 0 0
1 0 0
0 1 0
0 0 1
3 0 2 1
3 0 1 3
3 0 3 2
3 1 2 3
"""


def _model_fixture(client: TestClient) -> tuple[dict[str, object], ReconstructionModel]:
    response = client.post(
        "/api/v1/projects", json={"name": "Model fixture", "project_type": "single_room"}
    )
    project = response.json()
    path = Path(str(project["root_path"])) / "mesh" / "fixture.ply"
    path.write_text(TETRAHEDRON_PLY, encoding="ascii")
    factory = client.app.state.session_factory
    with factory() as session:
        preset = session.scalar(select(ProcessingPreset))
        assert preset is not None
        job = ReconstructionJob(
            project_id=str(project["id"]), preset_id=preset.id, status="completed"
        )
        session.add(job)
        session.flush()
        model = ReconstructionModel(
            project_id=str(project["id"]),
            job_id=job.id,
            model_type="textured_mesh",
            file_path=str(path),
            format="ply",
            vertex_count=4,
            face_count=4,
            texture_count=0,
            file_size_bytes=path.stat().st_size,
            is_primary=True,
        )
        session.add(model)
        session.commit()
        session.refresh(model)
        session.expunge(model)
    return project, model


def test_model_scale_crop_and_glb_export_are_persisted(client: TestClient, tmp_path: Path) -> None:
    project, model = _model_fixture(client)
    listed = client.get(f"/api/v1/projects/{project['id']}/models")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == model.id

    scaled = client.post(
        f"/api/v1/models/{model.id}/scale",
        json={
            "point_a": {"x": 0, "y": 0, "z": 0},
            "point_b": {"x": 2, "y": 0, "z": 0},
            "actual_distance": 100,
            "unit": "cm",
        },
    )
    assert scaled.status_code == 200, scaled.text
    assert scaled.json()["calculated_scale_factor"] == 0.5

    cropped = client.post(
        f"/api/v1/models/{model.id}/crop",
        json={
            "minimum": {"x": -0.1, "y": -0.1, "z": -0.1},
            "maximum": {"x": 1.1, "y": 1.1, "z": 1.1},
        },
    )
    assert cropped.status_code == 201, cropped.text
    assert cropped.json()["model_type"] == "cropped_mesh"
    assert Path(cropped.json()["file_path"]).is_file()

    root = Path(str(project["root_path"]))
    point_cloud = root / "sparse" / "points.ply"
    point_cloud.write_text(TETRAHEDRON_PLY, encoding="ascii")
    (root / "previews" / "cameras.json").write_text(
        '{"version":1,"cameras":[{"id":1,"position":{"x":0,"y":0,"z":0},'
        '"quaternion":{"x":0,"y":0,"z":0,"w":1}}]}',
        encoding="utf-8",
    )
    factory = client.app.state.session_factory
    with factory() as session:
        source = session.get(ReconstructionModel, model.id)
        assert source is not None
        session.add(
            ReconstructionModel(
                project_id=source.project_id,
                job_id=source.job_id,
                model_type="sparse_point_cloud",
                file_path=str(point_cloud),
                format="ply",
                vertex_count=4,
                face_count=4,
                texture_count=0,
                file_size_bytes=point_cloud.stat().st_size,
                is_primary=False,
            )
        )
        session.commit()

    destination = tmp_path / "chosen-export-folder"
    destination.mkdir()
    exported = client.post(
        f"/api/v1/models/{cropped.json()['id']}/exports",
        json={
            "export_format": "glb",
            "output_directory": str(destination),
            "include_point_cloud": True,
            "include_camera_positions": True,
        },
    )
    assert exported.status_code == 201, exported.text
    body = exported.json()
    output = Path(body["output_path"])
    assert output.parent == destination.resolve()
    assert body["status"] == "completed"
    assert output.read_bytes()[:4] == b"glTF"
    assert output.with_name(f"{output.stem}_point_cloud.ply").is_file()
    assert output.with_name(f"{output.stem}_cameras.json").is_file()
    assert client.get(f"/api/v1/exports/{body['id']}").json()["file_size_bytes"] > 0


def test_requested_missing_export_sidecar_removes_partial_output(client: TestClient) -> None:
    project, model = _model_fixture(client)
    response = client.post(
        f"/api/v1/models/{model.id}/exports",
        json={"export_format": "glb", "include_camera_positions": True},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "TOO_FEW_REGISTERED_IMAGES"
    assert not list((Path(str(project["root_path"])) / "exports").glob("*"))


def test_model_operations_reject_paths_outside_project(client: TestClient, tmp_path: Path) -> None:
    _, model = _model_fixture(client)
    outside = tmp_path / "outside.ply"
    outside.write_text(TETRAHEDRON_PLY, encoding="ascii")
    factory = client.app.state.session_factory
    with factory() as session:
        stored = session.get(ReconstructionModel, model.id)
        assert stored is not None
        stored.file_path = str(outside)
        session.commit()

    response = client.post(f"/api/v1/models/{model.id}/exports", json={"export_format": "glb"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PATH_INVALID"


def test_mesh_simplification_creates_valid_derived_model(client: TestClient) -> None:
    _, model = _model_fixture(client)
    sphere = trimesh.creation.icosphere(subdivisions=2)
    sphere.export(model.file_path, file_type="ply")
    factory = client.app.state.session_factory
    with factory() as session:
        stored = session.get(ReconstructionModel, model.id)
        assert stored is not None
        stored.vertex_count = len(sphere.vertices)
        stored.face_count = len(sphere.faces)
        stored.file_size_bytes = Path(stored.file_path).stat().st_size
        session.commit()

    response = client.post(f"/api/v1/models/{model.id}/simplify", json={"target_face_count": 80})
    assert response.status_code == 201, response.text
    assert 0 < response.json()["face_count"] <= 80
    assert Path(response.json()["file_path"]).is_file()
