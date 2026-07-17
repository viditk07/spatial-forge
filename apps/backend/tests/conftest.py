from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from spatialforge_backend.api.app import close_app_engine, create_app
from spatialforge_backend.core.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "app",
        projects_dir=tmp_path / "projects",
        database_url=f"sqlite:///{tmp_path / 'app' / 'test.db'}",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
    close_app_engine(app)
