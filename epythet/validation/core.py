"""The ``validate`` orchestrator: resolve the package, run the levels, build the report.

This module is the single source of truth every surface calls. It returns a
:class:`~epythet.validation.model.Report` (JSON-able via ``to_dict``), never
prints and never exits, so the CLI, a future MCP tool or an HTTP endpoint all
wrap the same function.

Seams (one keyword argument each, as in decision D8):

- ``backend=`` — the build backend for level 1; defaults to
  :class:`~epythet.validation.build.SphinxBackend`. Levels 0 and 0.5 never
  touch it.
- ``ledger=`` — the rule catalog; ``None`` is the bundled ledger, a directory
  is a package-local overlay.

Levels 2 (render) and 3 (review) are declared in the model and reserved for
WP3; asking for them raises :class:`NotImplementedError` with a pointer.
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from epythet.validation.model import (
    IMPLEMENTED_LEVELS,
    IMPLEMENTED_TIERS,
    Finding,
    Report,
    Timer,
    levels_for_tier,
    sort_findings,
)
from epythet.validation.ledger import (
    Ledger,
    append_observations,
    load_ledger,
    occurrence_counts,
)

PROJECT_MARKERS = ("pyproject.toml", "setup.cfg")


@dataclass
class ResolvedPackage:
    """Where the package's source lives and which project it belongs to."""

    name: str
    package_dir: Path
    project_dir: Path
    version: str | None = None


def _project_metadata(project_dir: Path) -> tuple[str | None, str | None]:
    """``(name, version)`` from the project config.

    epythet's own ``parse_config`` is tried first (the one import from the rest
    of epythet; it keeps its 5-tuple by the v2 back-compat contract). Whenever
    it cannot read the file, a direct read of ``[project]`` is the fallback.
    """
    for marker in PROJECT_MARKERS:
        config = project_dir / marker
        if not config.exists():
            continue
        try:
            from epythet.config_parser import parse_config

            name, _copyright, _author, version, _display = parse_config(str(config))
            return (name or None), (version or None)
        except Exception:
            pass
        if marker == "pyproject.toml":
            try:
                import tomllib
            except ImportError:  # Python 3.10
                import tomli as tomllib  # type: ignore[no-redef]
            try:
                project = tomllib.loads(config.read_text(encoding="utf-8")).get(
                    "project", {}
                )
                return project.get("name"), project.get("version")
            except Exception:
                return None, None
        return None, None
    return None, None


