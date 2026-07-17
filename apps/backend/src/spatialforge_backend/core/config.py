"""Runtime configuration with privacy-preserving defaults."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration, normally supplied by the desktop process."""

    model_config = SettingsConfigDict(env_prefix="SPATIALFORGE_", extra="ignore")

    host: str = Field(default="127.0.0.1", pattern=r"^127\.0\.0\.1$")
    port: int = Field(default=8765, ge=1024, le=65535)
    data_dir: Path = Field(default_factory=lambda: Path.home() / "SpatialForge")
    projects_dir: Path = Field(default_factory=lambda: Path.home() / "SpatialForgeProjects")
    database_url: str | None = None
    launch_token: str | None = None
    log_level: str = "INFO"
    colmap_executable: Path = Path("colmap")
    max_concurrent_jobs: int = Field(default=1, ge=1, le=4)
    stage_timeout_seconds: float = Field(default=86_400, ge=1)
    resource_preflight_enabled: bool = True

    @property
    def resolved_database_url(self) -> str:
        """Return the configured database URL or the local application database."""
        return self.database_url or f"sqlite:///{self.data_dir / 'spatialforge.db'}"


@lru_cache
def get_settings() -> Settings:
    """Return process settings."""
    return Settings()
