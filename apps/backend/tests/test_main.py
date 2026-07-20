from __future__ import annotations

from unittest.mock import patch

from spatialforge_backend.__main__ import main
from spatialforge_backend.core.config import get_settings


def test_server_disables_access_log_to_avoid_filling_redirected_output() -> None:
    get_settings.cache_clear()
    with patch("spatialforge_backend.__main__.uvicorn.run") as run:
        main()

    assert run.call_args.kwargs["host"] == "127.0.0.1"
    assert run.call_args.kwargs["access_log"] is False
