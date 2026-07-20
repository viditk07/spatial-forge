from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from spatialforge_backend.services.paths import PROJECT_DIRECTORIES


def test_launch_token_is_required(tmp_path: Path) -> None:
    from spatialforge_backend.api.app import close_app_engine, create_app
    from spatialforge_backend.core.config import Settings

    app = create_app(
        Settings(
            data_dir=tmp_path / "app",
            projects_dir=tmp_path / "projects",
            database_url=f"sqlite:///{tmp_path / 'app' / 'token.db'}",
            launch_token="test-launch-token",  # noqa: S106 - non-secret fixture
        )
    )
    with TestClient(app) as token_client:
        assert token_client.get("/api/v1/health").status_code == 401
        assert (
            token_client.get(
                "/api/v1/health", headers={"X-SpatialForge-Token": "test-launch-token"}
            ).status_code
            == 200
        )
    close_app_engine(app)


def test_health_reports_local_only(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.2.1", "local_only": True}


def test_create_and_retrieve_project(client: TestClient) -> None:
    created = client.post(
        "/api/v1/projects",
        json={"name": "Dining Room", "project_type": "single_room", "notes": "fixture"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    project_root = Path(body["root_path"])
    assert project_root.is_dir()
    assert all((project_root / child).is_dir() for child in PROJECT_DIRECTORIES)
    manifest = json.loads((project_root / "project.json").read_text(encoding="utf-8"))
    assert manifest["id"] == body["id"]

    fetched = client.get(f"/api/v1/projects/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Dining Room"
    assert [project["id"] for project in client.get("/api/v1/projects").json()] == [body["id"]]
    opened = client.post(f"/api/v1/projects/{body['id']}/open")
    assert opened.status_code == 200
    assert opened.json()["last_opened_at"] is not None


def test_create_and_delete_project_in_selected_directory(
    client: TestClient, tmp_path: Path
) -> None:
    selected = tmp_path / "chosen-project-parent"
    selected.mkdir()
    created = client.post(
        "/api/v1/projects",
        json={
            "name": "Custom location",
            "project_type": "single_room",
            "project_directory": str(selected),
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    root = Path(body["root_path"])
    assert root.parent == selected.resolve()

    deleted = client.delete(f"/api/v1/projects/{body['id']}?confirmation=Custom%20location")
    assert deleted.status_code == 204, deleted.text
    assert not root.exists()


def test_invalid_project_type_is_rejected_without_files(client: TestClient) -> None:
    response = client.post("/api/v1/projects", json={"name": "Bad", "project_type": "not_a_type"})
    assert response.status_code == 422


def test_missing_project_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
