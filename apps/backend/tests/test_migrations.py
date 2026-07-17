from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _config(database: Path) -> Config:
    backend_root = Path(__file__).parents[1]
    config = Config(backend_root / "alembic.ini")
    config.set_main_option("script_location", str(backend_root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    return config


def test_initial_migration_upgrade_and_downgrade(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    config = _config(database)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    assert "projects" in inspect(engine).get_table_names()
    assert "alembic_version" in inspect(engine).get_table_names()
    engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(f"sqlite:///{database}")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
