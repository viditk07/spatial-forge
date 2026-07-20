"""Run the loopback API."""

import uvicorn

from spatialforge_backend.core.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "spatialforge_backend.api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
