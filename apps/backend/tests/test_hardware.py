from __future__ import annotations

import json
import subprocess

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from spatialforge_backend.db.models import HardwareProfile
from spatialforge_backend.services import hardware
from spatialforge_backend.services.hardware import capture_hardware, dependency_report


def test_hardware_snapshot_is_conservative_and_complete() -> None:
    profile = capture_hardware()
    assert profile.logical_core_count >= 1
    assert profile.memory_total_mb > 0
    assert profile.memory_available_mb > 0
    assert profile.recommended_preset in {
        "fast_preview",
        "balanced_room",
        "cpu_compatible",
    }


def test_dependency_report_has_explicit_results() -> None:
    report = dependency_report()
    assert [item["name"] for item in report] == [
        "colmap",
        "DensifyPointCloud",
        "ReconstructMesh",
        "TextureMesh",
        "ffmpeg",
        "blender",
    ]
    assert all(isinstance(item["available"], bool) for item in report)


def test_startup_hardware_snapshot_is_persisted(client: TestClient) -> None:
    factory = client.app.state.session_factory
    with factory() as session:
        assert session.scalar(select(func.count(HardwareProfile.id))) == 1


def test_windows_gpu_fallback_detects_intel_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hardware.platform, "system", lambda: "Windows")
    monkeypatch.setattr(hardware.shutil, "which", lambda name: "powershell.exe")
    payload = json.dumps({"Name": "Intel(R) Arc(TM) A770 Graphics", "AdapterRAM": 17179869184})
    monkeypatch.setattr(
        hardware.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, payload, ""),
    )

    name, memory = hardware._windows_gpu_profile()

    assert name == "Intel(R) Arc(TM) A770 Graphics"
    assert memory == 16384


def test_nvidia_usage_parser_is_optional_and_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hardware.shutil, "which", lambda name: "nvidia-smi")
    monkeypatch.setattr(
        hardware.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "42, 3072\n", ""),
    )

    assert hardware.nvidia_usage() == (42.0, 3072)
