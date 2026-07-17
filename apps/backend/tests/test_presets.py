from __future__ import annotations

import json

from spatialforge_backend.core.config import Settings
from spatialforge_backend.db.session import (
    create_database_engine,
    initialise_database,
    session_factory,
)
from spatialforge_backend.services.presets import list_presets, seed_system_presets


def test_system_preset_seed_is_complete_and_idempotent(settings: Settings) -> None:
    engine = create_database_engine(settings)
    initialise_database(engine)
    factory = session_factory(engine)
    with factory() as session:
        seed_system_presets(session)
        seed_system_presets(session)
        presets = list_presets(session)
        assert {preset.preset_type for preset in presets} == {
            "fast_preview",
            "balanced_room",
            "high_quality",
            "exterior_building",
            "cpu_compatible",
        }
        cpu = next(p for p in presets if p.preset_type == "cpu_compatible")
        preview = next(p for p in presets if p.preset_type == "fast_preview")
        assert cpu.requires_cuda is False
        assert json.loads(preview.configuration_json)["dense_enabled"] is False

        preview.configuration_json = "{}"
        preview.requires_cuda = True
        session.commit()
        seed_system_presets(session)
        session.refresh(preview)
        assert json.loads(preview.configuration_json)["dense_enabled"] is False
        assert preview.requires_cuda is False
    engine.dispose()
