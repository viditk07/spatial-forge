# PyInstaller specification for the isolated local backend.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

root = Path(SPEC).resolve().parents[3]
backend = root / "apps" / "backend"
datas = [
    (str(backend / "migrations"), "spatialforge_backend/migrations"),
    (str(backend / "alembic.ini"), "spatialforge_backend"),
]
hiddenimports = collect_submodules("spatialforge_backend")
hiddenimports += collect_submodules("sqlalchemy.dialects.sqlite")
hiddenimports += ["cv2"]

analysis = Analysis(
    [str(backend / "packaging" / "backend_entry.py")],
    pathex=[str(backend / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["_pytest", "matplotlib", "pytest", "scipy"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="spatialforge-backend",
    console=False,
    disable_windowed_traceback=False,
)
collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    name="spatialforge-backend",
)
