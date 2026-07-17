"""Conservative local hardware and dependency inspection."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass

import psutil
from sqlalchemy.orm import Session

from spatialforge_backend.db.models import HardwareProfile


@dataclass(frozen=True, slots=True)
class HardwareSnapshot:
    operating_system: str
    cpu_model: str
    logical_core_count: int
    memory_total_mb: int
    memory_available_mb: int
    gpu_model: str | None
    gpu_memory_mb: int | None
    cuda_available: bool
    opengl_version: str | None
    recommended_preset: str

    def to_dict(self) -> dict[str, str | int | bool | None]:
        return asdict(self)


def _nvidia_profile() -> tuple[str | None, int | None]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None, None
    try:
        completed = subprocess.run(  # noqa: S603 - executable is resolved from a fixed name
            [
                executable,
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
            shell=False,
        )
        first = completed.stdout.strip().splitlines()[0]
        name, memory = (part.strip() for part in first.rsplit(",", 1))
        return name, int(memory)
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None, None


def _windows_gpu_profile() -> tuple[str | None, int | None]:
    """Query the primary Windows display adapter without loading a graphics context."""
    if platform.system() != "Windows":
        return None, None
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if not executable:
        return None, None
    command = (
        "Get-CimInstance Win32_VideoController | "
        "Where-Object { $_.Name -and $_.Name -notmatch 'Microsoft Basic' } | "
        "Select-Object -First 1 Name,AdapterRAM | ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(  # noqa: S603 - executable and script are fixed
            [executable, "-NoProfile", "-NonInteractive", "-Command", command],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
            shell=False,
        )
        payload = json.loads(completed.stdout)
        name = payload.get("Name")
        adapter_ram = payload.get("AdapterRAM")
        memory = int(adapter_ram) // 1024**2 if adapter_ram else None
        return (str(name), memory) if name else (None, None)
    except (OSError, TypeError, ValueError, json.JSONDecodeError, subprocess.SubprocessError):
        return None, None


def nvidia_usage() -> tuple[float | None, int | None]:
    """Return current NVIDIA utilisation and used VRAM, or unknown when unavailable."""
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None, None
    try:
        completed = subprocess.run(  # noqa: S603 - executable is resolved from a fixed name
            [
                executable,
                "--query-gpu=utilization.gpu,memory.used",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
            shell=False,
        )
        first = completed.stdout.strip().splitlines()[0]
        utilisation, memory = (part.strip() for part in first.rsplit(",", 1))
        return float(utilisation), int(memory)
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None, None


def capture_hardware() -> HardwareSnapshot:
    """Capture safe capability facts without network access."""
    memory = psutil.virtual_memory()
    gpu, gpu_memory = _nvidia_profile()
    cuda_available = gpu is not None
    if gpu is None:
        gpu, gpu_memory = _windows_gpu_profile()
    memory_gb = memory.total / (1024**3)
    if gpu and gpu_memory and gpu_memory >= 6144 and memory_gb >= 24:
        preset = "balanced_room"
    elif memory_gb >= 16:
        preset = "cpu_compatible"
    else:
        preset = "fast_preview"
    return HardwareSnapshot(
        operating_system=f"{platform.system()} {platform.release()} ({platform.machine()})",
        cpu_model=platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "Unknown CPU"),
        logical_core_count=psutil.cpu_count(logical=True) or 1,
        memory_total_mb=memory.total // (1024**2),
        memory_available_mb=memory.available // (1024**2),
        gpu_model=gpu,
        gpu_memory_mb=gpu_memory,
        cuda_available=cuda_available,
        opengl_version=None,
        recommended_preset=preset,
    )


def persist_hardware(session: Session, snapshot: HardwareSnapshot) -> HardwareProfile:
    """Persist a startup capability snapshot for diagnostics and support history."""
    profile = HardwareProfile(
        cpu_model=snapshot.cpu_model,
        logical_core_count=snapshot.logical_core_count,
        memory_total_mb=snapshot.memory_total_mb,
        gpu_model=snapshot.gpu_model,
        gpu_memory_mb=snapshot.gpu_memory_mb,
        cuda_available=snapshot.cuda_available,
        opengl_version=snapshot.opengl_version,
        operating_system=snapshot.operating_system,
        recommended_preset=snapshot.recommended_preset,
    )
    session.add(profile)
    session.commit()
    return profile


def dependency_report() -> list[dict[str, str | bool | None]]:
    """Return explicit availability and version information for external tools."""
    results: list[dict[str, str | bool | None]] = []
    for name in (
        "colmap",
        "DensifyPointCloud",
        "ReconstructMesh",
        "TextureMesh",
        "ffmpeg",
        "blender",
    ):
        path = shutil.which(name)
        version: str | None = None
        if path:
            try:
                completed = subprocess.run(  # noqa: S603 - fixed allowlist only
                    [path, "--version"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=False,
                )
                version = (completed.stdout or completed.stderr).splitlines()[0][:200]
            except (OSError, subprocess.SubprocessError):
                version = "Unable to query version"
        results.append({"name": name, "available": path is not None, "version": version})
    return results