def _find_project_dir(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
    return start.parent


def _package_dir_in_project(project_dir: Path, name: str | None) -> Path | None:
    candidates = []
    if name:
        candidates += [
            project_dir / name,
            project_dir / name.replace("-", "_"),
            project_dir / "src" / name,
        ]
    candidates += [
        project_dir / project_dir.name,
        project_dir / "src" / project_dir.name,
    ]
    for candidate in candidates:
        if (candidate / "__init__.py").exists():
            return candidate
    return None


def resolve_package(package: str | os.PathLike) -> ResolvedPackage:
    """Turn ``<package_dir_or_import_name>`` into a :class:`ResolvedPackage`.

    Accepts a project root (contains ``pyproject.toml``/``setup.cfg``), a
    package directory (contains ``__init__.py``) or an importable name.
    """
    path = Path(package).expanduser()
    if path.is_dir():
        path = path.resolve()
        if (path / "__init__.py").exists():
            project_dir = _find_project_dir(path.parent)
            name, version = _project_metadata(project_dir)
            return ResolvedPackage(path.name, path, project_dir, version)
        name, version = _project_metadata(path)
        package_dir = _package_dir_in_project(path, name)
        if package_dir is None:
            raise FileNotFoundError(
                f"{path} is neither a package (no __init__.py) nor a project with a "
                f"package directory I can find (tried {name or path.name!r} and src/)"
            )
        return ResolvedPackage(package_dir.name, package_dir, path, version)
    spec = importlib.util.find_spec(str(package)) if "/" not in str(package) else None
    if spec is None or not spec.submodule_search_locations:
        raise FileNotFoundError(
            f"{package!r} is not a directory or an importable package"
        )
    package_dir = Path(next(iter(spec.submodule_search_locations))).resolve()
    project_dir = _find_project_dir(package_dir.parent)
    _name, version = _project_metadata(project_dir)
    return ResolvedPackage(package_dir.name, package_dir, project_dir, version)


def _epythet_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("epythet")
    except Exception:
        return None


def validate(
    package: str | os.PathLike,
    *,
    level: int = 1,
    levels: Iterable[float] | None = None,
    ledger: Ledger | str | os.PathLike | None = None,
    backend=None,
    fail_on: str = "error",
    napoleon: bool = True,
    style: str = "google",
    ignore: Iterable[str] = (),
    observe: bool = True,
    observations_path: str | os.PathLike | None = None,
) -> Report:
    """Validate a package's documentation and return a :class:`Report`.

    Args:
        package: A project root, a package directory, or an importable name.
        level: The CLI tier: ``0`` lint only, ``1`` lint + parse (default),
            ``2`` adds the Sphinx build. Tiers 3 and 4 belong to WP3.
        levels: An explicit set of levels (``[0.5]`` for a parse-only sweep);
            overrides ``level`` when given.
        ledger: ``None`` for the bundled rules, or a directory overlay.
        backend: The build backend for level 1 (default: ``SphinxBackend()``).
        fail_on: Severity threshold recorded on the report for exit codes.
        napoleon: Pre-process Google/NumPy sections the way the fleet's
            ``conf.py`` does. Set ``False`` for a package built without napoleon.
        style: Docstring convention passed to ruff and pydoclint.
        ignore: Path substrings to skip, as ``epythet quickstart --ignore``.
        observe: Append findings to the observations JSONL (outside the repo).
        observations_path: Override the observations file (tests use this).
    """
    from epythet.validation.build import SphinxBackend, run_build_level
    from epythet.validation.docstrings import count_public_objects, iter_docstrings
    from epythet.validation.lint import run_lint_level
    from epythet.validation.parse import run_parse_level, sphinx_available

    if levels is None:
        if level not in IMPLEMENTED_TIERS:
            raise NotImplementedError(
                f"level {level} (render/review) is owned by WP3; implemented tiers: {IMPLEMENTED_TIERS}"
            )
        levels = levels_for_tier(level)
    levels = sorted(set(levels))
    unsupported = [lv for lv in levels if lv not in IMPLEMENTED_LEVELS]
    if unsupported:
        raise NotImplementedError(
            f"levels {unsupported} are owned by WP3; implemented: {IMPLEMENTED_LEVELS}"
        )
    resolved = resolve_package(package)
    catalog = load_ledger(ledger)
    backend = backend if backend is not None else SphinxBackend()
    # Importing Sphinx costs a few hundred ms; only pay it when a level needs it.
    versions = backend.versions() if any(lv >= 0.5 for lv in levels) else {}
    report = Report(
        package=resolved.name,
        package_dir=str(resolved.package_dir),
        levels_run=levels,
        epythet_version=_epythet_version(),
        sphinx_version=versions.get("sphinx"),
        docutils_version=versions.get("docutils"),
        ledger_sources=[str(p) for p in catalog.sources],
    )
    ignore = tuple(ignore)
    findings: list[Finding] = []

    if 0 in levels:
        with Timer(report.durations, "0"):
            found, notes = run_lint_level(
                resolved.package_dir, project_dir=resolved.project_dir, style=style
            )
        findings += found
        report.notes += notes

    if 0.5 in levels:
        with Timer(report.durations, "0.5"):
            if napoleon and not sphinx_available():
                report.notes.append(
                    "sphinx not importable: napoleon pre-processing skipped"
                )
            skipped: list[str] = []
            findings += run_parse_level(
                iter_docstrings(
                    resolved.package_dir,
                    ignore=ignore,
                    on_skip=lambda path, reason: skipped.append(
                        f"skipped {path.name}: {reason}"
                    ),
                ),
                catalog,
                napoleon=napoleon,
            )
            report.notes += skipped
            coverage = count_public_objects(resolved.package_dir, ignore=ignore)
        report.objects_checked = coverage.checked
        report.objects_undocumented = coverage.undocumented

    if 1 in levels:
        with Timer(report.durations, "1"):
            found, notes = run_build_level(
                resolved.project_dir, catalog, backend=backend
            )
        findings += found
        report.notes += notes

    counts = occurrence_counts(Path(observations_path) if observations_path else None)
    for finding in findings:
        finding.ledger_occurrences = counts.get(finding.rule, 0)
    report.findings = sort_findings(findings)
    if observe and report.findings:
        written = append_observations(
            report.findings,
            package=resolved.name,
            package_version=resolved.version,
            path=Path(observations_path) if observations_path else None,
        )
        report.notes.append(f"{written} observations appended to the ledger")
    return report
