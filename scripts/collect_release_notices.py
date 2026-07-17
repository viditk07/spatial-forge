"""Fail-closed runtime licence check and notice collector for release packaging."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from importlib.metadata import Distribution, distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
PYTHON_RUNTIME_ROOTS = {
    "alembic": set(),
    "fastapi": set(),
    "fast-simplification": set(),
    "httpx": set(),
    "opencv-python-headless": set(),
    "pillow": set(),
    "psutil": set(),
    "pydantic-settings": set(),
    "python-multipart": set(),
    "sqlalchemy": set(),
    "structlog": set(),
    "trimesh": set(),
    "typer": set(),
    "uvicorn": {"standard"},
}
NUGET_NOTICES = {
    "microsoft.extensions.dependencyinjection/10.0.10": ("THIRD-PARTY-NOTICES.TXT",),
    "microsoft.web.webview2/1.0.4078.44": ("LICENSE.txt", "NOTICE.txt"),
}


def _safe_name(value: str) -> str:
    return "".join(
        character if character.isalnum() else "-" for character in value
    ).strip("-")


def _python_runtime_closure() -> list[tuple[str, Distribution]]:
    pending = list(PYTHON_RUNTIME_ROOTS.items())
    resolved: dict[str, Distribution] = {}
    while pending:
        name, extras = pending.pop()
        canonical = canonicalize_name(name)
        if canonical in resolved:
            continue
        package = distribution(name)
        resolved[canonical] = package
        for requirement_text in package.requires or []:
            requirement = Requirement(requirement_text)
            contexts = extras or {""}
            if requirement.marker and not any(
                requirement.marker.evaluate({"extra": extra}) for extra in contexts
            ):
                continue
            pending.append((requirement.name, set(requirement.extras)))
    return sorted(resolved.items())


def _licence_identifier(package: Distribution) -> str | None:
    metadata = package.metadata
    declared = metadata.get("License-Expression") or metadata.get("License")
    if declared and declared.strip():
        return declared.splitlines()[0]
    classifiers = metadata.get_all("Classifier") or []
    known = {
        "License :: OSI Approved :: Apache Software License": "Apache-2.0",
        "License :: OSI Approved :: BSD License": "BSD",
        "License :: OSI Approved :: ISC License (ISCL)": "ISC",
        "License :: OSI Approved :: MIT License": "MIT",
        "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    }
    return next(
        (
            identifier
            for classifier, identifier in known.items()
            if classifier in classifiers
        ),
        None,
    )


def collect(output: Path, nuget_root: Path) -> dict[str, object]:
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("Release notice output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"python": [], "viewer": [], "dotnet": []}
    errors: list[str] = []

    for name, package in _python_runtime_closure():
        metadata = package.metadata
        licence = _licence_identifier(package)
        if licence is None:
            errors.append(f"{name} {package.version}: missing licence metadata")
            continue
        entry = {
            "name": name,
            "version": package.version,
            "licence": licence,
        }
        cast_entries = manifest["python"]
        assert isinstance(cast_entries, list)
        cast_entries.append(entry)
        for declared in metadata.get_all("License-File") or []:
            candidates = [
                file for file in package.files or [] if str(file).endswith(declared)
            ]
            if not candidates:
                errors.append(
                    f"{name} {package.version}: declared licence file {declared} missing"
                )
                continue
            source = Path(package.locate_file(candidates[0]))
            target = output / f"python-{_safe_name(name)}-{source.name}"
            shutil.copyfile(source, target)

    three_root = ROOT / "apps" / "viewer" / "node_modules" / "three"
    three_package = json.loads(
        (three_root / "package.json").read_text(encoding="utf-8")
    )
    if three_package.get("license") != "MIT" or not (three_root / "LICENSE").is_file():
        errors.append("three: expected MIT metadata and LICENSE file")
    else:
        shutil.copyfile(three_root / "LICENSE", output / "viewer-three-LICENSE")
        viewer_entries = manifest["viewer"]
        assert isinstance(viewer_entries, list)
        viewer_entries.append(
            {"name": "three", "version": three_package["version"], "licence": "MIT"}
        )

    for relative, filenames in NUGET_NOTICES.items():
        package_root = nuget_root / relative
        dotnet_entries = manifest["dotnet"]
        assert isinstance(dotnet_entries, list)
        dotnet_entries.append({"package": relative, "notice_files": list(filenames)})
        for filename in filenames:
            source = package_root / filename
            if not source.is_file():
                errors.append(f"{relative}: missing {filename}")
                continue
            shutil.copyfile(
                source, output / f"dotnet-{relative.replace('/', '-')}-{filename}"
            )

    if errors:
        raise RuntimeError(
            "Release notice validation failed:\n- " + "\n- ".join(errors)
        )
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    default_nuget = Path(
        os.environ.get("NUGET_PACKAGES", Path.home() / ".nuget" / "packages")
    )
    parser.add_argument("--nuget-root", type=Path, default=default_nuget)
    arguments = parser.parse_args()
    manifest = collect(arguments.output.resolve(), arguments.nuget_root.resolve())
    print(
        "Validated release notices for "
        f"{sum(len(entries) for entries in manifest.values())} runtime dependency groups."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
