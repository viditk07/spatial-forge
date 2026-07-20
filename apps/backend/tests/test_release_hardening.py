from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_github_actions_and_installer_tool_are_immutably_pinned() -> None:
    workflows = [
        ROOT / ".github" / "workflows" / "ci.yml",
        ROOT / ".github" / "workflows" / "windows-package.yml",
    ]
    action = re.compile(r"^\s*- uses: [^@\s]+@([0-9a-f]{40})(?:\s+#\s+v\d+)?$", re.MULTILINE)
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        uses = [line for line in text.splitlines() if "- uses:" in line]
        assert uses
        assert len(action.findall(text)) == len(uses)

    package_workflow = workflows[1].read_text(encoding="utf-8")
    assert "choco install innosetup --version=6.7.1" in package_workflow


def test_packaging_has_portable_hashes_and_fail_closed_signing() -> None:
    script = (ROOT / "scripts" / "package-windows.ps1").read_text(encoding="utf-8")

    assert "[IO.Path]::GetRelativePath($publish, $_.FullName)" in script
    assert "Select-Object Hash, Path" not in script
    assert "Get-AuthenticodeSignature" in script
    assert '$RequireSigning -and $signature.Status -ne "Valid"' in script


def test_public_governance_documents_are_explicit() -> None:
    licence = (ROOT / "LICENSE.txt").read_text(encoding="utf-8")
    normalised = " ".join(licence.split())

    assert "SpatialForge Source-Visible Evaluation Licence 1.0" in licence
    assert "no licence is granted to copy, modify, distribute" in normalised
    for path in ("SECURITY.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", ".github/CODEOWNERS"):
        assert (ROOT / path).is_file()
