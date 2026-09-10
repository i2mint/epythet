"""Level 0: static docstring linters, normalised into the finding model.

Two tools are shelled out to. ``ruff check --select D`` covers pydocstyle
(presence, summary lines, section formatting for the configured convention).
``pydoclint`` covers signature consistency (``DOC1xx``/``DOC2xx``/``DOC4xx``/
``DOC5xx``: undocumented or misnamed parameters, missing returns), which ruff
only previews a handful of; it is optional and skipped with a note when it is
not installed.

Findings keep the tool's own code as ``rule`` (``D102``, ``DOC101``) and name
the tool in ``tool``, so they never collide with ledger ids.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterator

from epythet.validation.model import Finding

LINT_LEVEL = 0

#: Docstring styles ruff's pydocstyle convention and pydoclint's ``--style`` both accept.
STYLES = ("google", "numpy", "sphinx")


def ruff_severity(code: str) -> str:
    """``D1xx`` (missing docstrings) are warnings; other ``D`` rules are style, so info.

    >>> ruff_severity("D102"), ruff_severity("D205")
    ('warning', 'info')
    """
    return "warning" if code.startswith("D1") else "info"


def _relative(filename: str, project_dir: Path) -> str:
    try:
        return Path(filename).resolve().relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        return filename


def run_ruff(
    package_dir: Path, *, project_dir: Path, style: str = "google"
) -> tuple[list[Finding], list[str]]:
    """Run ``ruff check --select D`` and translate its JSON output.

    Returns ``(findings, notes)``; ``notes`` explains a skipped run.
    """
    exe = shutil.which("ruff")
    if exe is None:
        return [], [
            "ruff not found: level 0 pydocstyle checks skipped (pip install 'epythet[validate]')"
        ]
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}, got {style!r}")
    cmd = [
        exe,
        "check",
        "--select",
        "D",
        "--output-format",
        "json",
        "--exit-zero",
        "--no-cache",
        "--config",
        f"lint.pydocstyle.convention = '{style}'",
        str(package_dir),
    ]
    proc = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
    if proc.returncode not in (0, 1) or not proc.stdout.strip():
        return [], [
            f"ruff failed (exit {proc.returncode}): {proc.stderr.strip()[:300]}"
        ]
    try:
        diagnostics = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [], [f"ruff produced unparseable output: {proc.stdout[:200]!r}"]
    findings = [
        Finding(
            rule=d["code"],
            severity=ruff_severity(d["code"]),
            level=LINT_LEVEL,
            message=d["message"],
            file=_relative(d["filename"], project_dir),
            line=d.get("location", {}).get("row"),
            detector="lint",
            fix=(d.get("fix") or {}).get("message") or "",
            autofixable=bool(d.get("fix")),
            tool="ruff",
        )
        for d in diagnostics
        if (d.get("code") or "").startswith("D")
    ]
    return findings, []


_PYDOCLINT_LINE_RE = re.compile(r"^\s+(?P<line>\d+): (?P<code>DOC\d+): (?P<msg>.*)$")

#: pydoclint options that silence its type-hint bookkeeping: the house convention
#: is types in annotations, never in the docstring, and not every signature is annotated.
PYDOCLINT_OPTIONS = (
    "--quiet",
    "--skip-checking-short-docstrings",
    "true",
    "--arg-type-hints-in-docstring",
    "false",
    "--arg-type-hints-in-signature",
    "false",
    "--check-return-types",
    "false",
    "--check-yield-types",
    "false",
)


def pydoclint_severity(code: str) -> str:
    """``DOC1xx`` (arguments disagree with the signature) are warnings; the rest info.

    >>> pydoclint_severity("DOC101"), pydoclint_severity("DOC201")
    ('warning', 'info')
    """
    return "warning" if code.startswith("DOC1") else "info"


def _parse_pydoclint(output: str, project_dir: Path) -> Iterator[Finding]:
    current_file: str | None = None
    for raw in output.splitlines():
        if not raw.strip():
            continue
        match = _PYDOCLINT_LINE_RE.match(raw)
        if match is None:
            if not raw.startswith(" "):
                current_file = _relative(raw.strip(), project_dir)
            continue
        yield Finding(
            rule=match["code"],
            severity=pydoclint_severity(match["code"]),
            level=LINT_LEVEL,
            message=match["msg"].strip(),
            file=current_file,
            line=int(match["line"]),
            detector="lint",
            tool="pydoclint",
        )


def run_pydoclint(
    package_dir: Path, *, project_dir: Path, style: str = "google"
) -> tuple[list[Finding], list[str]]:
    """Run ``pydoclint`` if installed; otherwise return a note and no findings.

    pydoclint writes its report to stderr, so both streams are parsed.
    """
    exe = shutil.which("pydoclint")
    if exe is None:
        return [], [
            "pydoclint not installed: signature-consistency checks skipped (pip install pydoclint)"
        ]
    cmd = [exe, "--style", style, *PYDOCLINT_OPTIONS, str(package_dir)]
    proc = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
    output = proc.stdout + "\n" + proc.stderr
    if proc.returncode not in (0, 1) and "DOC" not in output:
        return [], [
            f"pydoclint failed (exit {proc.returncode}): {proc.stderr.strip()[:300]}"
        ]
    return list(_parse_pydoclint(output, project_dir)), []


def run_lint_level(
    package_dir: Path, *, project_dir: Path, style: str = "google"
) -> tuple[list[Finding], list[str]]:
    """Level 0: ruff D plus pydoclint, with notes for anything skipped."""
    findings: list[Finding] = []
    notes: list[str] = []
    for runner in (run_ruff, run_pydoclint):
        found, noted = runner(package_dir, project_dir=project_dir, style=style)
        findings.extend(found)
        notes.extend(noted)
    return findings, notes
