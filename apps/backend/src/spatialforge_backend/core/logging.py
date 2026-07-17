"""Local JSONL logging with privacy-safe structured fields."""

from __future__ import annotations

import logging
from pathlib import Path

import structlog
from structlog.stdlib import BoundLogger

_LOGGER_NAME = "spatialforge"


def configure_logging(log_path: Path, level: str = "INFO") -> None:
    """Configure one process-local JSONL sink, replacing stale test or restart handlers."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(_LOGGER_NAME)
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(component: str) -> BoundLogger:
    """Return a logger with the mandatory component field."""
    return structlog.get_logger(_LOGGER_NAME).bind(component=component)
