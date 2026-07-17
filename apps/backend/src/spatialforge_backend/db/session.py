"""Database engine and request session lifecycle."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker

from spatialforge_backend.core.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    """Create a SQLite engine with required integrity settings."""
    if settings.resolved_database_url.startswith("sqlite:///"):
        database_path = settings.resolved_database_url.removeprefix("sqlite:///")
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.resolved_database_url, future=True)

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


def initialise_database(engine: Engine) -> None:
    """Upgrade the local database through bundled, versioned Alembic migrations."""
    package_root = Path(__file__).resolve().parents[1]
    script_location = package_root / "migrations"
    if not script_location.is_dir():
        script_location = package_root.parents[1] / "migrations"
    if not script_location.is_dir():
        raise RuntimeError("Bundled database migrations are missing")
    config = Config()
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("sqlalchemy.url", str(engine.url))
    tables = set(inspect(engine).get_table_names())
    if "projects" in tables and "alembic_version" not in tables:
        # Pre-0.1 development builds used metadata.create_all at the same schema head.
        command.stamp(config, "head")
    else:
        command.upgrade(config, "head")


def session_factory(engine: Engine | Connection) -> sessionmaker[Session]:
    """Create non-expiring sessions suitable for service boundaries."""
    return sessionmaker(engine, expire_on_commit=False)


def session_dependency(factory: sessionmaker[Session]) -> Generator[Session]:
    """Yield one transactional API request session."""
    with factory() as session:
        yield session
