"""Versioned built-in reconstruction presets."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from spatialforge_backend.db.models import ProcessingPreset

_NAMESPACE = uuid.UUID("a1e6682c-5d14-4b30-8527-d2dc7c32c540")


@dataclass(frozen=True, slots=True)
class PresetDefinition:
    name: str
    preset_type: str
    minimum_ram_gb: float
    requires_cuda: bool
    configuration: dict[str, object]


SYSTEM_PRESETS = (
    PresetDefinition(
        "Fast Preview",
        "fast_preview",
        8,
        False,
        {
            "max_image_size": 1600,
            "max_features": 4096,
            "dense_quality": "low",
            "dense_enabled": False,
        },
    ),
    PresetDefinition(
        "Balanced Room",
        "balanced_room",
        16,
        True,
        {"max_image_size": 2400, "max_features": 8192, "dense_quality": "medium"},
    ),
    PresetDefinition(
        "High Quality",
        "high_quality",
        32,
        True,
        {"max_image_size": 0, "max_features": 16384, "dense_quality": "high"},
    ),
    PresetDefinition(
        "Exterior Building",
        "exterior_building",
        24,
        True,
        {"max_image_size": 2400, "max_features": 8192, "matcher": "sequential"},
    ),
    PresetDefinition(
        "CPU-Compatible",
        "cpu_compatible",
        16,
        False,
        {"max_image_size": 1600, "max_features": 4096, "dense_enabled": False},
    ),
)


def preset_id(preset_type: str) -> str:
    """Return the stable UUID for a system preset."""
    return str(uuid.uuid5(_NAMESPACE, preset_type))


def seed_system_presets(session: Session) -> None:
    """Seed and version built-ins while leaving user-created presets untouched."""
    existing = {
        preset.preset_type: preset
        for preset in session.scalars(
            select(ProcessingPreset).where(ProcessingPreset.is_system_preset)
        )
    }
    for definition in SYSTEM_PRESETS:
        preset = existing.get(definition.preset_type)
        configuration_json = json.dumps(definition.configuration, sort_keys=True)
        if preset is not None:
            preset.name = definition.name
            preset.configuration_json = configuration_json
            preset.minimum_ram_gb = definition.minimum_ram_gb
            preset.requires_cuda = definition.requires_cuda
            continue
        session.add(
            ProcessingPreset(
                id=preset_id(definition.preset_type),
                name=definition.name,
                preset_type=definition.preset_type,
                configuration_json=configuration_json,
                minimum_ram_gb=definition.minimum_ram_gb,
                requires_cuda=definition.requires_cuda,
                is_system_preset=True,
            )
        )
    session.commit()


def list_presets(session: Session) -> list[ProcessingPreset]:
    return list(session.scalars(select(ProcessingPreset).order_by(ProcessingPreset.minimum_ram_gb)))
