"""Run the complete cross-platform validation available on the current host."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(arguments: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print(f"+ {' '.join(arguments)}", flush=True)
    subprocess.run(arguments, cwd=cwd, env=env, check=True, shell=False)  # noqa: S603


def main() -> int:
    python = ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    if not python.is_file():
        raise RuntimeError("Create .venv and install apps/backend[dev,vision] first.")
    python_quality_paths = ["apps/backend", "scripts/collect_release_notices.py"]
    run([str(python), "-m", "ruff", "format", "--check", *python_quality_paths])
    run([str(python), "-m", "ruff", "check", *python_quality_paths])
    run([str(python), "-m", "mypy", "apps/backend/src"])
    run([str(python), "-m", "pytest", "apps/backend/tests"])
    run(["npm", "run", "format:check"], ROOT / "apps/viewer")
    run(["npm", "run", "lint"], ROOT / "apps/viewer")
    run(["npm", "run", "typecheck"], ROOT / "apps/viewer")
    run(["npm", "test"], ROOT / "apps/viewer")
    run(["npm", "run", "build"], ROOT / "apps/viewer")
    dotnet = shutil.which("dotnet") or str(ROOT / (".dotnet/dotnet.exe" if os.name == "nt" else ".dotnet/dotnet"))
    if Path(dotnet).is_file() or shutil.which(dotnet):
        environment = os.environ.copy()
        environment["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
        environment.setdefault("DOTNET_CLI_HOME", str(ROOT / ".dotnet-home"))
        solution = "apps/desktop/SpatialForge.sln"
        run([dotnet, "format", solution, "--verify-no-changes", "--no-restore"], env=environment)
        run([dotnet, "build", solution, "-c", "Release", "--no-restore", "-m:1"], env=environment)
        run([dotnet, "test", solution, "-c", "Release", "--no-build", "--no-restore", "-m:1"], env=environment)
    else:
        print("Skipping desktop validation: dotnet was not found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
