from __future__ import annotations

from sqlalchemy import inspect, text

from spatialforge_backend.core.config import Settings
from spatialforge_backend.db.session import create_database_engine, initialise_database


def test_schema_contains_all_required_entities(settings: Settings) -> None:
    engine = create_database_engine(settings)
    initialise_database(engine)
    tables = set(inspect(engine).get_table_names())
    assert {
        "projects",
        "capture_devices",
        "image_assets",
        "image_quality_metrics",
        "processing_presets",
        "reconstruction_jobs",
        "pipeline_stages",
        "reconstruction_models",
        "scale_references",
        "exports",
        "hardware_profiles",
    } <= tables
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
    engine.dispose()
